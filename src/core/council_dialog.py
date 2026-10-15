import threading
from dataclasses import dataclass, field
from enum import Enum, auto

from structlog import get_logger

from src.council import (
    CouncilError,
    CouncilMember,
    CouncilRepository,
    Platform,
    parse_bool,
    parse_optional_id,
)
from src.i18n import t

from .types import KeyboardKind, Reply

logger = get_logger(__name__)

DialogKey = tuple[Platform, int]


class Step(Enum):
    ADD_DATA = auto()
    EDIT_CHOOSE = auto()
    EDIT_DATA = auto()
    DELETE_CHOOSE = auto()
    DELETE_CONFIRM = auto()


@dataclass
class DialogState:
    step: Step
    snapshot: list[CouncilMember] = field(default_factory=list)
    target: CouncilMember | None = None


def format_member(member: CouncilMember, index: int | None = None) -> str:
    no_id = t("council.no_id")
    text = t(
        "council.member",
        surname=member.surname,
        vk_id=member.vk_id if member.vk_id is not None else no_id,
        tg_id=member.tg_id if member.tg_id is not None else no_id,
        admin_mark=t("council.admin_mark") if member.is_admin else "",
    )
    return text if index is None else t("council.list_item", index=index, member=text)


def format_list(members: list[CouncilMember]) -> str:
    if not members:
        return t("council.list_empty")
    lines = [t("council.list_header", count=len(members))]
    lines += [format_member(m, i) for i, m in enumerate(members, start=1)]
    return "\n".join(lines)


def member_to_line(member: CouncilMember) -> str:
    return "; ".join([
        member.surname,
        str(member.vk_id) if member.vk_id is not None else "-",
        str(member.tg_id) if member.tg_id is not None else "-",
        t("buttons.yes").lower() if member.is_admin else t("buttons.no").lower(),
    ])


def parse_member_line(text: str) -> CouncilMember:
    separator = ";" if ";" in text else ","
    parts = [p.strip() for p in text.split(separator)]
    if len(parts) == 3:
        parts.append("0")
    if len(parts) != 4:
        raise CouncilError("council.errors.format", format=t("council.input_format"))
    surname, vk_raw, tg_raw, admin_raw = parts
    if not surname:
        raise CouncilError("council.errors.surname")
    try:
        vk_id = parse_optional_id(vk_raw)
    except ValueError:
        raise CouncilError("council.errors.vk_id") from None
    try:
        tg_id = parse_optional_id(tg_raw)
    except ValueError:
        raise CouncilError("council.errors.tg_id") from None
    if vk_id is None and tg_id is None:
        raise CouncilError("council.errors.no_ids")
    try:
        is_admin = parse_bool(admin_raw)
    except ValueError:
        raise CouncilError("council.errors.admin_flag") from None
    return CouncilMember(surname=surname, vk_id=vk_id, tg_id=tg_id, is_admin=is_admin)


class CouncilDialog:
    """Диалог админа для управления списком советовцев. Общий для TG и VK."""

    def __init__(self, repository: CouncilRepository) -> None:
        self.repository = repository
        self._states: dict[DialogKey, DialogState] = {}
        self._lock = threading.Lock()

    # ---------- состояние ----------

    def in_dialog(self, key: DialogKey) -> bool:
        with self._lock:
            return key in self._states

    def reset(self, key: DialogKey) -> None:
        with self._lock:
            if self._states.pop(key, None) is not None:
                logger.debug("Council dialog reset")

    def _set(self, key: DialogKey, state: DialogState) -> None:
        with self._lock:
            self._states[key] = state
        logger.debug("Council dialog step", step=state.step.name,
                     target=state.target.surname if state.target else None)

    def _get(self, key: DialogKey) -> DialogState | None:
        with self._lock:
            return self._states.get(key)

    # ---------- кнопки меню ----------

    def menu_buttons(self) -> set[str]:
        return {
            t("buttons.council_menu"),
            t("buttons.council_list"),
            t("buttons.council_add"),
            t("buttons.council_edit"),
            t("buttons.council_delete"),
        }

    def on_menu_button(self, key: DialogKey, text: str) -> Reply:
        self.reset(key)
        if text == t("buttons.council_list"):
            logger.info("Admin requested council list")
            return Reply(format_list(self.repository.all()), KeyboardKind.COUNCIL_MENU)
        if text == t("buttons.council_add"):
            self._set(key, DialogState(Step.ADD_DATA))
            return Reply(t("council.add_prompt", format=t("council.input_format")),
                         KeyboardKind.CANCEL)
        if text in (t("buttons.council_edit"), t("buttons.council_delete")):
            members = self.repository.all()
            if not members:
                return Reply(t("council.list_empty"), KeyboardKind.COUNCIL_MENU)
            is_edit = text == t("buttons.council_edit")
            self._set(key, DialogState(
                Step.EDIT_CHOOSE if is_edit else Step.DELETE_CHOOSE, snapshot=members
            ))
            prompt_key = "council.choose_edit" if is_edit else "council.choose_delete"
            return Reply(t(prompt_key, list=format_list(members)), KeyboardKind.CANCEL)
        # buttons.council_menu
        return Reply(t("council.menu"), KeyboardKind.COUNCIL_MENU)

    # ---------- ввод внутри диалога ----------

    def on_input(self, key: DialogKey, text: str) -> Reply:
        state = self._get(key)
        if state is None:
            return Reply(t("council.menu"), KeyboardKind.COUNCIL_MENU)

        if text in (t("buttons.cancel"), t("buttons.no"), t("buttons.back")):
            self.reset(key)
            logger.info("Admin cancelled council action", step=state.step.name)
            return Reply(t("common.cancelled"), KeyboardKind.COUNCIL_MENU)

        try:
            match state.step:
                case Step.ADD_DATA:
                    return self._add(key, text)
                case Step.EDIT_CHOOSE:
                    return self._choose(key, state, text, Step.EDIT_DATA)
                case Step.EDIT_DATA:
                    return self._edit(key, state, text)
                case Step.DELETE_CHOOSE:
                    return self._choose(key, state, text, Step.DELETE_CONFIRM)
                case Step.DELETE_CONFIRM:
                    return self._delete(key, state, text)
        except CouncilError as ex:
            logger.warning("Council action rejected", step=state.step.name,
                           reason=ex.key, input=text)
            if ex.key == "council.record_changed":
                self.reset(key)
                return Reply(t(ex.key), KeyboardKind.COUNCIL_MENU)
            keyboard = (KeyboardKind.CONFIRM if state.step is Step.DELETE_CONFIRM
                        else KeyboardKind.CANCEL)
            return Reply(t(ex.key, **ex.params), keyboard)
        raise AssertionError(f"Unknown step {state.step}")

    def _add(self, key: DialogKey, text: str) -> Reply:
        member = parse_member_line(text)
        self.repository.add(member)
        self.reset(key)
        return Reply(t("council.added", member=format_member(member)),
                     KeyboardKind.COUNCIL_MENU)

    def _choose(self, key: DialogKey, state: DialogState, text: str, next_step: Step) -> Reply:
        raw = text.strip().rstrip(".")
        if not raw.isdigit() or not 1 <= int(raw) <= len(state.snapshot):
            raise CouncilError("council.bad_index", max=len(state.snapshot))
        target = state.snapshot[int(raw) - 1]
        self._set(key, DialogState(next_step, snapshot=state.snapshot, target=target))
        if next_step is Step.EDIT_DATA:
            return Reply(t("council.edit_prompt",
                           member=format_member(target),
                           format=t("council.input_format"),
                           current_line=member_to_line(target)),
                         KeyboardKind.CANCEL)
        return Reply(t("council.confirm_delete", member=format_member(target)),
                     KeyboardKind.CONFIRM)

    def _edit(self, key: DialogKey, state: DialogState, text: str) -> Reply:
        assert state.target is not None
        new_member = parse_member_line(text)
        self.repository.update(state.target, new_member)
        self.reset(key)
        return Reply(t("council.updated",
                       old=format_member(state.target),
                       new=format_member(new_member)),
                     KeyboardKind.COUNCIL_MENU)

    def _delete(self, key: DialogKey, state: DialogState, text: str) -> Reply:
        assert state.target is not None
        if text != t("buttons.yes"):
            return Reply(t("council.confirm_delete", member=format_member(state.target)),
                         KeyboardKind.CONFIRM)
        self.repository.delete(state.target)
        self.reset(key)
        return Reply(t("council.deleted", member=format_member(state.target)),
                     KeyboardKind.COUNCIL_MENU)
