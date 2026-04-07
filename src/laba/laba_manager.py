from enum import Enum

from structlog import get_logger

from src.configs.consts import (
    ACCESS_DENIED_ANSWER,
    CLOSE_ALREADY_ANSWER,
    COUNCIL_MEMBERS_TG_IDS,
    COUNCIL_MEMBERS_VK_IDS,
    IS_CLOSE_ANSWER,
    IS_OPEN_ANSWER,
    OPEN_ALREADY_ANSWER,
    TO_CLOSE_ANSWER,
    TO_OPEN_ANSWER,
)

from .laba_api import LabStateApi

logger = get_logger()


class BotType(Enum):
    tg = 'telegram'
    vk = 'vk'


def lab_is_open_answer() -> str:
    logger.info("Lab is open answering")
    if LabStateApi.get_state():
        return IS_OPEN_ANSWER
    return IS_CLOSE_ANSWER


def lab_switch_state_answer(open: bool, user_id: int, bot_type: BotType) -> str:
    logger.info("Change state answering")
    if (
        user_id not in COUNCIL_MEMBERS_VK_IDS and bot_type == BotType.vk
        or user_id not in COUNCIL_MEMBERS_TG_IDS and bot_type == BotType.tg
    ):
        logger.warning("Not a council member tried to change state")
        return ACCESS_DENIED_ANSWER

    opened = LabStateApi.get_state()
    logger.info("Got lab state", state=opened)
    if open and opened:
        return OPEN_ALREADY_ANSWER
    elif open and not opened:
        LabStateApi.set_state(open)
        return TO_OPEN_ANSWER
    elif not open and opened:
        LabStateApi.set_state(open)
        return TO_CLOSE_ANSWER
    return CLOSE_ALREADY_ANSWER
