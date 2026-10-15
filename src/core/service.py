from structlog import get_logger
from structlog.contextvars import bound_contextvars

from src.council import CouncilMember, CouncilRepository, Platform
from src.i18n import t
from src.laba import LabApiError, LabStateApi

from .council_dialog import CouncilDialog
from .types import KeyboardKind, Reply

logger = get_logger(__name__)


class BotService:
    """Вся логика бота, не зависящая от платформы. TG и VK только передают сюда текст."""

    def __init__(self, lab_api: LabStateApi, council: CouncilRepository) -> None:
        self.lab_api = lab_api
        self.council = council
        self.dialog = CouncilDialog(council)

    # ---------- точки входа ----------

    def handle_start(self, platform: Platform, user_id: int, username: str | None = None) -> Reply:
        member = self.council.find(platform, user_id)
        with bound_contextvars(**self._context(platform, user_id, username, member)):
            logger.info("Start command")
            self.dialog.reset((platform, user_id))
            return self._reply(Reply(t("lab.start"), self.main_keyboard(member)))

    def handle_message(
        self, platform: Platform, user_id: int, text: str, username: str | None = None
    ) -> Reply | None:
        member = self.council.find(platform, user_id)
        with bound_contextvars(**self._context(platform, user_id, username, member)):
            logger.info("Incoming message", text=text)
            try:
                reply = self._dispatch(platform, user_id, text.strip(), member)
            except Exception:
                logger.exception("Failed to handle message", text=text)
                self.dialog.reset((platform, user_id))
                reply = Reply(t("common.error"), self.main_keyboard(member))
            if reply is None:
                logger.info("Message is not a command, ignored")
                return None
            return self._reply(reply)

    def main_keyboard(self, member: CouncilMember | None) -> KeyboardKind:
        if member is None:
            return KeyboardKind.USER
        return KeyboardKind.ADMIN if member.is_admin else KeyboardKind.COUNCIL

    # ---------- маршрутизация ----------

    def _dispatch(
        self, platform: Platform, user_id: int, text: str, member: CouncilMember | None
    ) -> Reply | None:
        key = (platform, user_id)
        is_admin = member is not None and member.is_admin

        if self.dialog.in_dialog(key):
            if not is_admin:
                logger.warning("User lost admin rights during council dialog")
                self.dialog.reset(key)
                return Reply(t("common.access_denied"), self.main_keyboard(member))
            return self.dialog.on_input(key, text)

        if text == t("buttons.begin"):
            return Reply(t("lab.start"), self.main_keyboard(member))
        if text == t("buttons.is_open"):
            return self._lab_state(member)
        if text in (t("buttons.open"), t("buttons.close")):
            return self._switch_lab(member, open_lab=text == t("buttons.open"))
        if text in self.dialog.menu_buttons():
            if not is_admin:
                logger.warning("Non-admin tried to use council management", button=text)
                return Reply(t("common.access_denied"), self.main_keyboard(member))
            return self.dialog.on_menu_button(key, text)
        if text == t("buttons.back"):
            return Reply(t("common.back_to_main"), self.main_keyboard(member))
        return None

    # ---------- лаборатория ----------

    def _lab_state(self, member: CouncilMember | None) -> Reply:
        keyboard = self.main_keyboard(member)
        try:
            is_open = self.lab_api.get_state()
        except LabApiError:
            return Reply(t("lab.service_unavailable"), keyboard)
        logger.info("Lab state requested", is_open=is_open)
        return Reply(t("lab.is_open" if is_open else "lab.is_closed"), keyboard)

    def _switch_lab(self, member: CouncilMember | None, open_lab: bool) -> Reply:
        keyboard = self.main_keyboard(member)
        if member is None:
            logger.warning("Not a council member tried to change lab state", open=open_lab)
            return Reply(t("common.access_denied"), keyboard)
        try:
            is_open = self.lab_api.get_state()
            if is_open == open_lab:
                logger.info("Lab state unchanged, already in requested state", is_open=is_open)
                return Reply(t("lab.already_open" if open_lab else "lab.already_closed"),
                             keyboard)
            new_state = self.lab_api.set_state(open_lab)
        except LabApiError:
            return Reply(t("lab.service_unavailable"), keyboard)
        logger.info("Lab state changed", by=member.surname, old=is_open, new=new_state)
        return Reply(t("lab.opened" if open_lab else "lab.closed"), keyboard)

    # ---------- служебное ----------

    @staticmethod
    def _context(
        platform: Platform, user_id: int, username: str | None, member: CouncilMember | None
    ) -> dict[str, object]:
        return {
            "platform": platform.value,
            "user_id": user_id,
            "username": username,
            "council": member.surname if member else None,
            "admin": bool(member and member.is_admin),
        }

    @staticmethod
    def _reply(reply: Reply) -> Reply:
        logger.info("Reply", text=reply.text, keyboard=reply.keyboard.value)
        return reply
