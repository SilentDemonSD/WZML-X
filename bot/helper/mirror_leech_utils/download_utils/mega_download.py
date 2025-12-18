from ...listeners.mega_listener import MegaAppListener


async def add_mega_download(listener, path):
    mega_listener = MegaAppListener(listener)
    await mega_listener.download(path)
