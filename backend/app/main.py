"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.routes import router as api_router

app = FastAPI(title="SentinelScrape API", version="0.1.0")
app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
