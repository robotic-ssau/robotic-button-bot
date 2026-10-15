from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from src.core import KeyboardKind
from src.i18n import t


def _button(key: str) -> KeyboardButton:
    return KeyboardButton(text=t(f"buttons.{key}"))


def build_keyboard(kind: KeyboardKind) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]]
    match kind:
        case KeyboardKind.USER:
            rows = [[_button("is_open")]]
        case KeyboardKind.COUNCIL:
            rows = [[_button("is_open")], [_button("open"), _button("close")]]
        case KeyboardKind.ADMIN:
            rows = [
                [_button("is_open")],
                [_button("open"), _button("close")],
                [_button("council_menu")],
            ]
        case KeyboardKind.COUNCIL_MENU:
            rows = [
                [_button("council_list")],
                [_button("council_add"), _button("council_edit"), _button("council_delete")],
                [_button("back")],
            ]
        case KeyboardKind.CANCEL:
            rows = [[_button("cancel")]]
        case KeyboardKind.CONFIRM:
            rows = [[_button("yes"), _button("no")]]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=False)
