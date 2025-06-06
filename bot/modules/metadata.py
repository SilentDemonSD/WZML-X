from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE
from os import path as ospath, walk

from aiofiles.os import path as aiopath, remove
from aioshutil import move

from .. import LOGGER, cpu_eater_lock, task_dict, task_dict_lock
from ..core.config_manager import BinConfig
from ..helper.ext_utils.bot_utils import sync_to_async
from ..helper.ext_utils.files_utils import get_path_size
from ..helper.ext_utils.media_utils import FFMpeg, get_document_type, get_media_info
from ..helper.mirror_leech_utils.status_utils.metadata_status import MetadataStatus


async def apply_metadata_title(self, dl_path, gid, metadata_dict):
    if not metadata_dict:
        return dl_path

    LOGGER.info(f"Applying metadata: '{metadata_dict}' to {self.name}")
    ffmpeg = FFMpeg(self)

    is_file_input = await aiopath.isfile(dl_path)
    files_to_process = []

    if is_file_input:
        is_video, is_audio, _ = await get_document_type(dl_path)
        if is_video or is_audio:
            files_to_process.append((dl_path, is_video, is_audio))
        else:
            LOGGER.info(f"Skipping metadata for non-audio/video file: {dl_path}")
            return dl_path
    else:
        for dirpath, _, filenames in await sync_to_async(walk, dl_path, topdown=False):
            for filename in filenames:
                f_path = ospath.join(dirpath, filename)
                is_video, is_audio, _ = await get_document_type(f_path)
                if is_video or is_audio:
                    files_to_process.append((f_path, is_video, is_audio))
                else:
                    LOGGER.info(f"Skipping metadata for non-audio/video file: {f_path}")

    if not files_to_process:
        LOGGER.info(f"No audio/video files found in {dl_path} to apply metadata.")
        return dl_path

    processed_one_successfully = False
    original_dl_path_name = ospath.basename(dl_path) if is_file_input else dl_path

    async with task_dict_lock:
        task_dict[self.mid] = MetadataStatus(self, ffmpeg, gid, "up")

    self.progress = False
    await cpu_eater_lock.acquire()
    self.progress = True

    try:
        for file_path, is_video, is_audio in files_to_process:
            if self.is_cancelled:
                break

            self.subname = ospath.basename(file_path)
            self.subsize = await get_path_size(file_path)

            original_extension = ospath.splitext(file_path)[1]
            temp_output_name = (
                f"{ospath.splitext(file_path)[0]}.meta_temp{original_extension}"
            )

            base_cmd = [
                BinConfig.FFMPEG_NAME,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                file_path,
                "-map",
                "0",
                "-map_metadata",
                "-1",
            ]

            for key, value in metadata_dict.items():
                base_cmd.extend(["-metadata", f"{key}={value}"])

            if is_video:
                for key, value in metadata_dict.items():
                    base_cmd.extend(
                        [
                            "-metadata:s:v",
                            f"{key}={value}",
                            "-metadata:s:a",
                            f"{key}={value}",
                            "-metadata:s:s",
                            f"{key}={value}",
                        ]
                    )
            elif is_audio:
                for key, value in metadata_dict.items():
                    base_cmd.extend(["-metadata:s:a", f"{key}={value}"])

            cmd = base_cmd + ["-c", "copy", temp_output_name]

            ffmpeg.clear()
            media_info_tuple = await get_media_info(file_path)
            if media_info_tuple:
                ffmpeg._total_time = media_info_tuple[0]

            self.subproc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
            await ffmpeg._ffmpeg_progress()
            _, stderr = await self.subproc.communicate()
            return_code = self.subproc.returncode

            if self.is_cancelled:
                if await aiopath.exists(temp_output_name):
                    await remove(temp_output_name)
                break

            if return_code == 0:
                LOGGER.info(f"Successfully applied metadata to {file_path}")
                await remove(file_path)
                await move(temp_output_name, file_path)
                if is_file_input and file_path == dl_path:
                    original_dl_path_name = file_path
                processed_one_successfully = True
            else:
                stderr_decoded = stderr.decode().strip()
                LOGGER.error(
                    f"Error applying metadata to {file_path}: {stderr_decoded}"
                )
                if await aiopath.exists(temp_output_name):
                    await remove(temp_output_name)
    finally:
        cpu_eater_lock.release()

    return (
        original_dl_path_name
        if is_file_input and processed_one_successfully
        else dl_path
    )
