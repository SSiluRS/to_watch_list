# back/scripts/fill_years.py
from __future__ import annotations
import os
import asyncio
import httpx
import argparse
from typing import Optional, List, Dict, Any, Tuple
from contextlib import asynccontextmanager
import mysql.connector
from mysql.connector import Error as MySQLError

from pathlib import Path

# Загружаем .env из корня back/
env_path = Path(__file__).resolve().parent.parent / ".env"


# --- настройка из .env бекенда ---
DB_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("MYSQL_PORT", "3306"))
DB_USER = os.getenv("MYSQL_USER", "to_watch_list")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
DB_NAME = os.getenv("MYSQL_DATABASE", "to_watch_list")

BACKEND_BASE = "http://127.0.0.1:8000"
KINODECR_PATH = "/kinopoisk/description"  # наша ручка

CONCURRENCY = int(os.getenv("FILL_YEARS_CONCURRENCY", "5"))
TIMEOUT = float(os.getenv("FILL_YEARS_TIMEOUT", "100.0"))

TYPE_MAP = {
    "фильм": "movie",
    "movie": "movie",
    "сериал": "tv-series",
    "tv-series": "tv-series",
    "аниме": "anime",
    "cartoon": "cartoon",
    "мультфильм": "cartoon",
    "mini-series": "mini-series",
    "animated-series": "animated-series",
    "tv-show": "tv-show",
}

def get_connection():
    return mysql.connector.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASSWORD, database=DB_NAME,
        autocommit=False,
    )

def normalize_type(t: Optional[str]) -> Optional[str]:
    if not t:
        return None
    t = t.strip().lower()
    return TYPE_MAP.get(t, t)

def fetch_items(only_missing: bool, limit: Optional[int]) -> List[Dict[str, Any]]:
    sql = "SELECT id, title, type, year FROM items"
    cond = []
    if only_missing:
        cond.append("year IS NULL")
    if cond:
        sql += " WHERE " + " AND ".join(cond)
    sql += " ORDER BY id ASC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    with get_connection() as conn, conn.cursor(dictionary=True) as cur:
        cur.execute(sql)
        return list(cur.fetchall())

def update_years(updates: List[Tuple[int, int]]):
    if not updates:
        return
    with get_connection() as conn, conn.cursor() as cur:
        cur.executemany("UPDATE items SET year=%s WHERE id=%s", [(y, i) for (i, y) in updates])
        conn.commit()

@asynccontextmanager
async def http_client():
    async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT)) as client:
        yield client

async def resolve_year(client: httpx.AsyncClient, title: str, type_: Optional[str], year_hint: Optional[int]) -> Optional[int]:
    """Дёргаем наш бекенд /kinopoisk/description; он уже делает фильтрацию/подбор."""
    params = {
        "query": title,
    }
    if type_:
        params["type"] = normalize_type(type_)
    if year_hint:
        params["year"] = int(year_hint)

    r = await client.get(f"http://127.0.0.1:8000/kinopoisk/description", params=params)
    print(r.status_code, r.text)
    if r.status_code != 200:
        # можно залогировать r.text
        return None
    data = r.json() or {}
    match = data.get("match") or {}
    y = match.get("year")
    # слегка страхуемся: если вернулся год, но в выдаче есть candidates с тем же названием — нормально.
    return int(y) if isinstance(y, int) else None

async def worker(items: List[Dict[str, Any]], sem: asyncio.Semaphore, results: List[Tuple[int, int]], dry_run: bool):
    async with http_client() as client:
        for it in items:
            async with sem:
                title = it.get("title") or ""
                type_ = it.get("type")
                year_hint = it.get("year")  # для непустых можно валидировать/исправлять
                try:
                    new_year = await resolve_year(client, title, type_, year_hint=None)
                except Exception:
                    new_year = None
                if new_year is not None and new_year > 1887 and new_year < 2101:
                    if not dry_run:
                        results.append((it["id"], new_year))
                    print(f"[OK] id={it['id']} «{title}» -> {new_year}")
                else:
                    print(f"[SKIP] id={it['id']} «{title}» -> not found")

async def main():
    parser = argparse.ArgumentParser(description="Fill missing 'year' for items via Kinopoisk proxy.")
    parser.add_argument("--only-missing", action="store_true", help="Обрабатывать только записи без года (по умолчанию)")
    parser.add_argument("--all", dest="only_missing", action="store_false", help="Обрабатывать все записи")
    parser.add_argument("--limit", type=int, default=None, help="Ограничить количество строк")
    parser.add_argument("--dry-run", action="store_true", help="Не писать в БД, только вывод")
    parser.add_argument("--batch", type=int, default=200, help="Размер пакета для UPDATE")
    args = parser.parse_args()

    only_missing = True if args.only_missing or not args.all else False

    items = fetch_items(only_missing=only_missing, limit=args.limit)
    if not items:
        print("Нет записей для обработки.")
        return

    sem = asyncio.Semaphore(CONCURRENCY)
    pending_updates: List[Tuple[int, int]] = []

    # Можно разбить список на чанки, чтобы периодически коммитить
    CHUNK = 5
    for i in range(0, len(items), CHUNK):
        chunk = items[i:i+CHUNK]
        await worker(chunk, sem, pending_updates, dry_run=args.dry_run)
        if pending_updates and not args.dry_run:
            # пачками коммитим
            to_commit, pending_updates = pending_updates[:args.batch], pending_updates[args.batch:]
            update_years(to_commit)

    # добиваем хвост
    if pending_updates and not args.dry_run:
        update_years(pending_updates)

    print("Готово.")

if __name__ == "__main__":
    asyncio.run(main())
