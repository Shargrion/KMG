"""Web backend using FastAPI."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/metrics")
def metrics() -> dict[str, str]:
    """Return basic health metrics for the service."""
    return {"status": "ok"}
