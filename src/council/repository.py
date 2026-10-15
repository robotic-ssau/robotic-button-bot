import csv
import os
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from structlog import get_logger

from .models import CouncilMember, Platform

logger = get_logger(__name__)

FIELDNAMES = ("surname", "vk_id", "tg_id", "is_admin")
TRUE_VALUES = {"1", "true", "yes", "y", "да", "д", "+", "admin", "админ"}
FALSE_VALUES = {"0", "false", "no", "n", "нет", "н", "-", ""}


class CouncilError(Exception):
    """Ошибка изменения списка. `key` — ключ локализации, `params` — подстановки."""

    def __init__(self, key: str, **params: object) -> None:
        super().__init__(key)
        self.key = key
        self.params = params


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"Not a boolean: {value!r}")


def parse_optional_id(value: str) -> int | None:
    normalized = value.strip().lower().removeprefix("@").removeprefix("id")
    if normalized in ("", "-", "—"):
        return None
    if not normalized.isdigit():
        raise ValueError(f"Not an id: {value!r}")
    return int(normalized)


class CouncilRepository:
    """Список советовцев в CSV-файле.

    Файл перечитывается автоматически, если изменился на диске (его могли поправить
    руками или через бота на другой платформе). Изменения пишутся атомарно,
    под файловой блокировкой, чтобы TG- и VK-боты не затёрли правки друг друга.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock_path = path.with_name(path.name + ".lock")
        self._thread_lock = threading.RLock()
        self._members: list[CouncilMember] = []
        self._mtime: float | None = None
        if not self.path.exists():
            logger.warning("Council file not found, creating empty one", path=str(path))
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._write([])
        self._reload_if_changed()

    # ---------- чтение ----------

    def all(self) -> list[CouncilMember]:
        with self._thread_lock:
            self._reload_if_changed()
            return list(self._members)

    def find(self, platform: Platform, user_id: int) -> CouncilMember | None:
        for member in self.all():
            if member.platform_id(platform) == user_id:
                return member
        return None

    def _reload_if_changed(self) -> None:
        try:
            mtime = self.path.stat().st_mtime
        except FileNotFoundError:
            logger.error("Council file disappeared", path=str(self.path))
            self._members, self._mtime = [], None
            return
        if mtime == self._mtime:
            return
        self._members = self._read()
        self._mtime = mtime
        logger.info(
            "Council list loaded",
            path=str(self.path),
            members=len(self._members),
            admins=sum(m.is_admin for m in self._members),
        )

    def _read(self) -> list[CouncilMember]:
        members: list[CouncilMember] = []
        with self.path.open(encoding="utf-8-sig", newline="") as file:
            sample = file.read(2048)
            file.seek(0)
            try:
                dialect: type[csv.Dialect] | csv.Dialect = csv.Sniffer().sniff(
                    sample, delimiters=",;"
                )
            except csv.Error:
                dialect = csv.excel
            reader = csv.DictReader(file, dialect=dialect)
            for row in reader:
                line = reader.line_num
                try:
                    member = CouncilMember(
                        surname=(row.get("surname") or "").strip(),
                        vk_id=parse_optional_id(row.get("vk_id") or ""),
                        tg_id=parse_optional_id(row.get("tg_id") or ""),
                        is_admin=parse_bool(row.get("is_admin") or ""),
                    )
                except ValueError as ex:
                    logger.error("Bad row in council file, skipped",
                                 line=line, row=row, error=str(ex))
                    continue
                if not member.surname:
                    logger.error("Row without surname in council file, skipped",
                                 line=line, row=row)
                    continue
                members.append(member)
        return members

    # ---------- запись ----------

    def add(self, member: CouncilMember) -> None:
        def change(members: list[CouncilMember]) -> list[CouncilMember]:
            self._check_duplicates(member, members)
            return members + [member]

        self._modify(change)
        logger.info("Council member added", member=member.as_log_dict())

    def update(self, old: CouncilMember, new: CouncilMember) -> None:
        def change(members: list[CouncilMember]) -> list[CouncilMember]:
            if old not in members:
                raise CouncilError("council.record_changed")
            others = [m for m in members if m != old]
            self._check_duplicates(new, others)
            return [new if m == old else m for m in members]

        self._modify(change)
        logger.info("Council member updated",
                    old=old.as_log_dict(), new=new.as_log_dict())

    def delete(self, member: CouncilMember) -> None:
        def change(members: list[CouncilMember]) -> list[CouncilMember]:
            if member not in members:
                raise CouncilError("council.record_changed")
            return [m for m in members if m != member]

        self._modify(change)
        logger.info("Council member deleted", member=member.as_log_dict())

    @staticmethod
    def _check_duplicates(member: CouncilMember, others: list[CouncilMember]) -> None:
        for other in others:
            if member.vk_id is not None and other.vk_id == member.vk_id:
                raise CouncilError("council.errors.duplicate_vk",
                                   id=member.vk_id, surname=other.surname)
            if member.tg_id is not None and other.tg_id == member.tg_id:
                raise CouncilError("council.errors.duplicate_tg",
                                   id=member.tg_id, surname=other.surname)

    def _modify(self, change: Callable[[list[CouncilMember]], list[CouncilMember]]) -> None:
        with self._thread_lock, self._file_lock():
            self._mtime = None  # перечитать свежую версию с диска
            self._reload_if_changed()
            new_members = change(list(self._members))
            if self._members and not any(m.is_admin for m in new_members):
                raise CouncilError("council.errors.last_admin")
            self._write(new_members)
            self._members = new_members
            self._mtime = self.path.stat().st_mtime

    def _write(self, members: list[CouncilMember]) -> None:
        tmp_path = self.path.with_name(self.path.name + ".tmp")
        with tmp_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(FIELDNAMES)
            for m in members:
                writer.writerow([
                    m.surname,
                    "" if m.vk_id is None else m.vk_id,
                    "" if m.tg_id is None else m.tg_id,
                    int(m.is_admin),
                ])
        os.replace(tmp_path, self.path)

    @contextmanager
    def _file_lock(self, timeout: float = 10.0, stale_after: float = 30.0) -> Iterator[None]:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fd = os.open(self._lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError:
                try:
                    age = time.time() - self._lock_path.stat().st_mtime
                    if age > stale_after:
                        logger.warning("Removing stale council lock file", age=round(age, 1))
                        self._lock_path.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() > deadline:
                    raise TimeoutError(f"Could not lock {self._lock_path}") from None
                time.sleep(0.1)
        try:
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            yield
        finally:
            self._lock_path.unlink(missing_ok=True)
