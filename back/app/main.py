from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import json

from .db import get_conn
from .auth import get_user_id
from .schemas import ListCreate, ShareIn, RenameListIn

from app.kinopoisk import router as kinopoisk_router  # импорт роутера
from .items import router as items_router
from .auth import router as auth_router

app = FastAPI(title="ToWatchList API")

app.include_router(kinopoisk_router)
app.include_router(items_router)
app.include_router(auth_router)

# CORS при необходимости
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000"
    "http://192.168.1.255:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

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