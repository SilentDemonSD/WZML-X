from importlib import import_module
from os import listdir

from ...core.config_manager import Config

LOCALES_DIR = "bot/helper/languages"


class Language:
    _modules = {}
    _user_langs = {}

    def __init__(self, lang_code=None, user_id=None):
        self.load_translations()
        lang_code = lang_code or Config.DEFAULT_LANG

        if user_id:
            self._user_langs[user_id] = lang_code
        self.lang_code = self._user_langs.get(
            user_id, lang_code if lang_code in self._modules else Config.DEFAULT_LANG
        )

    @classmethod
    def load_translations(cls):
        if cls._modules:
            return cls._modules

        cls._modules = {}
        for file in listdir(LOCALES_DIR):
            if file.endswith(".py") and file != "__init__.py":
                lang_code = file.split(".")[0]
                cls._modules[lang_code] = import_module(
                    f"bot.helper.languages.{lang_code}"
                )
        return cls._modules

    def __getattr__(self, key):
        lang_module = self._modules.get(
            self.lang_code, self._modules[Config.DEFAULT_LANG]
        )
        return getattr(
            lang_module, key, getattr(self._modules[Config.DEFAULT_LANG], key, key)
        )
