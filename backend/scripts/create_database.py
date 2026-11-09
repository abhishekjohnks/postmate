"""Explicit local setup, never called by application startup."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from app.core.config import get_settings

settings = get_settings()
with psycopg.connect(host=settings.postgres_host, port=settings.postgres_port, dbname="postgres",
                     user=settings.postgres_user, password=settings.postgres_password, autocommit=True) as db:
    exists = db.execute("SELECT 1 FROM pg_database WHERE datname = %s", (settings.postgres_db,)).fetchone()
    if not exists:
        db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(settings.postgres_db)))
    print("Database ready:", settings.postgres_db)
