from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import APP_ENV
from app.database import check_database, get_collection
from app.realtime import event_manager

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/summary")
def system_summary():
    cameras = list(get_collection("cameras").find({}, {"_id": 0}))
    online = sum(1 for camera in cameras if camera.get("status") == "online")
    start_of_day = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()
    events_today = get_collection("events").count_documents(
        {"timestamp": {"$gte": start_of_day}}
    )
    return {
        "system": "ARGUS",
        "environment": APP_ENV,
        "cameras_total": len(cameras),
        "cameras_online": online,
        "events_today": events_today,
        "realtime_clients": len(event_manager.connections),
        "database": "connected",
    }


@router.get("/database")
def database_status():
    try:
        check_database()
        return {"status": "connected"}
    except Exception:
        return {"status": "unavailable"}
