from structlog import get_logger

from src.configs import Configs, get_configs, setup_logging
from src.council import CouncilRepository
from src.i18n import init_localization
from src.laba import LabStateApi

from .service import BotService


def bootstrap(service_name: str) -> tuple[Configs, BotService]:
    """Общий запуск для обоих ботов: конфиг, логи, локализация, список совета."""
    configs = get_configs()
    setup_logging(
        service_name=service_name,
        log_dir=configs.log_dir,
        level=configs.log_level,
        retention_days=configs.log_retention_days,
    )
    logger = get_logger(__name__)
    logger.info(
        "Bot starting",
        service=service_name,
        back_url=configs.back_url,
        council_csv=str(configs.council_csv),
        locale=configs.locale,
        log_dir=str(configs.log_dir),
        log_level=configs.log_level,
        log_retention_days=configs.log_retention_days,
    )
    init_localization(configs.locale)
    service = BotService(
        lab_api=LabStateApi(configs.back_url, timeout=configs.lab_api_timeout),
        council=CouncilRepository(configs.council_csv),
    )
    return configs, service
