from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


CameraType = Literal["usb", "integrated", "phone", "rtsp", "ip", "virtual"]
CameraStatus = Literal["online", "offline", "degraded"]
EventType = Literal[
    "motion",
    "person",
    "object_detected",
    "camera_online",
    "camera_offline",
    "camera_degraded",
]
EventStatus = Literal["new", "acknowledged", "resolved"]


class CameraCreate(BaseModel):
    camera_id: str | None = Field(default=None, min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    type: CameraType = "virtual"
    stream_url: str | None = None
    source: str | None = None
    location: str | None = Field(default=None, max_length=150)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CameraUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: CameraType | None = None
    stream_url: str | None = None
    source: str | None = None
    location: str | None = Field(default=None, max_length=150)
    metadata: dict[str, Any] | None = None


class HeartbeatRequest(BaseModel):
    fps: float | None = Field(default=None, ge=0, le=240)
    status: CameraStatus = "online"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CameraProvisionRequest(BaseModel):
    camera_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    type: CameraType = "integrated"
    source: str = Field(default="0", min_length=1, max_length=500)
    edge_host: str = Field(default="localhost", min_length=1, max_length=255)
    edge_port: int = Field(default=8081, ge=1, le=65535)
    core_api_url: str = Field(default="http://localhost:8000", max_length=500)
    iot_segment: str = Field(default="iot-cameras", min_length=1, max_length=100)
    enabled: bool = True
    location: str | None = Field(default=None, max_length=150)


class EventCreate(BaseModel):
    camera_id: str = Field(min_length=1)
    type: EventType
    confidence: float | None = Field(default=None, ge=0, le=1)
    object_name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    snapshot_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventUpdate(BaseModel):
    status: EventStatus | None = None
    description: str | None = Field(default=None, max_length=500)
    object_name: str | None = Field(default=None, max_length=100)
    metadata: dict[str, Any] | None = None


class ApiDocument(BaseModel):
    model_config = ConfigDict(extra="allow")
