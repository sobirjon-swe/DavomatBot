import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from api.deps import close_bot
from api.routes_employees import router as employees_router
from api.routes_me import router as me_router
from api.routes_reports import router as reports_router
from database.session import close_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API ishga tushdi")
    yield
    # Bot sessiyasi va baza puli ataylab shu yerda yopiladi: ular jarayon
    # davomida qayta ishlatiladi va uvicorn to'xtaganda ochiq qolmasligi kerak.
    await close_bot()
    await close_engine()


def create_app() -> FastAPI:
    config.validate()

    app = FastAPI(
        title="DavomatBot API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )

    if config.CORS_ORIGINS:
        # Prodda Mini App Telegram ichida ochiladi va CORS kerak emas;
        # bu faqat lokal `vite dev` uchun.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.CORS_ORIGINS,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    for router in (me_router, employees_router, reports_router):
        app.include_router(router, prefix="/api")

    return app


app = create_app()
