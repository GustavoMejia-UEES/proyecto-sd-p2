from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status

from app.database import get_collection
from app.schemas import EventType, TaskCreate, TaskPriority, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _serialize(task: dict) -> dict:
    task.pop("_id", None)
    return task


def _task_priority(event_type: EventType) -> TaskPriority:
    if event_type in ("camera_offline", "camera_degraded", "object_detected"):
        return "high"
    if event_type == "person":
        return "medium"
    return "low"


def create_task_from_event(event: dict) -> tuple[dict, bool] | None:
    """Keep one active alert per camera/object and preserve its occurrences."""
    event_type = event["type"]
    object_name = event.get("object_name") or "general"
    alert_key = f"{event['camera_id']}:{event_type}:{object_name}"
    collection = get_collection("tasks")
    duplicate = collection.find_one(
        {
            "source": "camera",
            "alert_key": alert_key,
            "estado": {"$ne": "Completada"},
        }
    )
    if duplicate:
        now = now_iso()
        update = {
            "last_event_id": event["id"],
            "last_seen_at": now,
            "occurrences": duplicate.get("occurrences", 1) + 1,
            "updated_at": now,
        }
        collection.update_one({"id": duplicate["id"]}, {"$set": update})
        duplicate.update(update)
        return _serialize(duplicate), False

    now = now_iso()
    description = event.get("description") or f"Evento {event_type} detectado"
    task = {
        "id": f"TASK-{uuid4().hex[:8].upper()}",
        "titulo": description,
        "estado": "Pendiente",
        "source": "camera",
        "camera_id": event["camera_id"],
        "event_id": event["id"],
        "event_type": event_type,
        "alert_key": alert_key,
        "occurrences": 1,
        "last_event_id": event["id"],
        "last_seen_at": now,
        "priority": _task_priority(event_type),
        "created_at": now,
        "updated_at": now,
    }
    collection.insert_one(task)
    return _serialize(task), True


@router.get("")
def list_tasks(
    task_status: str | None = Query(default=None, alias="estado"),
    source: str | None = None,
    camera_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    query = {
        key: value
        for key, value in {
            "estado": task_status,
            "source": source,
            "camera_id": camera_id,
        }.items()
        if value is not None
    }
    tasks = list(
        get_collection("tasks").find(query).sort("updated_at", -1).limit(limit)
    )
    return [_serialize(task) for task in tasks]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate):
    collection = get_collection("tasks")
    now = now_iso()
    task = {
        "id": f"TASK-{uuid4().hex[:8].upper()}",
        **payload.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    collection.insert_one(task)
    return _serialize(task)


@router.get("/{task_id}")
def get_task(task_id: str):
    task = get_collection("tasks").find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize(task)


@router.patch("/{task_id}")
def update_task(task_id: str, payload: TaskUpdate):
    updates = {
        key: value
        for key, value in payload.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if not updates:
        return get_task(task_id)

    updates["updated_at"] = now_iso()
    result = get_collection("tasks").update_one(
        {"id": task_id}, {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return get_task(task_id)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str):
    result = get_collection("tasks").delete_one({"id": task_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
