from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import API_CORS_ORIGINS, APP_ENV, APP_NAME
from app.database import check_database
from app.routes import cameras, events, system, tasks
from app.realtime import event_manager

app = FastAPI(
    title=APP_NAME,
    version="0.4.0",
    description="ARGUS distributed vision and device monitoring core API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=API_CORS_ORIGINS,
    allow_credentials=API_CORS_ORIGINS != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cameras.router)
app.include_router(events.router)
app.include_router(system.router)
app.include_router(tasks.router)


@app.get("/")
def root():
    return {
        "system": "ARGUS",
        "service": "core-api",
        "environment": APP_ENV,
        "status": "online"
    }


@app.get("/health")
def health():
    try:
        check_database()

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "database": "unavailable"
            }
        )


@app.websocket("/ws/events")
async def events_websocket(websocket):
    await event_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        event_manager.disconnect(websocket)
