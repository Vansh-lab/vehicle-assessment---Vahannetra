from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vahannetra.backend.app.core.settings import settings
from vahannetra.backend.app.routers import analyze_router, health_router, system_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "VahanNetra backend foundation up", "docs": "/docs"}


app.include_router(health_router)
app.include_router(system_router)
app.include_router(analyze_router)
