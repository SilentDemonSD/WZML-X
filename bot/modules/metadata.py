from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE
import os
from os import path as ospath, walk

from aiofiles.os import path as aiopath, remove
from aioshutil import move

from .. import LOGGER, cpu_eater_lock, task_dict, task_dict_lock
from ..core.config_manager import BinConfig
from ..helper.ext_utils.bot_utils import sync_to_async
from ..helper.ext_utils.files_utils import get_path_size
from ..helper.ext_utils.media_utils import (
    FFMpeg,
    get_document_type,
    get_media_info,
    get_streams,
)
from ..helper.mirror_leech_utils.status_utils.metadata_status import MetadataStatus


async def apply_metadata_title(
    self,
    dl_path,
    gid,
    metadata_dict,
    audio_metadata_dict=None,
    video_metadata_dict=None,
    subtitle_metadata_dict=None,
):
    if not any(
        [
            metadata_dict,
            audio_metadata_dict,
            video_metadata_dict,
            subtitle_metadata_dict,
        ]
    ):
        return dl_path

    LOGGER.info(f"Applying metadata to {self.name}")
    ffmpeg = FFMpeg(self)
    is_file = await aiopath.isfile(dl_path)
    files = (
        [(dl_path, *await get_document_type(dl_path))]
        if is_file
        else [
            (ospath.join(d, f), *await get_document_type(ospath.join(d, f)))
            for d, _, fs in await sync_to_async(walk, dl_path, topdown=False)
            for f in fs
        ]
    )
    files = [(f, v, a) for f, v, a, _ in files if v or a]
    if not files:
        LOGGER.info(f"No audio/video files found in {dl_path} to apply metadata.")
        return dl_path

    async with task_dict_lock:
        task_dict[self.mid] = MetadataStatus(self, ffmpeg, gid, "up")
    self.progress = False
    await cpu_eater_lock.acquire()
    self.progress = True

    try:
        for file_path, is_video, is_audio in files:
            if self.is_cancelled:
                break
            self.subname = ospath.basename(file_path)
            self.subsize = await get_path_size(file_path)
            meta = await self.metadata_processor.process_all(
                video_metadata_dict or {},
                audio_metadata_dict or {},
                subtitle_metadata_dict or {},
                file_path,
            )
            if metadata_dict:
                meta["global"].update(
                    await self.metadata_processor.process(metadata_dict, file_path)
                )
            ext = ospath.splitext(file_path)[1]
            temp_out = f"{ospath.splitext(file_path)[0]}.meta_temp{ext}"
            streams = await get_streams(file_path)
            if not streams:
                LOGGER.error(f"Error getting streams for {file_path}. Skipping.")
                if is_file:
                    cpu_eater_lock.release()
                    return dl_path
                continue

            met_cmd = [
                BinConfig.FFMPEG_NAME,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                file_path,
            ]
            maps, meta_maps = [], []
            v, a, s = 0, 0, 0
            for stream in streams:
                idx, typ = stream["index"], stream["codec_type"]
                maps += ["-map", f"0:{idx}"]
                if typ == "video":
                    maps += [f"-c:v:{v}", "copy"]
                    if "tags" in stream and "language" in stream["tags"]:
                        meta_maps += [
                            f"-metadata:s:v:{v}",
                            f"language={stream['tags']['language']}",
                        ]
                    for k, v_ in meta["video"].items():
                        meta_maps += [f"-metadata:s:v:{v}", f"{k}={v_}"]
                    v += 1
                elif typ == "audio":
                    maps += [f"-c:a:{a}", "copy"]
                    if "tags" in stream and "language" in stream["tags"]:
                        meta_maps += [
                            f"-metadata:s:a:{a}",
                            f"language={stream['tags']['language']}",
                        ]
                    audio_meta = next(
                        (
                            m["metadata"]
                            for m in meta["audio_streams"]
                            if m["index"] == idx
                        ),
                        {},
                    )
                    for k, v_ in audio_meta.items():
                        meta_maps += [f"-metadata:s:a:{a}", f"{k}={v_}"]
                    a += 1
                elif typ == "subtitle":
                    maps += [f"-c:s:{s}", "copy"]
                    if "tags" in stream and "language" in stream["tags"]:
                        meta_maps += [
                            f"-metadata:s:s:{s}",
                            f"language={stream['tags']['language']}",
                        ]
                    sub_meta = next(
                        (
                            m["metadata"]
                            for m in meta["subtitle_streams"]
                            if m["index"] == idx
                        ),
                        {},
                    )
                    for k, v_ in sub_meta.items():
                        meta_maps += [f"-metadata:s:s:{s}", f"{k}={v_}"]
                    s += 1
                else:
                    maps += [f"-c:{idx}", "copy"]

            met_cmd += maps
            met_cmd += ["-map_metadata", "-1"]
            for item in meta_maps:
                met_cmd.append(item)
            for k, v_ in meta["global"].items():
                met_cmd += ["-metadata", f"{k}={v_}"]
            met_cmd += ["-threads", str(max(1, (os.cpu_count() or 2) // 2)), temp_out]

            ffmpeg.clear()
            media_info = await get_media_info(file_path)
            if media_info:
                ffmpeg._total_time = media_info[0]

            LOGGER.debug(f"FFmpeg command: {' '.join(met_cmd)}")
            self.subproc = await create_subprocess_exec(
                *met_cmd, stdout=PIPE, stderr=PIPE
            )
            await ffmpeg._ffmpeg_progress()
            _, stderr = await self.subproc.communicate()
            stderr_text = stderr.decode().strip() if stderr else ""

            if self.is_cancelled:
                if await aiopath.exists(temp_out):
                    await remove(temp_out)
                break

            if self.subproc.returncode == 0:
                LOGGER.info(f"Successfully applied metadata to {file_path}")
                await remove(file_path)
                await move(temp_out, file_path)
            else:
                LOGGER.error(f"Error applying metadata to {file_path}: {stderr_text}")
                if await aiopath.exists(temp_out):
                    await remove(temp_out)
    finally:
        cpu_eater_lock.release()
    return dl_path
