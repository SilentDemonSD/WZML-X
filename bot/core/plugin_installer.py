import shutil
import stat
import sys
import tarfile
import zipfile
from hashlib import sha256
from json import loads as json_loads
from pathlib import Path
from time import time
from uuid import uuid4

from .. import LOGGER
from .config_manager import Config
from .plugin_manager import MANIFEST_NAMES, PluginManifest, read_manifest

DEFAULT_SLUG = "SilentDemonSD/WZML-X"
DEFAULT_BRANCH = "wzv3-dev"
INDEX_PATH = "plugins/index.json"
MAX_ARCHIVE = 16 * 1024 * 1024
MAX_UNPACKED = 48 * 1024 * 1024
MAX_MEMBERS = 512
MANIFEST_DEPTH = 3
INDEX_TTL = 900


class InstallError(Exception):
    pass


def upstream_slug():
    repo = str(Config.UPSTREAM_REPO or "").strip()
    if not repo:
        return DEFAULT_SLUG
    text = repo.split("://", 1)[-1]
    if "@" in text:
        text = text.rsplit("@", 1)[1]
    text = text.split("#", 1)[0].split("?", 1)[0].strip("/")
    if text.endswith(".git"):
        text = text[:-4]
    parts = [part for part in text.split("/") if part]
    if len(parts) < 3 or "github.com" not in parts[0].lower():
        return DEFAULT_SLUG
    return f"{parts[1]}/{parts[2]}"


def official_repo_spec():
    branch = str(Config.UPSTREAM_BRANCH or "").strip() or DEFAULT_BRANCH
    return f"{upstream_slug()}@{branch}"


def official_index_url():
    branch = str(Config.UPSTREAM_BRANCH or "").strip() or DEFAULT_BRANCH
    return f"https://raw.githubusercontent.com/{upstream_slug()}/{branch}/{INDEX_PATH}"


def safe_target(dest, name):
    text = str(name).replace("\\", "/")
    if not text or text.startswith("/") or text.startswith("~"):
        raise InstallError(f"archive member has an absolute path: {name}")
    if len(text) > 1 and text[1] == ":":
        raise InstallError(f"archive member has a drive letter: {name}")
    if any(part == ".." for part in text.split("/")):
        raise InstallError(f"archive member escapes the target folder: {name}")
    target = (dest / text).resolve()
    if target != dest and dest not in target.parents:
        raise InstallError(f"archive member escapes the target folder: {name}")
    return target


def _guard(count, total):
    if count > MAX_MEMBERS:
        raise InstallError(f"archive has {count} entries, the limit is {MAX_MEMBERS}")
    if total > MAX_UNPACKED:
        raise InstallError(
            f"archive unpacks to {total} bytes, the limit is {MAX_UNPACKED}"
        )


def _extract_zip(archive, dest):
    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
        _guard(len(infos), sum(info.file_size for info in infos))
        targets = []
        for info in infos:
            if stat.S_ISLNK(info.external_attr >> 16):
                raise InstallError(f"archive contains a symlink: {info.filename}")
            targets.append((info, safe_target(dest, info.filename)))
        for info, target in targets:
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out, 65536)


def _extract_tar(archive, dest):
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        _guard(len(members), sum(m.size for m in members))
        for member in members:
            if member.issym() or member.islnk():
                raise InstallError(f"archive contains a link: {member.name}")
            if not (member.isfile() or member.isdir()):
                raise InstallError(f"archive contains {member.name}, not a plain file")
            safe_target(dest, member.name)
        bundle.extractall(dest, filter="data")


def extract_archive(archive, dest):
    archive = Path(archive)
    dest = Path(dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    size = archive.stat().st_size
    if size > MAX_ARCHIVE:
        raise InstallError(f"archive is {size} bytes, the limit is {MAX_ARCHIVE}")
    if zipfile.is_zipfile(archive):
        _extract_zip(archive, dest)
    elif tarfile.is_tarfile(archive):
        _extract_tar(archive, dest)
    else:
        raise InstallError("not a zip or tar archive")
    return dest


def find_plugin_roots(folder):
    folder = Path(folder)
    found = []
    queue = [(folder, 0)]
    while queue:
        current, depth = queue.pop(0)
        if any((current / name).is_file() for name in MANIFEST_NAMES):
            found.append(current)
            continue
        if depth >= MANIFEST_DEPTH:
            continue
        for child in sorted(current.iterdir()):
            if child.is_dir() and not child.name.startswith((".", "__")):
                queue.append((child, depth + 1))
    if not found:
        raise InstallError(
            "no wzml_plugin.yml found in the archive; a plugin must ship a manifest"
        )
    return found


def find_plugin_root(folder):
    return find_plugin_roots(folder)[0]


def digest(path):
    hasher = sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            hasher.update(block)
    return hasher.hexdigest()


async def download(url, dest):
    from niquests import AsyncSession

    async with AsyncSession() as session:
        response = await session.get(url, allow_redirects=True, timeout=60)
        if response.status_code != 200:
            raise InstallError(f"download failed with HTTP {response.status_code}")
        declared = response.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > MAX_ARCHIVE:
            raise InstallError(
                f"the file is {declared} bytes, the limit is {MAX_ARCHIVE}"
            )
        body = response.content or b""
        if not body:
            raise InstallError("the download was empty")
        if len(body) > MAX_ARCHIVE:
            raise InstallError(
                f"the file is {len(body)} bytes, the limit is {MAX_ARCHIVE}"
            )
        with open(dest, "wb") as handle:
            handle.write(body)
    return dest


def github_archive_url(spec):
    text = str(spec or "").strip()
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    text = text.rstrip("/")
    if text.endswith(".git"):
        text = text[:-4]
    branch = "main"
    if "@" in text:
        text, branch = text.rsplit("@", 1)
    if text.count("/") == 3 and "/tree/" in text:
        owner_repo, branch = text.split("/tree/", 1)
        text = owner_repo
    parts = [p for p in text.split("/") if p]
    if len(parts) != 2:
        raise InstallError(f"expected owner/repo, got {spec!r}")
    owner, repo = parts
    return f"https://codeload.github.com/{owner}/{repo}/tar.gz/refs/heads/{branch}"


async def install_dependencies(specs):
    if not specs:
        return True, ""
    from ..helper.ext_utils.bot_utils import cmd_exec

    attempts = []
    if shutil.which("uv"):
        attempts.append(
            ["uv", "pip", "install", "--python", sys.executable, "--no-cache-dir", *specs]
        )
    attempts.append([sys.executable, "-m", "pip", "install", "--no-input", *specs])

    last = ""
    for cmd in attempts:
        LOGGER.info(f"installing plugin dependencies: {' '.join(specs)}")
        _, err, code = await cmd_exec(cmd)
        if code == 0:
            return True, ""
        last = err or f"exit code {code}"
        LOGGER.warning(f"dependency install failed with {cmd[0]}: {last[:300]}")
    return False, last[:500]


def index_problem(payload):
    if not isinstance(payload, (dict, list)):
        return "that URL is not a plugin index"
    if isinstance(payload, list):
        return ""
    if "plugins" in payload:
        return "" if isinstance(payload["plugins"], list) else "its plugins key is not a list"
    if payload.get("$schema") and ("properties" in payload or "$defs" in payload):
        return (
            "that is the index SCHEMA, not an index. Point PLUGIN_INDEXES at a "
            "file holding a plugins list instead"
        )
    return "no plugins key in that file"


class PluginInstaller:
    def __init__(self, manager):
        self.manager = manager
        self._index = []
        self._index_at = 0.0
        self.problems = []

    @property
    def staging_dir(self):
        return self.manager.plugins_dir / ".staging"

    def index_urls(self):
        urls = [official_index_url()]
        for url in Config.PLUGIN_INDEXES or []:
            url = str(url).strip()
            if url and url not in urls:
                urls.append(url)
        return urls

    async def fetch_index(self, force=False):
        if not force and self._index and time() - self._index_at < INDEX_TTL:
            return self._index

        entries = []
        seen = set()
        problems = []
        try:
            from niquests import AsyncSession

            session_factory = AsyncSession
        except Exception as err:
            self.problems = [(u, f"cannot reach the network: {err}") for u in self.index_urls()]
            self._index = []
            self._index_at = time()
            LOGGER.error(f"plugin index: no http client available: {err}")
            return []

        try:
            entries, problems = await self._read_indexes(session_factory, seen)
        except Exception as err:
            problems = [(u, f"index fetch failed: {err}") for u in self.index_urls()]
            LOGGER.error(f"plugin index fetch failed: {err}", exc_info=True)
        self._index = entries
        self._index_at = time()
        self.problems = problems
        return entries

    async def _read_indexes(self, session_factory, seen):
        entries = []
        problems = []
        async with session_factory() as session:
            for url in self.index_urls():
                try:
                    response = await session.get(url, allow_redirects=True, timeout=20)
                    if response.status_code != 200:
                        why = f"HTTP {response.status_code}"
                        if response.status_code == 404:
                            why += " (no index file at that address)"
                        problems.append((url, why))
                        LOGGER.warning(f"plugin index {url} -> {why}")
                        continue
                    payload = json_loads(response.content or b"{}")
                except Exception as err:
                    problems.append((url, f"unreadable: {err}"))
                    LOGGER.warning(f"plugin index {url} unreadable: {err}")
                    continue

                why = index_problem(payload)
                if why:
                    problems.append((url, why))
                    LOGGER.warning(f"plugin index {url}: {why}")
                    continue

                items = payload.get("plugins") if isinstance(payload, dict) else payload
                good = 0
                for item in items or []:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("id") or item.get("name") or "").strip()
                    if not name or name in seen:
                        continue
                    if not (item.get("url") or item.get("repo")):
                        LOGGER.warning(
                            f"plugin index {url}: {name} has neither url nor repo"
                        )
                        continue
                    seen.add(name)
                    item["id"] = name
                    item["index"] = url
                    entries.append(item)
                    good += 1
                if not good:
                    problems.append((url, "reachable, but it lists no plugins yet"))
        return entries, problems

    def index_entry(self, name):
        for item in self._index:
            if item.get("id") == name:
                return item
        return None

    def _fresh_stage(self):
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        folder = self.staging_dir / uuid4().hex
        folder.mkdir()
        return folder

    def clear_staging(self):
        shutil.rmtree(self.staging_dir, ignore_errors=True)

    def _stage_root_of(self, path):
        staging = self.staging_dir.resolve()
        current = Path(path).resolve()
        while current.parent != staging:
            if current.parent == current or staging not in current.parents:
                return current
            current = current.parent
        return current

    async def stage_archive(self, archive, expect_sha=None, pick=None):
        if expect_sha:
            got = digest(archive)
            if got.lower() != str(expect_sha).lower():
                raise InstallError(
                    f"checksum mismatch: expected {expect_sha}, got {got}"
                )
        folder = self._fresh_stage()
        try:
            extract_archive(archive, folder)
            roots = find_plugin_roots(folder)
        except InstallError:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        except Exception as err:
            shutil.rmtree(folder, ignore_errors=True)
            raise InstallError(str(err)) from err

        found = []
        for root in roots:
            try:
                found.append((root, read_manifest(root)))
            except Exception as err:
                LOGGER.warning(f"skipping {root.name} in archive: {err}")
        if not found:
            shutil.rmtree(folder, ignore_errors=True)
            raise InstallError("no readable manifest in the archive")

        found.sort(key=lambda pair: pair[1].name)
        if pick:
            found = [pair for pair in found if pair[1].name == pick]
            if not found:
                shutil.rmtree(folder, ignore_errors=True)
                raise InstallError(f"{pick} is not in that archive")
        return folder, found

    def check(self, manifest):
        from ..version import get_version
        from .plugin_manager import missing_dependencies

        problem = manifest.version_error(get_version())
        if problem:
            raise InstallError(problem)
        clash = self.manager.taken_commands(skip=manifest.name)
        for item in manifest.command_names():
            if item in clash:
                raise InstallError(f"/{item} is already used by {clash[item]}")
        return missing_dependencies(manifest.python_dependencies)

    async def stage_url(self, url, expect_sha=None, pick=None):
        folder = self._fresh_stage()
        archive = folder / "download.bin"
        try:
            await download(url, archive)
            return await self.stage_archive(archive, expect_sha, pick)
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    async def stage_github(self, spec, pick=None):
        return await self.stage_url(github_archive_url(spec), pick=pick)

    async def stage_entry(self, item, pick=None):
        if item.get("repo"):
            return await self.stage_github(item["repo"], pick=pick or item["id"])
        return await self.stage_url(item["url"], item.get("sha256"), pick=pick)

    async def finalize(self, staged_root, manifest, source="local", url="", cleanup=True):
        name = manifest.name
        target = self.manager.dir_of(name)

        if name in self.manager.records:
            await self.manager.unload(name)

        backup = None
        if target.exists():
            backup = target.with_name(f"{name}.bak-{uuid4().hex[:8]}")
            target.rename(backup)
        try:
            shutil.copytree(staged_root, target)
            ok, err = await self.manager.load(
                name, enabled=True, source=source, url=url
            )
            if not ok:
                raise InstallError(err)
        except Exception as err:
            shutil.rmtree(target, ignore_errors=True)
            if backup is not None:
                backup.rename(target)
                await self.manager.load(name)
            raise InstallError(str(err)) from err
        finally:
            if cleanup:
                shutil.rmtree(self._stage_root_of(staged_root), ignore_errors=True)

        if backup is not None:
            shutil.rmtree(backup, ignore_errors=True)
        await self.manager._store(name, source=source, url=url)
        LOGGER.info(f"plugin {name} v{manifest.version} installed from {source}")
        return True

    async def uninstall(self, name):
        if name in self.manager.records:
            await self.manager.unload(name)
        try:
            target = self.manager.dir_of(name)
        except ValueError as err:
            return False, str(err)
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        self.manager.states.pop(name, None)
        try:
            from ..helper.ext_utils.db_handler import database

            await database.rm_plugin(name)
        except Exception as err:
            LOGGER.error(f"plugin {name}: could not clear the database record: {err}")
        LOGGER.info(f"plugin {name} uninstalled")
        return True, ""


def get_installer():
    from .plugin_manager import get_plugin_manager

    manager = get_plugin_manager()
    if getattr(manager, "installer", None) is None:
        manager.installer = PluginInstaller(manager)
    return manager.installer


__all__ = [
    "InstallError",
    "find_plugin_roots",
    "official_repo_spec",
    "index_problem",
    "official_index_url",
    "upstream_slug",
    "PluginInstaller",
    "PluginManifest",
    "download",
    "extract_archive",
    "find_plugin_root",
    "get_installer",
    "github_archive_url",
    "install_dependencies",
    "safe_target",
]
