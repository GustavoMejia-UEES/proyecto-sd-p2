from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status

from app.config import CAMERA_HEARTBEAT_TIMEOUT_SECONDS
from app.database import get_collection
from app.realtime import event_manager
from app.schemas import CameraCreate, CameraUpdate, HeartbeatRequest

router = APIRouter(prefix="/api/cameras", tags=["cameras"])


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _camera_status(camera: dict) -> str:
    heartbeat = camera.get("last_heartbeat")
    if not heartbeat:
        return camera.get("status", "offline")

    try:
        last_seen = datetime.fromisoformat(heartbeat)
    except ValueError:
        return camera.get("status", "offline")

    if datetime.now(timezone.utc) - last_seen > timedelta(
        seconds=CAMERA_HEARTBEAT_TIMEOUT_SECONDS
    ):
        return "offline"
    return camera.get("status", "online")


def _serialize(camera: dict) -> dict:
    camera.pop("_id", None)
    camera["status"] = _camera_status(camera)
    return camera


@router.get("")
def list_cameras(
    camera_status: str | None = Query(default=None, alias="status"),
    camera_type: str | None = Query(default=None, alias="type"),
):
    query = {}
    if camera_type:
        query["type"] = camera_type

    cameras = list(get_collection("cameras").find(query).sort("name", 1))
    serialized = [_serialize(camera) for camera in cameras]
    if camera_status:
        serialized = [
            camera for camera in serialized if camera["status"] == camera_status
        ]
    return serialized


@router.post("", status_code=status.HTTP_201_CREATED)
def create_camera(payload: CameraCreate):
    collection = get_collection("cameras")
    camera_id = payload.camera_id or f"CAM-{uuid4().hex[:8].upper()}"
    if collection.find_one({"id": camera_id}):
        raise HTTPException(status_code=409, detail="Camera already exists")
    now = now_iso()
    camera = {
        "id": camera_id,
        **payload.model_dump(exclude={"camera_id"}),
        "status": "offline",
        "fps": None,
        "last_heartbeat": None,
        "created_at": now,
        "updated_at": now,
    }
    collection.insert_one(camera)
    camera.pop("_id", None)
    return camera


@router.get("/{camera_id}")
def get_camera(camera_id: str):
    camera = get_collection("cameras").find_one({"id": camera_id})
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return _serialize(camera)


@router.patch("/{camera_id}")
def update_camera(camera_id: str, payload: CameraUpdate):
    collection = get_collection("cameras")
    updates = {
        key: value
        for key, value in payload.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if not updates:
        return get_camera(camera_id)

    updates["updated_at"] = now_iso()
    result = collection.update_one({"id": camera_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Camera not found")
    return get_camera(camera_id)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(camera_id: str):
    result = get_collection("cameras").delete_one({"id": camera_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Camera not found")


@router.post("/{camera_id}/heartbeat")
async def camera_heartbeat(camera_id: str, payload: HeartbeatRequest):
    collection = get_collection("cameras")
    camera = collection.find_one({"id": camera_id})
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    previous_status = _camera_status(camera)
    heartbeat_time = now_iso()
    updates = {
        "status": payload.status,
        "fps": payload.fps,
        "last_heartbeat": heartbeat_time,
        "updated_at": heartbeat_time,
    }
    if payload.metadata:
        updates["metadata"] = {**camera.get("metadata", {}), **payload.metadata}

    collection.update_one({"id": camera_id}, {"$set": updates})
    updated = get_camera(camera_id)

    if previous_status != payload.status:
        event_type = f"camera_{payload.status}"
        await event_manager.broadcast(
            {"type": "camera_status", "camera": updated, "event": event_type}
        )
    return updated
