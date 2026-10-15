import time
from typing import Any

import requests
from pydantic import BaseModel, ValidationError
from structlog import get_logger

logger = get_logger(__name__)


class StateModel(BaseModel):
    state: bool


class LabApiError(Exception):
    pass


class LabStateApi:
    """Клиент сервиса состояния лаборатории (https://github.com/Sapdotten/laba_back)."""

    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_state(self) -> bool:
        return self._request("GET", "/state")

    def set_state(self, new_state: bool) -> bool:
        return self._request("POST", "/change_state", json={"state": new_state})

    def _request(self, method: str, path: str, **kwargs: Any) -> bool:
        url = self.base_url + path
        started = time.perf_counter()
        try:
            response = requests.request(method, url, timeout=self.timeout, **kwargs)
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            response.raise_for_status()
            state: bool = StateModel.model_validate(response.json()).state
        except requests.RequestException as ex:
            logger.error("Lab API request failed", method=method, url=url,
                         error=repr(ex), payload=kwargs.get("json"))
            raise LabApiError(str(ex)) from ex
        except (ValueError, ValidationError) as ex:
            logger.error("Lab API returned unexpected body", method=method, url=url,
                         body=response.text[:500], error=repr(ex))
            raise LabApiError(str(ex)) from ex
        logger.info("Lab API request", method=method, url=url, status=response.status_code,
                    elapsed_ms=elapsed_ms, payload=kwargs.get("json"), state=state)
        return state
