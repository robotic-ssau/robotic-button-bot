from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from src.core import KeyboardKind
from src.i18n import t

PRIMARY = VkKeyboardColor.PRIMARY
SECONDARY = VkKeyboardColor.SECONDARY
POSITIVE = VkKeyboardColor.POSITIVE
NEGATIVE = VkKeyboardColor.NEGATIVE

# Каждая строка — список (ключ кнопки, цвет)
LAYOUTS: dict[KeyboardKind, list[list[tuple[str, VkKeyboardColor]]]] = {
    KeyboardKind.USER: [
        [("is_open", PRIMARY)],
    ],
    KeyboardKind.COUNCIL: [
        [("is_open", PRIMARY)],
        [("close", NEGATIVE), ("open", POSITIVE)],
    ],
    KeyboardKind.ADMIN: [
        [("is_open", PRIMARY)],
        [("close", NEGATIVE), ("open", POSITIVE)],
        [("council_menu", SECONDARY)],
    ],
    KeyboardKind.COUNCIL_MENU: [
        [("council_list", PRIMARY)],
        [("council_add", POSITIVE), ("council_edit", SECONDARY), ("council_delete", NEGATIVE)],
        [("back", SECONDARY)],
    ],
    KeyboardKind.CANCEL: [
        [("cancel", SECONDARY)],
    ],
    KeyboardKind.CONFIRM: [
        [("yes", NEGATIVE), ("no", SECONDARY)],
    ],
}


def build_keyboard(kind: KeyboardKind) -> str:
    keyboard = VkKeyboard(one_time=False)
    for row_index, row in enumerate(LAYOUTS[kind]):
        if row_index:
            keyboard.add_line()
        for key, color in row:
            keyboard.add_button(t(f"buttons.{key}"), color=color)
    result: str = keyboard.get_keyboard()
    return result
