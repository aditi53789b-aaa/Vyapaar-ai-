import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
import app.models # registers all models
from app.services.government.sync_service import sync_government_schemes
from app.routers import (
    auth_router,
    business_router,
    customers_router,
    transactions_router,
    invoices_router,
    voice_router,
    dashboard_router,
    government_schemes_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and seed official government schemes
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        sync_government_schemes(db)
    finally:
        db.close()
    yield
    # Shutdown

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Multilingual business management and official government schemes discovery & readiness platform for India's micro-merchants.",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Core API Routers
api_v1 = settings.API_V1_STR
app.include_router(auth_router, prefix=api_v1)
app.include_router(business_router, prefix=api_v1)
app.include_router(customers_router, prefix=api_v1)
app.include_router(transactions_router, prefix=api_v1)
app.include_router(invoices_router, prefix=api_v1)
app.include_router(voice_router, prefix=api_v1)
app.include_router(dashboard_router, prefix=api_v1)
app.include_router(government_schemes_router, prefix=api_v1)

# Frontend static asset mounting
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>Vyapaar AI Government Schemes API is Active</h1><p>Visit <a href='/docs'>/docs</a></p>")

@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "Vyapaar AI Core & Government Schemes Platform",
        "version": settings.PROJECT_VERSION
    }
