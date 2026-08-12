import os

from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "ARGUS Core API")
APP_ENV = os.getenv("APP_ENV", "development")

MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_DB = os.getenv("MONGO_DB", "argus")
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")

API_CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("API_CORS_ORIGINS", "*").split(",")
    if origin.strip()
]

CAMERA_HEARTBEAT_TIMEOUT_SECONDS = int(
    os.getenv("CAMERA_HEARTBEAT_TIMEOUT_SECONDS", "15")
)
