from re import match as re_match
from base64 import urlsafe_b64decode, urlsafe_b64encode


def is_magnet(url: str):
    return bool(
        re_match(
            r"^magnet:\?.*xt=urn:(btih|btmh):([a-zA-Z0-9]{32,40}|[a-z2-7]{32}).*", url
        )
    )


def is_url(url: str):
    return bool(
        re_match(
            r"^(?!\/)(rtmps?:\/\/|mms:\/\/|rtsp:\/\/|https?:\/\/|ftp:\/\/)?([^\/:]+:[^\/@]+@)?(www\.)?(?=[^\/:\s]+\.[^\/:\s]+)([^\/:\s]+\.[^\/:\s]+)(:\d+)?(\/[^#\s]*[\s\S]*)?(\?[^#\s]*)?(#.*)?$",
            url,
        )
    )


def is_gdrive_link(url: str):
    return "drive.google.com" in url or "drive.usercontent.google.com" in url


def is_telegram_link(url: str):
    return url.startswith(("https://t.me/", "tg://openmessage?user_id="))


def is_mega_link(url: str):
    return "mega.nz" in url or "mega.co.nz" in url


def is_rapidgator_link(url: str):
    if not url:
        return False
    return "rapidgator.net" in url or "rapidgator.asia" in url or "rg.to" in url


def is_mega_folder_link(link: str) -> bool:
    if not link:
        return False
    return "/folder/" in link or "#F!" in link


def get_mega_subfolder_handle(link: str) -> str | None:
    if not link:
        return None
    parts = link.split("/folder/")
    if len(parts) >= 3:
        return parts[-1].split("#")[0].split("/")[0].split("?")[0]
    parts = link.split("#F!")
    if len(parts) >= 3:
        return parts[-1].split("!")[0].split("/")[0].split("?")[0]
    return None


def get_mega_link_type(url):
    return "folder" if "folder" in url or "/#F!" in url else "file"


def is_share_link(url: str):
    return bool(
        re_match(
            r"https?:\/\/.+\.gdtot\.\S+|https?:\/\/(filepress|filebee|appdrive|gdflix)\.\S+",
            url,
        )
    )


def is_rclone_path(path: str):
    return bool(
        re_match(
            r"^(mrcc:)?(?!(magnet:|mtp:|sa:|tp:))(?![- ])[a-zA-Z0-9_\. -]+(?<! ):(?!.*\/\/).*$|^rcl$",
            path,
        )
    )


def is_gdrive_id(id_: str):
    return bool(
        re_match(
            r"^(tp:|sa:|mtp:)?(?:[a-zA-Z0-9-_]{33}|[a-zA-Z0-9_-]{19})$|^gdl$|^(tp:|mtp:)?root$",
            id_,
        )
    )


def encode_slink(string):
    return (urlsafe_b64encode(string.encode("ascii")).decode("ascii")).strip("=")


def decode_slink(b64_str):
    return urlsafe_b64decode(
        (b64_str.strip("=") + "=" * (-len(b64_str.strip("=")) % 4)).encode("ascii")
    ).decode("ascii")
