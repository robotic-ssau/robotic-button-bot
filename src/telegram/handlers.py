import keyboards
from aiogram import F, types
from aiogram.dispatcher.router import Router
from aiogram.filters import Command

from src.configs.consts import (
    COUNCIL_MEMBERS_TG_IDS,
    IS_OPEN_QUERY,
    START_TEXT,
    TO_CLOSE_QUERY,
    TO_OPEN_QUERY,
)
from src.laba import BotType, lab_is_open_answer, lab_switch_state_answer

router = Router()


@router.message(Command(commands=["start"]))
async def start(msg: types.Message) -> None:
    if msg.from_user.id in COUNCIL_MEMBERS_TG_IDS:
        keyboard = keyboards.admin_keyboard()
    else:
        keyboard = keyboards.user_keyboard()
    await msg.answer(START_TEXT, reply_markup=keyboard)


@router.message(F.text == TO_OPEN_QUERY)
async def open_lab(msg: types.Message) -> None:
    await msg.answer(lab_switch_state_answer(True, msg.from_user.id, BotType.tg))


@router.message(F.text == TO_CLOSE_QUERY)
async def close_lab(msg: types.Message) -> None:
    await msg.answer(lab_switch_state_answer(False, msg.from_user.id, BotType.tg))


@router.message(F.text == IS_OPEN_QUERY)
async def get_lab_state(msg: types.Message) -> None:
    await msg.answer(lab_is_open_answer())
