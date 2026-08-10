from fastapi import FastAPI

app = FastAPI(
    title="ARGUS Core API",
    version="0.1.0"
)

@app.get("/")
def root():
    return {
        "system": "ARGUS",
        "service": "core-api",
        "status": "online"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }