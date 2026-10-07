"""FastAPI app factory for casemap server (SP-2)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import casemap
from casemap.server import ws as ws_router
from casemap.server.config import Settings, get_settings
from casemap.server.db import get_engine
from casemap.server.models import Base
from casemap.server.routers import brain_map, cases, ci, projects, statuses
from casemap.server.routers import specs as specs_router

STATIC_DIR = Path(__file__).parent / "static"
PROJECT_ROOT = Path(casemap.__file__).resolve().parents[2]
DEFAULT_FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

# ponytail: prefixes the SPA catch-all must NOT serve — these are server-owned
# routes that have their own handlers (or should 404 if the path is unknown).
_SPA_EXCLUDED_PREFIXES = ("api/", "docs", "openapi.json", "redoc", "static/", "assets/")


def _resolve_frontend_dist(settings: Settings) -> Path | None:
    """Return the frontend dist path to serve, or None if unavailable.

    Priority: explicit `CASEMAP_FRONTEND_DIST` env var > default discovery
    (`<project_root>/frontend/dist`). The path must exist AND contain
    `index.html` to be considered available.
    """
    candidate = settings.frontend_dist_path or DEFAULT_FRONTEND_DIST
    if candidate is None:
        return None
    candidate = Path(candidate)
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    if not (candidate / "index.html").is_file():
        return None
    return candidate


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

    frontend_dist = _resolve_frontend_dist(settings)

    if frontend_dist is None:
        # No frontend build — fall back to the placeholder index + legacy /static.
        @app.get("/", include_in_schema=False)
        def _root() -> FileResponse:
            return FileResponse(STATIC_DIR / "index.html")

        if STATIC_DIR.exists():
            app.mount(
                "/static", StaticFiles(directory=str(STATIC_DIR)), name="static"
            )

    # REST API — registered FIRST so the SPA catch-all (added after) cannot
    # shadow /api/v1/*. Starlette resolves routes in registration order;
    # first match wins.
    api_prefix = "/api/v1"
    app.include_router(projects.router, prefix=api_prefix)
    app.include_router(specs_router.router, prefix=api_prefix)
    app.include_router(brain_map.router, prefix=api_prefix)
    app.include_router(cases.router, prefix=api_prefix)
    app.include_router(statuses.router, prefix=api_prefix)
    app.include_router(ci.router, prefix=api_prefix)
    app.include_router(ws_router.router, prefix=api_prefix)

    if frontend_dist is not None:
        # ponytail: SPA routes registered LAST — anything not matched by the API
        # above (or by /docs / /openapi.json built-ins) falls through here.
        assets_dir = frontend_dist / "assets"
        if assets_dir.is_dir():
            app.mount(
                "/assets",
                StaticFiles(directory=str(assets_dir)),
                name="frontend-assets",
            )
        index_file = frontend_dist / "index.html"

        @app.get("/", include_in_schema=False)
        def _spa_root() -> FileResponse:
            return FileResponse(index_file)

        @app.get("/{full_path:path}", include_in_schema=False)
        def _spa_catch_all(full_path: str) -> FileResponse:
            # Anything under server-owned prefixes must 404 normally, not
            # silently turn into the SPA shell.
            if full_path.startswith(_SPA_EXCLUDED_PREFIXES):
                raise HTTPException(status_code=404, detail="Not Found")
            return FileResponse(index_file)

    return app


# Module-level app for `uvicorn casemap.server.app:app`.
# ponytail: conftest fixtures swap db_module.engine BEFORE create_app() runs
# in tests, so tables get created on the test engine.
__all__ = ["app", "create_app"]

# Imported lazily to keep create_app() explicit to first use.
app = create_app()
