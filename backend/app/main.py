from contextlib import asynccontextmanager
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from cryptography.fernet import Fernet
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from app.api import accounts, auth, customers, documents, payments, reporting, schemes, users
from app.core.config import get_settings
from app.db.session import engine
from app.services.notifications import refresh_notifications

settings = get_settings()


@asynccontextmanager
async def lifespan(app):
    Fernet(settings.encryption_key.encode())
    scheduler = BackgroundScheduler(timezone=settings.app_timezone)
    if settings.enable_scheduler:
        scheduler.add_job(refresh_notifications, "interval", minutes=15, id="dues", max_instances=1, coalesce=True)
        scheduler.start()
        try:
            refresh_notifications()
        except OperationalError:
            logging.getLogger(__name__).warning("Database unavailable; configure PostgreSQL and run migrations")
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="PostMate API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_credentials=False, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                   allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
                   expose_headers=["X-Page-Count"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(status_code=409, content={"detail": "Record conflicts with an existing record or a database constraint"})


@app.exception_handler(OperationalError)
async def database_error(request, exc):
    return JSONResponse(status_code=503, content={"detail": "Database unavailable. Check PostgreSQL configuration and migrations."})


@app.get("/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "postgresql"}


for router in (auth.router, users.router, customers.router, schemes.router, accounts.router,
               payments.router, documents.router, reporting.router):
    app.include_router(router, prefix="/api")
