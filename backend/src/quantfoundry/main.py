"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy import Engine

from quantfoundry import __version__
from quantfoundry.api.plugins import router as plugins_router
from quantfoundry.api.system import router as system_router
from quantfoundry.db.session import create_database_engine, create_session_factory
from quantfoundry.errors import install_error_handlers
from quantfoundry.settings import Settings


def create_app(*, settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    runtime_settings = settings or Settings.from_env()
    runtime_engine = engine or create_database_engine(runtime_settings)

    app = FastAPI(
        title="QuantFoundry API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = runtime_settings
    app.state.engine = runtime_engine
    app.state.session_factory = create_session_factory(runtime_engine)

    install_error_handlers(app)
    app.include_router(system_router)
    app.include_router(plugins_router)

    @app.get("/api/v1/openapi.json", include_in_schema=False)
    def openapi_schema() -> dict[str, object]:
        return app.openapi()

    return app
