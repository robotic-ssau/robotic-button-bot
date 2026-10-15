import json
from pathlib import Path
from typing import Any

from structlog import get_logger

logger = get_logger(__name__)

LOCALES_DIR = Path(__file__).resolve().parent / "locales"


class Localization:
    """Тексты бота из файла src/i18n/locales/<locale>.json.

    Ключи вложенные, обращение через точку: t("buttons.open").
    Подстановки в стиле str.format: t("council.added", surname="Иванов").
    """

    def __init__(self, locale: str = "ru") -> None:
        self.locale = locale
        path = LOCALES_DIR / f"{locale}.json"
        with path.open(encoding="utf-8") as file:
            self._data: dict[str, Any] = json.load(file)
        logger.info("Localization loaded", locale=locale, path=str(path))

    def get(self, key: str, **kwargs: Any) -> str:
        node: Any = self._data
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                logger.error("Missing localization key", key=key, locale=self.locale)
                return key
            node = node[part]
        if not isinstance(node, str):
            logger.error("Localization key is not a string", key=key, locale=self.locale)
            return key
        if not kwargs:
            return node
        try:
            return node.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            logger.exception("Failed to format localization string", key=key)
            return node


_localization: Localization | None = None


def init_localization(locale: str) -> Localization:
    global _localization
    _localization = Localization(locale)
    return _localization


def t(key: str, **kwargs: Any) -> str:
    global _localization
    if _localization is None:
        _localization = Localization()
    return _localization.get(key, **kwargs)


__all__ = ["Localization", "init_localization", "t"]
