from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import Error as MySQLError

from app.auth import get_user_id
from app.schemas import ItemCreate, ItemPatch
from .db import get_conn  # у тебя уже есть
# если у тебя есть авторизация — добавь Depends(...) при необходимости

router = APIRouter(prefix="/items", tags=["items"])

# Белый список колонок сортировки (ключ=имя из API → значение=SQL-выражение)
SORT_WHITELIST: dict[str, str] = {
    "created_at": "i.id",
    "title":      "i.title",
    "year":       "i.year",
    "rating":     "i.rating",
    "genre":      "i.genre"
}

@router.get("")
def get_items(
    list_id: int,
    user_id: int = Depends(get_user_id),
    sort_by: Literal["created_at","title","year","rating","genre"] = Query("created_at"),
    order:   Literal["asc","desc"] = Query("desc"),
    limit:   int = Query(50, ge=1, le=200),
    offset:  int = Query(0, ge=0),
    genre_filter: Optional[str] = Query(None, description="Фильтр по жанру"),
):
    # 1) проверяем доступ к списку (как у тебя и было)
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT 1 FROM lists WHERE id=%s AND user_id=%s
            UNION
            SELECT 1 FROM shared_lists WHERE list_id=%s AND shared_with_id=%s
        """, (list_id, user_id, list_id, user_id))
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="Access denied")

        # 2) формируем ORDER BY из белого списка (никаких подстановок «как есть»!)
        column = SORT_WHITELIST[sort_by]
        direction = "ASC" if order == "asc" else "DESC"
        # стабильная сортировка добавочно по id
        order_clause = f"{column} {direction}, i.id {direction}"

        # WHERE
        where_parts = ["i.list_id=%s"]
        params = [list_id]

        if genre_filter:
            where_parts.append("i.genre LIKE %s")
            params.append(f"%{genre_filter}%")

        where_sql = " AND ".join(where_parts)

        cur.execute(f"""
            SELECT i.*
            FROM items i
            WHERE {where_sql}
            ORDER BY {order_clause}
            LIMIT %s OFFSET %s
        """, (*params, limit, offset))

        rows = cur.fetchall()

    return {
        "items": rows,
        "list_id": list_id,
        "sort_by": sort_by,
        "order": order,
        "limit": limit,
        "offset": offset,
    }

@router.post("", status_code=201)
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

@router.patch("")
def patch_item(body: ItemPatch, user_id: int = Depends(get_user_id)):
    fields, params = [], []
    if body.year is not None:
        fields.append("year=%s"); params.append(body.year)
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

@router.delete("")
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

@router.get("/genres")
def get_genres(list_id: int, user_id: int = Depends(get_user_id)):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        # Проверка доступа
        cur.execute("""
            SELECT 1 FROM lists WHERE id=%s AND user_id=%s
            UNION
            SELECT 1 FROM shared_lists WHERE list_id=%s AND shared_with_id=%s
        """, (list_id, user_id, list_id, user_id))
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="Access denied")

        # Берём все непустые жанры
        cur.execute("""
            SELECT genre
            FROM items
            WHERE list_id=%s AND genre IS NOT NULL AND genre <> ''
        """, (list_id,))
        rows = cur.fetchall()

    # Разделяем по запятой, убираем пробелы и делаем уникальные
    genres_set = set()
    for row in rows:
        parts = [g.strip() for g in row["genre"].split(",")]
        for g in parts:
            if g:
                genres_set.add(g)

    # Отсортировать по алфавиту
    genres_list = sorted(genres_set, key=lambda s: s.lower())

    return genres_list
