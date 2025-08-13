import os
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext
from werkzeug.security import check_password_hash as wz_check
from .db import get_conn

# JWT настройки
JWT_SECRET = os.getenv("JWT_SECRET", "change_me")
JWT_ALG = "HS256"
JWT_EXPIRE_DAYS = int(os.getenv("JWT_EXPIRE_DAYS", "7"))

# Настройка bcrypt через passlib
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------- Пароли ----------

def hash_password(password: str) -> str:
    """Хешируем новый пароль в bcrypt."""
    return pwd_ctx.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    """Проверка пароля: сначала bcrypt, потом werkzeug."""
    # bcrypt-хэш
    if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
        return pwd_ctx.verify(password, stored_hash)
    # werkzeug-хэш
    return wz_check(stored_hash, password)


def rehash_if_needed(user_id: int, password: str, stored_hash: str) -> None:
    """
    Если пароль был в старом формате werkzeug — пересчитываем в bcrypt.
    """
    if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
        return  # уже bcrypt
    new_hash = pwd_ctx.hash(password)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET password=%s WHERE id=%s", (new_hash, user_id))
        conn.commit()


# ---------- JWT ----------

def create_token(user_id: int) -> str:
    """Создаём JWT-токен с exp в UTC."""
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def parse_token(token: str) -> int:
    """Декодируем JWT и возвращаем user_id."""
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return int(data["sub"])
    except JWTError:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid or expired token")
