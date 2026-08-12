from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status

from app.database import get_collection
from app.realtime import event_manager
from app.routes.tasks import create_task_from_event
from app.schemas import EventCreate, EventUpdate

router = APIRouter(prefix="/api/events", tags=["events"])


def now_iso():
    return datetime.now(timezone.utc).isoformat()


@router.get("")
def list_events(
    camera_id: str | None = None,
    event_type: str | None = Query(default=None, alias="type"),
    event_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
):
    query = {
        key: value
        for key, value in {
            "camera_id": camera_id,
            "type": event_type,
            "status": event_status,
        }.items()
        if value is not None
    }
    events = list(
        get_collection("events")
        .find(query)
        .sort("timestamp", -1)
        .limit(limit)
    )
    for event in events:
        event.pop("_id", None)
    return events


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_event(payload: EventCreate):
    if not get_collection("cameras").find_one({"id": payload.camera_id}):
        raise HTTPException(status_code=404, detail="Camera not found")

    event = {
        "id": f"EVT-{uuid4().hex[:10].upper()}",
        **payload.model_dump(),
        "status": "new",
        "timestamp": now_iso(),
        "updated_at": now_iso(),
    }
    get_collection("events").insert_one(event)
    event.pop("_id", None)
    task_result = create_task_from_event(event)
    await event_manager.broadcast({"type": "event_created", "event": event})
    if task_result:
        generated_task, created = task_result
        await event_manager.broadcast(
            {
                "type": "task_created" if created else "task_updated",
                "task": generated_task,
            }
        )
        event["generated_task"] = generated_task
    return event


@router.get("/{event_id}")
def get_event(event_id: str):
    event = get_collection("events").find_one({"id": event_id})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.pop("_id", None)
    return event


@router.patch("/{event_id}")
async def update_event(event_id: str, payload: EventUpdate):
    updates = {
        key: value
        for key, value in payload.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if not updates:
        return get_event(event_id)

    updates["updated_at"] = now_iso()
    result = get_collection("events").update_one(
        {"id": event_id}, {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")

    event = get_event(event_id)
    await event_manager.broadcast({"type": "event_updated", "event": event})
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: str):
    result = get_collection("events").delete_one({"id": event_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    await event_manager.broadcast({"type": "event_deleted", "event_id": event_id})
