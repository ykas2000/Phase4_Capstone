import ipaddress
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


DeviceType = Literal["router", "switch", "server"]
DeviceStatus = Literal["online", "offline"]


class DeviceCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "device_id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "Core router",
                    "device_type": "router",
                    "ip_address": "192.168.1.1",
                    "status": "online",
                }
            ]
        }
    )

    device_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=100)
    device_type: DeviceType
    ip_address: str
    status: DeviceStatus = "online"

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, value: str) -> str:
        try:
            ipaddress.IPv4Address(value)
        except ipaddress.AddressValueError as error:
            raise ValueError("ip_address must be a valid IPv4 address") from error
        return value


class DeviceResponse(DeviceCreate):
    pass


class StatusUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"status": "offline"}]}
    )

    status: DeviceStatus


class AlertResponse(BaseModel):
    device_id: UUID
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"