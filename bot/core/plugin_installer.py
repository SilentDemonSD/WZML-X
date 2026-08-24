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
DEFAULT_BRANCH = "master"
INDEX_PATH = "plugins/index.json"
MAX_ARCHIVE = 16 * 1024 * 1024
MAX_UNPACKED = 48 * 1024 * 1024
MAX_MEMBERS = 512
MANIFEST_DEPTH = 3
INDEX_TTL = 900


class InstallError(Exception):
    pass


def upstream_slug():
    """owner/repo from UPSTREAM_REPO, with any embedded credentials dropped."""
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


def find_plugin_root(folder):
    folder = Path(folder)
    queue = [(folder, 0)]
    while queue:
        current, depth = queue.pop(0)
        if any((current / name).is_file() for name in MANIFEST_NAMES):
            return current
        if depth >= MANIFEST_DEPTH:
            continue
        for child in sorted(current.iterdir()):
            if child.is_dir() and not child.name.startswith((".", "__")):
                queue.append((child, depth + 1))
    raise InstallError(
        "no wzml_plugin.yml found in the archive; a plugin must ship a manifest"
    )


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


class PluginInstaller:
    def __init__(self, manager):
        self.manager = manager
        self._index = []
        self._index_at = 0.0

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

        from niquests import AsyncSession

        entries = []
        seen = set()
        async with AsyncSession() as session:
            for url in self.index_urls():
                try:
                    response = await session.get(url, allow_redirects=True, timeout=20)
                    if response.status_code != 200:
                        LOGGER.warning(f"plugin index {url} -> HTTP {response.status_code}")
                        continue
                    payload = json_loads(response.content or b"{}")
                except Exception as err:
                    LOGGER.warning(f"plugin index {url} unreadable: {err}")
                    continue
                items = payload.get("plugins") if isinstance(payload, dict) else payload
                for item in items or []:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("id") or item.get("name") or "").strip()
                    if not name or name in seen or not item.get("url"):
                        continue
                    seen.add(name)
                    item["id"] = name
                    item["index"] = url
                    entries.append(item)
        self._index = entries
        self._index_at = time()
        return entries

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
        """The per-install folder directly under .staging that holds `path`."""
        staging = self.staging_dir.resolve()
        current = Path(path).resolve()
        while current.parent != staging:
            if current.parent == current or staging not in current.parents:
                return current
            current = current.parent
        return current

    async def stage_archive(self, archive, expect_sha=None):
        """Extract and validate. Returns (staged_root, manifest, missing_deps)."""
        if expect_sha:
            got = digest(archive)
            if got.lower() != str(expect_sha).lower():
                raise InstallError(
                    f"checksum mismatch: expected {expect_sha}, got {got}"
                )
        folder = self._fresh_stage()
        try:
            extract_archive(archive, folder)
            root = find_plugin_root(folder)
            manifest = read_manifest(root)
        except InstallError:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        except Exception as err:
            shutil.rmtree(folder, ignore_errors=True)
            raise InstallError(str(err)) from err

        from ..version import get_version
        from .plugin_manager import missing_dependencies

        problem = manifest.version_error(get_version())
        if problem:
            shutil.rmtree(folder, ignore_errors=True)
            raise InstallError(problem)

        clash = self.manager.taken_commands(skip=manifest.name)
        for item in manifest.command_names():
            if item in clash:
                shutil.rmtree(folder, ignore_errors=True)
                raise InstallError(f"/{item} is already used by {clash[item]}")

        return root, manifest, missing_dependencies(manifest.python_dependencies)

    async def stage_url(self, url, expect_sha=None):
        folder = self._fresh_stage()
        archive = folder / "download.bin"
        try:
            await download(url, archive)
            return await self.stage_archive(archive, expect_sha)
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    async def stage_github(self, spec):
        return await self.stage_url(github_archive_url(spec))

    async def finalize(self, staged_root, manifest, source="local", url=""):
        """Install a staged plugin. Returns True, or raises InstallError after
        rolling the previous version back."""
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
