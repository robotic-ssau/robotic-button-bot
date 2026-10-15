from dataclasses import dataclass
from enum import Enum


class KeyboardKind(Enum):
    USER = "user"              # «Лаборатория открыта?»
    COUNCIL = "council"        # + «Открыть» / «Закрыть»
    ADMIN = "admin"            # + «Советовцы»
    COUNCIL_MENU = "council_menu"  # Список / Добавить / Изменить / Удалить / Назад
    CANCEL = "cancel"          # Отмена
    CONFIRM = "confirm"        # Да / Нет


@dataclass(frozen=True)
class Reply:
    text: str
    keyboard: KeyboardKind
