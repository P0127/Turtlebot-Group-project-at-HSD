"""FastAPI application setup (routers, middleware, lifespan)."""
from contextlib import asynccontextmanager
import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import control, stt, tts, state
from app.core.controller import controller

logger = logging.getLogger("backend.api.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug("App lifespan start")
    yield
    logger.debug("App lifespan shutdown")
    controller.shutdown()


def create_api_app() -> FastAPI:
    # Load backend/.env if present (useful for local dev & WSL)
    load_dotenv()

    app = FastAPI(title="Robot Control Backend", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for now -> Should be changed later on
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(control.router, prefix="/api/v1/control", tags=["control"])
    app.include_router(stt.router, prefix="/api/v1/stt", tags=["stt"])
    app.include_router(tts.router, prefix="/api/v1/tts", tags=["tts"])
    app.include_router(state.router, prefix="/api/v1/state", tags=["state"])

    @app.get("/")
    def root():
        return {"name": "Robot Control Backend", "docs": "/docs"}

    return app
