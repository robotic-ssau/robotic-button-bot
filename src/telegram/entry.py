import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from structlog import get_logger

from src.configs import Configs, setup_logging

from .handlers import router

setup_logging()
logger = get_logger()


def register_routers(dp: Dispatcher) -> None:
    dp.include_routers(router)


async def main() -> None:
    session = AiohttpSession()
    bot = Bot(Configs().tg_bot_token, session=session)
    dp = Dispatcher()
    register_routers(dp)
    try:
        await bot.delete_webhook()
        await asyncio.create_task(dp.start_polling(bot))

    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    asyncio.run(main())
