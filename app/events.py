from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable, List

from pydantic import BaseModel, Field

from app.models import AlertResponse

if TYPE_CHECKING:
    from app.repositories.device_repository import InMemoryDeviceRepository


def create_offline_alert(
    repository: "InMemoryDeviceRepository", device_id: str
) -> None:
    alert = AlertResponse(
        device_id=device_id,
        message=f"Device {device_id} went offline.",
        timestamp=datetime.now(timezone.utc),
    )
    repository.save_alert(alert)


class DeviceEvent(BaseModel):
    event_type: str
    device_id: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


EventHandler = Callable[[DeviceEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: List[EventHandler] = []

    def subscribe(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    def publish(self, event: DeviceEvent) -> None:
        for handler in self._handlers:
            handler(event)