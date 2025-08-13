import os
import httpx
from fastapi import APIRouter, Query, HTTPException

router = APIRouter()
KINOPOISK_API_KEY = os.getenv("KINOPOISK_API_KEY")

@router.get("/kinopoisk/search")
async def kinopoisk_search(query: str = Query(..., min_length=1)):
    """Проксируем запрос к API Кинопоиска через наш сервер.
    Здесь мы используем httpx в асинхронном режиме, чтобы не блокировать event loop.
    Такой подход решает две задачи:
      1. API-ключ хранится на сервере и не виден пользователям.
      2. Мы можем обрабатывать и фильтровать ответы, а также логировать обращения.
    Асинхронный запрос позволяет обрабатывать несколько обращений к API параллельно.
    """
    if not KINOPOISK_API_KEY:
        raise HTTPException(status_code=500, detail="Kinopoisk API key not configured")

    url = f"https://api.kinopoisk.dev/v1.4/movie/search?query={query}"
    headers = {"X-API-KEY": KINOPOISK_API_KEY}

    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers)
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Kinopoisk API error")
        return r.json()