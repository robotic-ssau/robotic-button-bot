from structlog import get_logger
from vk_api import VkApi
from vk_api.longpoll import VkEventType, VkLongPoll
from vk_keyboards import get_keyboard

from src.configs import Configs, consts, setup_logging
from src.laba import BotType, lab_is_open_answer, lab_switch_state_answer

setup_logging()
logger = get_logger()


def main() -> None:
    logger.info("Start initializing bot")
    TOKEN = Configs().vk_bot_token
    vk_session = VkApi(token=TOKEN)
    vk = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)
    logger.info("Start bot polling")
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            logger.info("New message catched")
            match event.text:
                case consts.BEGIN_TEXT:
                    response = consts.START_TEXT
                case consts.IS_OPEN_QUERY:
                    response = lab_is_open_answer()
                case consts.TO_OPEN_QUERY:
                    response = lab_switch_state_answer(
                        open=True,
                        user_id=event.user_id,
                        bot_type=BotType.vk
                    )
                case consts.TO_CLOSE_QUERY:
                    response = lab_switch_state_answer(
                        open=False,
                        user_id=event.user_id,
                        bot_type=BotType.vk
                    )
                case _:
                    logger.info("Got not a command, continue")
                    continue
            if response:
                logger.info("Got answer, sending a message")
                vk.messages.send(
                    user_id=event.user_id,
                    message=response,
                    keyboard=get_keyboard(event.user_id),
                    random_id=0
                )
                logger.info("Message sent")


if __name__ == "__main__":
    main()
