from os import path as ospath
from re import compile as re_compile
from pycountry import languages
from ..ext_utils.media_utils import get_streams


class MetadataProcessor:
    def __init__(self):
        self.vars = {}
        self.audio_streams = []
        self.subtitle_streams = []
        self._year_pattern = re_compile(r"\b(19|20)\d{2}\b")
        self._sanitize_pattern = re_compile(r'[<>:"/\\?*]')

    def convert_lang_code(self, lang_code):
        if not lang_code or lang_code in ["unknown", "und", "none"]:
            return lang_code

        try:
            if len(lang_code) == 2:
                lang = languages.get(alpha_2=lang_code.lower())
            elif len(lang_code) == 3:
                lang = languages.get(alpha_3=lang_code.lower())
            else:
                return lang_code

            return lang.name if lang else lang_code
        except Exception:
            return lang_code

    async def extract_file_vars(self, file_path):
        self.vars = {
            "filename": ospath.basename(file_path),
            "basename": ospath.splitext(ospath.basename(file_path))[0],
            "extension": ospath.splitext(file_path)[1].lstrip("."),
            "audiolang": "unknown",
            "sublang": "none",
        }

        self.audio_streams = []
        self.subtitle_streams = []

        try:
            streams = await get_streams(file_path)
            if streams:
                for stream in streams:
                    codec_type = stream.get("codec_type", "").lower()
                    stream_lang = "unknown"
                    if "tags" in stream and "language" in stream["tags"]:
                        stream_lang = stream["tags"]["language"]

                    if codec_type == "audio":
                        self.audio_streams.append(
                            {
                                "index": stream.get("index", 0),
                                "language": stream_lang,
                                "full_language": self.convert_lang_code(stream_lang),
                            }
                        )
                        if self.vars["audiolang"] == "unknown" and stream_lang != "und":
                            self.vars["audiolang"] = self.convert_lang_code(stream_lang)
                    elif codec_type == "subtitle":
                        self.subtitle_streams.append(
                            {
                                "index": stream.get("index", 0),
                                "language": stream_lang,
                                "full_language": self.convert_lang_code(stream_lang),
                            }
                        )
                        if self.vars["sublang"] == "none" and stream_lang != "und":
                            self.vars["sublang"] = self.convert_lang_code(stream_lang)
        except Exception:
            pass

        year_match = self._year_pattern.findall(self.vars["basename"])
        if year_match:
            self.vars["year"] = year_match[-1]
        if year_match:
            self.vars["year"] = year_match[-1]

    def parse_string(self, metadata_str):
        metadata_dict = {}
        if metadata_str and isinstance(metadata_str, str):
            parts = []
            current = ""
            i = 0
            while i < len(metadata_str):
                if (
                    metadata_str[i] == "\\"
                    and i + 1 < len(metadata_str)
                    and metadata_str[i + 1] == "|"
                ):
                    current += "|"
                    i += 2
                elif metadata_str[i] == "|":
                    parts.append(current)
                    current = ""
                    i += 1
                else:
                    current += metadata_str[i]
                    i += 1
            if current:
                parts.append(current)

            for part in parts:
                if "=" in part:
                    key, value = part.split("=", 1)
                    metadata_dict[key.strip()] = value.strip()
        return metadata_dict

    def merge_dicts(self, default_dict, cmd_dict):
        merged = default_dict.copy() if default_dict else {}
        if cmd_dict:
            merged.update(cmd_dict)
        return merged

    def apply_vars_to_stream(
        self, metadata_dict, stream_lang=None, full_lang=None, stream_type="audio"
    ):
        if not metadata_dict or not isinstance(metadata_dict, dict):
            return {}

        processed = {}
        vars_with_stream = self.vars.copy()
        if stream_lang and stream_lang != "unknown":
            if stream_type == "audio":
                vars_with_stream["audiolang"] = full_lang or self.convert_lang_code(
                    stream_lang
                )
            elif stream_type == "subtitle":
                vars_with_stream["sublang"] = full_lang or self.convert_lang_code(
                    stream_lang
                )

        for key, value in metadata_dict.items():
            if isinstance(value, str):
                processed_value = value
                for var_name, var_value in vars_with_stream.items():
                    placeholder = f"{{{var_name}}}"
                    if placeholder in processed_value:
                        processed_value = processed_value.replace(
                            placeholder, str(var_value)
                        )
                processed[self.sanitize(key)] = processed_value
            else:
                processed[self.sanitize(key)] = str(value)

        return processed

    def apply_vars(self, metadata_dict):
        return self.apply_vars_to_stream(metadata_dict)

    def get_audio_metadata(self, audio_metadata_dict):
        audio_stream_metadata = []
        for stream in self.audio_streams:
            stream_meta = self.apply_vars_to_stream(
                audio_metadata_dict,
                stream["language"],
                stream["full_language"],
                "audio",
            )
            audio_stream_metadata.append(
                {"index": stream["index"], "metadata": stream_meta}
            )
        return audio_stream_metadata

    def get_subtitle_metadata(self, subtitle_metadata_dict):
        subtitle_stream_metadata = []
        for stream in self.subtitle_streams:
            stream_meta = self.apply_vars_to_stream(
                subtitle_metadata_dict,
                stream["language"],
                stream["full_language"],
                "subtitle",
            )
            subtitle_stream_metadata.append(
                {"index": stream["index"], "metadata": stream_meta}
            )
        return subtitle_stream_metadata

    def sanitize(self, value):
        if not isinstance(value, str):
            value = str(value)
        return self._sanitize_pattern.sub("_", value)[:100]

    async def process_all(
        self,
        video_metadata_dict,
        audio_metadata_dict,
        subtitle_metadata_dict,
        file_path,
    ):
        await self.extract_file_vars(file_path)

        return {
            "video": (
                self.apply_vars(video_metadata_dict) if video_metadata_dict else {}
            ),
            "audio_streams": (
                self.get_audio_metadata(audio_metadata_dict)
                if audio_metadata_dict
                else []
            ),
            "subtitle_streams": (
                self.get_subtitle_metadata(subtitle_metadata_dict)
                if subtitle_metadata_dict
                else []
            ),
            "global": {},
        }

    async def process(self, metadata_dict, file_path):
        await self.extract_file_vars(file_path)
        return self.apply_vars(metadata_dict)
