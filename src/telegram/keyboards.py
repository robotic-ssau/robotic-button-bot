from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from src.configs.consts import IS_OPEN_QUERY, TO_CLOSE_QUERY, TO_OPEN_QUERY


def user_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=IS_OPEN_QUERY)]
    ], resize_keyboard=True, one_time_keyboard=False)


def admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=IS_OPEN_QUERY)],
        [
            KeyboardButton(text=TO_OPEN_QUERY),
            KeyboardButton(text=TO_CLOSE_QUERY)
        ]
    ], resize_keyboard=True, one_time_keyboard=False)
