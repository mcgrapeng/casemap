"""FastAPI app factory for casemap server (SP-2)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from casemap.server.config import get_settings
from casemap.server.db import get_engine
from casemap.server.models import Base
from casemap.server.routers import brain_map, cases, ci, projects, statuses
from casemap.server.routers import specs as specs_router

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    settings = get_settings()
    # ponytail: create_all() at startup is enough for v1; Alembic when schemas
    # change. Cheaper than Alembic for an MVP and avoids the migration-tool tax.
    Base.metadata.create_all(get_engine())

    app = FastAPI(
        title="casemap server",
        version="0.2.0",
        description="REST API + persistence for casemap brain maps.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS — wide-open for dev; restrict at deploy.
    origins = settings.cors_origins if settings.cors_origins != ["*"] else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", include_in_schema=False)
    def _root() -> FileResponse:
        index = STATIC_DIR / "index.html"
        return FileResponse(index)

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # REST API
    api_prefix = "/api/v1"
    app.include_router(projects.router, prefix=api_prefix)
    app.include_router(specs_router.router, prefix=api_prefix)
    app.include_router(brain_map.router, prefix=api_prefix)
    app.include_router(cases.router, prefix=api_prefix)
    app.include_router(statuses.router, prefix=api_prefix)
    app.include_router(ci.router, prefix=api_prefix)

    return app


# Module-level app for `uvicorn casemap.server.app:app`.
# ponytail: conftest fixtures swap db_module.engine BEFORE create_app() runs
# in tests, so tables get created on the test engine.
__all__ = ["app", "create_app"]

# Imported lazily to keep create_app() explicit to first use.
app = create_app()
