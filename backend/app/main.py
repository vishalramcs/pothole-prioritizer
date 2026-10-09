"""SRPPS API entry point. Run from backend/:  uvicorn app.main:app --reload"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import get_settings
from app.core.db import get_engine
from app.repositories import config
from app.services import priority

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # TRD 4.5: weights are checked at startup. Bad weights stop the app; an unreachable DB does not,
    # so /api/health/db can still report it.
    try:
        with get_engine().connect() as conn:
            cfg = config.get_all(conn)
    except Exception as exc:
        logging.warning("Could not read config at startup (%s); weights not checked", type(exc).__name__)
    else:
        priority.check_weights(cfg)
    yield


app = FastAPI(title="SRPPS API", version="0.4.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


# TRD section 5: every error is { "error": "message" }, and bad input is 400 (422 means detection failed).
@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"] if p not in ("body", "query", "path", "form"))
    return JSONResponse({"error": f"{field}: {first['msg']}" if field else first["msg"]}, status_code=400)
