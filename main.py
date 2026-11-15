
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.routers import (ai, auth, customers, dashboard, health, invoices,
                         khata, payments, products, transactions, voice)
from app.utils.responses import ERROR_MARKER

logger = logging.getLogger("vyapaar_sathi")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from sqlalchemy import text
    from app.database import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Connected to PostgreSQL at %s:%s/%s",
                    settings.DB_HOST, settings.DB_PORT, settings.DB_NAME)
    except Exception as exc:
        logger.error("Could not connect to PostgreSQL: %s", exc)
        raise

    yield
    engine.dispose()
    logger.info("Database connection pool closed.")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: allow Arshpreet's Next.js dev server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Error handling: predictable JSON for every failure ----
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict) and ERROR_MARKER in exc.detail:
        code, message, details = exc.detail[ERROR_MARKER]
        error = {"code": code, "message": message}
        if details is not None:
            error["details"] = details
        return JSONResponse(status_code=exc.status_code,
                            content={"success": False, "error": error})
    return JSONResponse(status_code=exc.status_code,
                        content={"success": False,
                                 "error": {"code": "HTTP_ERROR", "message": str(exc.detail)}})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "One or more fields failed validation.",
                "details": exc.errors(),
            },
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {"code": "INTERNAL_SERVER_ERROR",
                      "message": "Something went wrong on the server."},
        },
    )

app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(customers.router, prefix=settings.API_PREFIX)
app.include_router(products.router, prefix=settings.API_PREFIX)
app.include_router(transactions.router, prefix=settings.API_PREFIX)
app.include_router(payments.router, prefix=settings.API_PREFIX)
app.include_router(khata.router, prefix=settings.API_PREFIX)
app.include_router(voice.router, prefix=settings.API_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_PREFIX)
app.include_router(invoices.router, prefix=settings.API_PREFIX)
app.include_router(ai.router, prefix=settings.API_PREFIX)


@app.get("/", tags=["Root"])
def root():
    return {"success": True,
            "data": {"app": settings.APP_NAME, "version": "1.0.0", "docs": "/docs"}}