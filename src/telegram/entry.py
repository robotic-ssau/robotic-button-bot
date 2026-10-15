import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from structlog import get_logger

from src.core.bootstrap import bootstrap

from .handlers import router


async def main() -> None:
    configs, service = bootstrap("telegram")
    logger = get_logger(__name__)
    if not configs.tg_bot_token:
        logger.critical("TG_BOT_TOKEN is not set")
        sys.exit(1)

    bot = Bot(configs.tg_bot_token, session=AiohttpSession())
    dp = Dispatcher(service=service)
    dp.include_routers(router)
    try:
        me = await bot.get_me()
        logger.info("Telegram bot authorized", bot_username=me.username, bot_id=me.id)
        await bot.delete_webhook()
        logger.info("Start polling")
        await dp.start_polling(bot)
    except Exception:
        logger.exception("Telegram bot crashed")
        raise
    finally:
        logger.info("Telegram bot stopped")
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
