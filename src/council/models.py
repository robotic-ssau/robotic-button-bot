from dataclasses import dataclass
from enum import Enum


class Platform(Enum):
    TG = "telegram"
    VK = "vk"


@dataclass(frozen=True)
class CouncilMember:
    surname: str
    vk_id: int | None
    tg_id: int | None
    is_admin: bool = False

    def platform_id(self, platform: Platform) -> int | None:
        return self.vk_id if platform is Platform.VK else self.tg_id

    def as_log_dict(self) -> dict[str, object]:
        return {
            "surname": self.surname,
            "vk_id": self.vk_id,
            "tg_id": self.tg_id,
            "is_admin": self.is_admin,
        }
