import asyncio

from aiogram import F, types
from aiogram.dispatcher.router import Router
from aiogram.filters import CommandStart
from aiogram.types import ErrorEvent
from structlog import get_logger

from src.core import BotService
from src.council import Platform
from src.i18n import t

from .keyboards import build_keyboard

logger = get_logger(__name__)
router = Router()


@router.message(CommandStart())
async def start(msg: types.Message, service: BotService) -> None:
    if msg.from_user is None:
        return
    reply = await asyncio.to_thread(
        service.handle_start, Platform.TG, msg.from_user.id, msg.from_user.username
    )
    await msg.answer(reply.text, reply_markup=build_keyboard(reply.keyboard))


@router.message(F.text)
async def text_message(msg: types.Message, service: BotService) -> None:
    if msg.from_user is None or msg.text is None:
        return
    reply = await asyncio.to_thread(
        service.handle_message,
        Platform.TG,
        msg.from_user.id,
        msg.text,
        msg.from_user.username,
    )
    if reply is not None:
        await msg.answer(reply.text, reply_markup=build_keyboard(reply.keyboard))


@router.errors()
async def on_error(event: ErrorEvent) -> None:
    message = event.update.message
    logger.exception(
        "Unhandled error in telegram handler",
        update_id=event.update.update_id,
        user_id=message.from_user.id if message and message.from_user else None,
        text=message.text if message else None,
        exc_info=event.exception,
    )
    if message is not None:
        try:
            await message.answer(t("common.error"))
        except Exception:
            logger.exception("Failed to send error message")
