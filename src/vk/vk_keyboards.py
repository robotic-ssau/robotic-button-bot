from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from src.configs import consts


def get_keyboard(id: int) -> str:
    if id in consts.COUNCIL_MEMBERS_VK_IDS:
        keyboard: str = create_keyboard_council().get_keyboard()
    else:
        keyboard = create_keyboard_user().get_keyboard()
    return keyboard


def create_keyboard_user() -> VkKeyboard:
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("Лаборатория открыта?", color=VkKeyboardColor.PRIMARY)
    return keyboard


def create_keyboard_council() -> VkKeyboard:
    keyboard = create_keyboard_user()
    keyboard.add_line()
    keyboard.add_button("Закрыть", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button("Открыть", color=VkKeyboardColor.POSITIVE)
    return keyboard
