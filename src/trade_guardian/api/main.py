from fastapi import FastAPI

from trade_guardian.api import api_router
from trade_guardian.api.routes.health import router as health_router
from trade_guardian.utils.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="Trade Guardian",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Routers
    api_router.include_router(health_router)
    app.include_router(api_router, prefix="")

    return app


app = create_app()


