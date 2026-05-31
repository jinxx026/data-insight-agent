from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router


app = FastAPI(
    title="DataInsight Agent API",
    description="FastAPI backend for dataset profiling, data quality analysis, EDA planning, reports, and RAG Q&A.",
    version="0.2.0",
)

app.include_router(router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "DataInsight Agent API",
        "docs": "/docs",
        "health": "/api/health",
    }
