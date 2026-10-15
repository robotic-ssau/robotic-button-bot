import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from types import TracebackType

import structlog


class DailyFileHandler(logging.FileHandler):
    """Пишет логи в файл `<prefix>_<YYYY-MM-DD>.log` и каждый день начинает новый.

    Старые файлы удаляются через `retention_days` дней (0 — хранить все).
    """

    def __init__(self, directory: Path, prefix: str, retention_days: int = 30) -> None:
        self.directory = directory
        self.prefix = prefix
        self.retention_days = retention_days
        self.directory.mkdir(parents=True, exist_ok=True)
        self.current_date = date.today()
        super().__init__(self._path_for(self.current_date), encoding="utf-8")
        self._cleanup()

    def _path_for(self, day: date) -> Path:
        return self.directory / f"{self.prefix}_{day.isoformat()}.log"

    def emit(self, record: logging.LogRecord) -> None:
        record_date = datetime.fromtimestamp(record.created).date()
        if record_date != self.current_date:
            self._switch_to(record_date)
        super().emit(record)

    def _switch_to(self, day: date) -> None:
        if self.stream:
            self.stream.close()
            self.stream = None
        self.current_date = day
        self.baseFilename = str(self._path_for(day).resolve())
        self._cleanup()

    def _cleanup(self) -> None:
        if self.retention_days <= 0:
            return
        border = self.current_date - timedelta(days=self.retention_days)
        for file in self.directory.glob(f"{self.prefix}_*.log"):
            try:
                file_date = date.fromisoformat(file.stem.removeprefix(f"{self.prefix}_"))
            except ValueError:
                continue
            if file_date < border:
                try:
                    file.unlink()
                except OSError:
                    pass


def setup_logging(
    service_name: str,
    log_dir: Path,
    level: str = "INFO",
    retention_days: int = 30,
) -> None:
    """Логи пишутся в консоль (цветом) и в ежедневный файл logs/<service>_<дата>.log."""
    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processor=structlog.dev.ConsoleRenderer(colors=True),
    ))

    file_handler = DailyFileHandler(log_dir, service_name, retention_days)
    file_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processor=structlog.dev.ConsoleRenderer(colors=False),
    ))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Шумные библиотеки — только предупреждения
    for noisy in ("urllib3", "asyncio", "aiohttp.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    def log_uncaught(
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        structlog.get_logger("uncaught").critical(
            "Uncaught exception", exc_info=(exc_type, exc, tb)
        )

    sys.excepthook = log_uncaught
