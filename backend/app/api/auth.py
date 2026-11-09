from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from app.core.security import Actor, DB, audit, passwords, token
from app.models import User
from app.api.helpers import data

router = APIRouter(prefix="/auth", tags=["Authentication"])
_attempts = {}
_guard = Lock()
_dummy = passwords.hash("PostMate-unused-password")


@router.post("/login")
def login(request: Request, db: DB, form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    # Per-process local limiter; production ingress must also enforce a shared limit.
    key = request.client.host if request.client else "unknown"
    now = datetime.now(timezone.utc)
    with _guard:
        for address in list(_attempts):
            _attempts[address] = [stamp for stamp in _attempts[address] if stamp > now - timedelta(minutes=5)]
            if not _attempts[address]:
                del _attempts[address]
        attempts = _attempts.setdefault(key, [])
        if len(attempts) >= 15:
            raise HTTPException(429, "Too many login attempts. Try again in five minutes.")
        attempts.append(now)
    user = db.scalar(select(User).where(User.username == form.username.lower()))
    valid = passwords.verify(form.password, user.password_hash if user else _dummy)
    if not user or not valid or not user.active:
        raise HTTPException(401, "Invalid credentials")
    audit(db, user, "auth.login", "users", user.id)
    return {"access_token": token(user), "token_type": "bearer", "user": data(user, {"password_hash", "token_version"})}


@router.get("/me")
def me(actor: Actor):
    return data(actor, {"password_hash", "token_version"})


@router.post("/logout")
def logout(db: DB, actor: Actor):
    # Increment in SQL to avoid lost updates from simultaneous logouts.
    from sqlalchemy import update
    db.execute(update(User).where(User.id == actor.id).values(token_version=User.token_version + 1))
    audit(db, actor, "auth.logout", "users", actor.id)
    return {"message": "All current sessions revoked"}
