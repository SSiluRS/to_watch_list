from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import json

from .db import get_conn
from .auth import create_token, parse_token, hash_password, verify_password, rehash_if_needed
from .schemas import RegisterIn, LoginIn, ListCreate, ItemCreate, ItemPatch, ShareIn, RenameListIn

app = FastAPI(title="ToWatchList API")

# CORS при необходимости
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

def get_user_id(creds: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[int]:
    if not creds:
        return None
    try:
        return parse_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

# --------- AUTH ----------
@app.post("/register")
def register(body: RegisterIn):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM users WHERE username=%s", (body.username,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Username already exists")

        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (body.username, hash_password(body.password))
        )
        conn.commit()
        user_id = cur.lastrowid

    token = create_token(user_id)
    # фронт после регистрации сразу кладёт token/user_id в localStorage
    return {"message": "User registered", "user_id": user_id, "token": token}


@app.post("/login")
def login(body: LoginIn):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, password FROM users WHERE username=%s", (body.username,))
        row = cur.fetchone()
        if not row or not verify_password(body.password, row["password"]):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # Автоматическая миграция пароля в bcrypt
        rehash_if_needed(row["id"], body.password, row["password"])

        token = create_token(row["id"])
        return {"message": "Login successful", "user_id": row["id"], "token": token}


@app.get("/auth-check")
def auth_check(user_id: int = Depends(get_user_id)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"message": "Authorized"}

# --------- USERS ----------
@app.get("/user")
def get_user_by_username(username: str):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        u = cur.fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")
        return u

# --------- LISTS ----------
@app.get("/lists")
def list_lists(user_id: int = Depends(get_user_id)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM lists WHERE user_id=%s", (user_id,))
        return cur.fetchall()

@app.post("/lists", status_code=201)
def create_list(body: ListCreate, user_id: int = Depends(get_user_id)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO lists (user_id, name) VALUES (%s, %s)", (user_id, body.name))
        conn.commit()
    return {"message": "List created"}

@app.patch("/rename_list")
def rename_list(body: RenameListIn, user_id: int = Depends(get_user_id)):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM lists WHERE id=%s AND user_id=%s", (body.list_id, user_id))
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="List not found or access denied")
        cur.execute("UPDATE lists SET name=%s WHERE id=%s", (body.new_name, body.list_id))
        conn.commit()
    return {"message": "List renamed successfully"}

@app.delete("/delete_list")
def delete_list(body: dict, user_id: int = Depends(get_user_id)):
    list_id = body.get("list_id")
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM lists WHERE id=%s AND user_id=%s", (list_id, user_id))
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="List not found or access denied")
        cur.execute("DELETE FROM lists WHERE id=%s", (list_id,))
        conn.commit()
    return {"message": "List deleted successfully"}

# --------- ITEMS ----------
@app.get("/items")
def get_items(list_id: int, user_id: int = Depends(get_user_id)):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        # Проверка права доступа: владелец или расшарено
        cur.execute("""
            SELECT 1 FROM lists WHERE id=%s AND user_id=%s
            UNION
            SELECT 1 FROM shared_lists WHERE list_id=%s AND shared_with_id=%s
        """, (list_id, user_id, list_id, user_id))
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="Access denied")
        cur.execute("SELECT * FROM items WHERE list_id=%s", (list_id,))
        return cur.fetchall()

@app.post("/items", status_code=201)
def add_item(body: ItemCreate, user_id: int = Depends(get_user_id)):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT 1 FROM lists WHERE id=%s AND user_id=%s", (body.list_id, user_id))
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="Access denied")
        cur.execute("""
            INSERT INTO items (list_id, title, type, cover_url, genre) VALUES (%s,%s,%s,%s,%s)
        """, (body.list_id, body.title, body.type, body.cover_url or "", body.genre))
        conn.commit()
    return {"message": "Item added"}

@app.patch("/items")
def patch_item(body: ItemPatch, user_id: int = Depends(get_user_id)):
    fields, params = [], []
    if body.title is not None:
        fields.append("title=%s"); params.append(body.title)
    if body.type is not None:
        fields.append("type=%s"); params.append(body.type)
    if body.cover_url is not None:
        fields.append("cover_url=%s"); params.append(body.cover_url)
    if body.watched is not None:
        fields.append("watched=%s"); params.append(1 if body.watched else 0)
    if not fields:
        raise HTTPException(status_code=400, detail="No changes provided")

    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        # владение по item -> list -> user
        cur.execute("""
            SELECT l.user_id FROM items i
            JOIN lists l ON i.list_id = l.id
            WHERE i.id=%s
        """, (body.id,))
        row = cur.fetchone()
        if not row or row["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        params.append(body.id)
        cur.execute(f"UPDATE items SET {', '.join(fields)} WHERE id=%s", params)
        conn.commit()
    return {"message": "Item updated"}

@app.delete("/items")
def delete_item(body: dict, user_id: int = Depends(get_user_id)):
    item_id = body.get("id")
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT l.user_id FROM items i JOIN lists l ON i.list_id=l.id WHERE i.id=%s
        """, (item_id,))
        row = cur.fetchone()
        if not row or row["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        cur.execute("DELETE FROM items WHERE id=%s", (item_id,))
        conn.commit()
    return {"message": "Item deleted"}

# --------- SHARING ----------
@app.post("/share", status_code=201)
def share_list(body: ShareIn, user_id: int = Depends(get_user_id)):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM users WHERE username=%s", (body.username,))
        share_to = cur.fetchone()
        if not share_to:
            raise HTTPException(status_code=404, detail="User not found")
        cur.execute("SELECT id FROM lists WHERE id=%s AND user_id=%s", (body.list_id, user_id))
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="Access denied")
        cur.execute("""
            INSERT INTO shared_lists (list_id, owner_id, shared_with_id) VALUES (%s,%s,%s)
        """, (body.list_id, user_id, share_to["id"]))
        conn.commit()
    return {"message": "List shared successfully"}

@app.get("/shared_lists")
def get_shared_lists(user_id: int = Depends(get_user_id)):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT lists.id, lists.name, u.username AS owner
            FROM shared_lists s
            JOIN lists ON s.list_id = lists.id
            JOIN users u ON s.owner_id = u.id
            WHERE s.shared_with_id=%s
        """, (user_id,))
        return cur.fetchall()

# --------- LOGS (опционально) ----------
@app.post("/logs")
async def log_event(request: Request, user_id: Optional[int] = Depends(get_user_id)):
    data = {}
    try:
        data = (await request.json()) if hasattr(request, "json") else {}
    except Exception:
        pass
    event = data.get("event", "unknown")
    payload = json.dumps(data.get("data", {}), ensure_ascii=False)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO logs (event, data, user_id) VALUES (%s,%s,%s)", (event, payload, user_id or 0))
        conn.commit()
    return {"message": "Log entry saved"}


from fastapi.staticfiles import StaticFiles
# Раздача фронта
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")