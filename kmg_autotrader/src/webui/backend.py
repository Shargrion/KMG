"""Web backend using FastAPI."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/metrics")
def metrics() -> dict[str, str]:
    return {"status": "ok"}
