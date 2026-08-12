from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status

from app.database import get_collection
from app.schemas import TaskCreate, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _serialize(task: dict) -> dict:
    task.pop("_id", None)
    return task


@router.get("")
def list_tasks(task_status: str | None = Query(default=None, alias="estado")):
    query = {"estado": task_status} if task_status else {}
    tasks = list(get_collection("tasks").find(query).sort("created_at", -1))
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
