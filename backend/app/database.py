from pymongo import MongoClient

from app.config import (
    MONGO_DB,
    MONGO_HOST,
    MONGO_PASSWORD,
    MONGO_PORT,
    MONGO_USER,
)

if MONGO_USER and MONGO_PASSWORD:
    MONGO_URI = (
        f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}"
        f"@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}"
        "?authSource=admin"
    )
else:
    MONGO_URI = f"mongodb://{MONGO_HOST}:{MONGO_PORT}"

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=3000,
)

db = client[MONGO_DB]


def check_database():
    client.admin.command("ping")
    return True


def get_collection(name):
    """Return a MongoDB collection from the configured ARGUS database."""
    return db[name]
