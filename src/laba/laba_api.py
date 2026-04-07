import json

import requests
from pydantic import BaseModel


class StateModel(BaseModel):
    state: bool


class LabStateApi:

    @classmethod
    def get_state(cls) -> bool:
        return StateModel(**json.loads(requests.get(cls.URL + "/state").text)).state

    @classmethod
    def set_state(cls, new_state: bool) -> bool:
        return StateModel(
            **json.loads(
                requests.post(
                    cls.URL + "/change_state",
                    json={"state": new_state}
                ).text
            )
        ).state
