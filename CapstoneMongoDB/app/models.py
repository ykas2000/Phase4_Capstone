import ipaddress
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeviceType(str, Enum):
    router = "router"
    switch = "switch"
    server = "server"


class DeviceStatus(str, Enum):
    online = "online"
    offline = "offline"


class DeviceCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "device_id": "R1",
                    "name": "core-router-1",
                    "device_type": "router",
                    "ip_address": "10.0.0.1",
                    "status": "online",
                    "location": "DC1 rack 4",
                }
            ]
        }
    )

    device_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    device_type: DeviceType
    ip_address: str
    status: DeviceStatus = DeviceStatus.online
    location: str | None = Field(default=None, max_length=100)

    @field_validator("ip_address")
    @classmethod
    def validate_ipv4(cls, value: str) -> str:
        try:
            return str(ipaddress.IPv4Address(value))
        except ValueError:
            raise ValueError("ip_address must be a valid IPv4 address")


class DeviceResponse(BaseModel):
    device_id: str
    name: str
    device_type: DeviceType
    ip_address: str
    status: DeviceStatus
    location: str | None = None


class StatusUpdate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "offline"}]})

    status: DeviceStatus


class AlertResponse(BaseModel):
    device_id: str
    message: str
    timestamp: datetime


class HealthResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    detail: str
