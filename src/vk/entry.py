import sys
import time

import requests
from structlog import get_logger
from structlog.contextvars import bound_contextvars
from vk_api import VkApi
from vk_api.exceptions import ApiError
from vk_api.longpoll import Event, VkEventType, VkLongPoll
from vk_api.utils import get_random_id

from src.core import BotService
from src.core.bootstrap import bootstrap
from src.council import Platform
from src.i18n import t

from .vk_keyboards import build_keyboard

RECONNECT_DELAY_SECONDS = 5

logger = get_logger(__name__)


def send(vk: object, user_id: int, text: str, keyboard: str) -> None:
    vk.messages.send(  # type: ignore[attr-defined]
        user_id=user_id,
        message=text,
        keyboard=keyboard,
        random_id=get_random_id(),
    )
    logger.debug("Message sent", user_id=user_id)


def process_event(event: Event, vk: object, service: BotService) -> None:
    user_id: int = event.user_id
    text: str = event.text or ""
    with bound_contextvars(vk_message_id=getattr(event, "message_id", None)):
        try:
            reply = service.handle_message(Platform.VK, user_id, text)
            if reply is not None:
                send(vk, user_id, reply.text, build_keyboard(reply.keyboard))
        except Exception:
            logger.exception("Failed to process VK message", user_id=user_id, text=text)
            try:
                member = service.council.find(Platform.VK, user_id)
                send(vk, user_id, t("common.error"),
                     build_keyboard(service.main_keyboard(member)))
            except Exception:
                logger.exception("Failed to send error message", user_id=user_id)


def main() -> None:
    configs, service = bootstrap("vk")
    if not configs.vk_bot_token:
        logger.critical("VK_BOT_TOKEN is not set")
        sys.exit(1)

    vk_session = VkApi(token=configs.vk_bot_token)
    vk = vk_session.get_api()

    while True:
        try:
            longpoll = VkLongPoll(vk_session)
            logger.info("Start VK long polling")
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    process_event(event, vk, service)
        except KeyboardInterrupt:
            logger.info("VK bot stopped by user")
            break
        except (requests.RequestException, ApiError):
            logger.exception("VK long polling failed, reconnecting",
                             delay_seconds=RECONNECT_DELAY_SECONDS)
            time.sleep(RECONNECT_DELAY_SECONDS)
        except Exception:
            logger.exception("Unexpected error in VK bot, reconnecting",
                             delay_seconds=RECONNECT_DELAY_SECONDS)
            time.sleep(RECONNECT_DELAY_SECONDS)


if __name__ == "__main__":
    main()
