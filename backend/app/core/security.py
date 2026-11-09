from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import AuditLog, User

passwords = PasswordHash.recommended()
oauth = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
DB = Annotated[Session, Depends(get_db, scope="function")]


def encrypt(value: str | None):
    return Fernet(get_settings().encryption_key.encode()).encrypt(value.encode()).decode() if value else None


def decrypt(value: str | None):
    return Fernet(get_settings().encryption_key.encode()).decrypt(value.encode()).decode() if value else None


def token(user: User):
    settings = get_settings()
    return jwt.encode({"sub": user.id, "ver": user.token_version,
                       "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.token_minutes),
                       "iat": datetime.now(timezone.utc)}, settings.jwt_secret, algorithm="HS256")


def current_user(db: DB, bearer: Annotated[str, Depends(oauth)]) -> User:
    try:
        claims = jwt.decode(bearer, get_settings().jwt_secret, algorithms=["HS256"], options={"require": ["exp", "sub", "ver"]})
        user = db.get(User, claims["sub"])
        if not user or not user.active or user.token_version != claims["ver"]:
            raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(401, "Session expired or invalid", headers={"WWW-Authenticate": "Bearer"})


Actor = Annotated[User, Depends(current_user)]


def admin(actor: Actor):
    if actor.role != "super_admin":
        raise HTTPException(403, "Super Admin permission required")
    return actor


Admin = Annotated[User, Depends(admin)]


def audit(db, actor, action, entity, entity_id=None, details=None):
    db.add(AuditLog(user_id=actor.id if actor else None, action=action,
                    entity_type=entity, entity_id=entity_id, details=details or {}))
