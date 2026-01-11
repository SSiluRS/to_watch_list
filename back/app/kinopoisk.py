import os
from typing import Optional, Literal, List
import httpx
from fastapi import APIRouter, Query, HTTPException
from unicodedata import normalize as u_normalize

router = APIRouter()
KINOPOISK_API_KEY = os.getenv("KINOPOISK_API_KEY")
BASE_URL = "https://api.poiskkino.dev/v1.4"


def _norm(s: Optional[str]) -> str:
    if not s:
        return ""
    return u_normalize("NFKC", s).strip().lower()


@router.get("/kinopoisk/search")
async def kinopoisk_search(
    query: str = Query(..., min_length=1, description="Название фильма/сериала"),
    type: Optional[Literal["movie","tv-series","cartoon","anime","animated-series","mini-series","tv-show"]] = Query(
        None, description="Тип контента"
    ),
    year: Optional[int] = Query(None, ge=1888, le=2100, description="Год выхода"),
    limit: int = Query(10, ge=1, le=50, description="Сколько документов вернуть")
):
    """Проксируем запрос к API ПоискКино через наш сервер.
    - Ключ хранится на сервере и не светится на фронте.
    - Асинхронный httpx не блокирует event loop.
    """
    if not KINOPOISK_API_KEY:
        raise HTTPException(status_code=500, detail="Kinopoisk API key not configured")

    params: dict = {"query": query, "limit": limit}
    # Даже если API /search не поддерживает фильтры напрямую, 
    # мы передаём их (на случай если поддержка появится/есть)
    if type:
        params["type"] = type
    if year:
        params["year"] = year

    headers = {"X-API-KEY": KINOPOISK_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            r = await client.get(f"{BASE_URL}/movie/search", params=params, headers=headers)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Kinopoisk request timed out")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Kinopoisk connection error")

    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=f"Kinopoisk API error: {r.text}")

    payload = r.json()
    
    # Дополнительная фильтрация на нашей стороне, если API проигнорировал параметры
    if type or year:
        docs = payload.get("docs", [])
        filtered_docs = [
            d for d in docs
            if (not type or d.get("type") == type)
            and (not year or d.get("year") == year)
        ]
        payload["docs"] = filtered_docs
        payload["limit"] = len(filtered_docs)
        
    return payload


@router.get("/kinopoisk/description")
async def kinopoisk_description(
    query: str = Query(..., min_length=1),
    type: Optional[str] = Query(None, description="Тип контента"),
    year: Optional[int] = Query(None, ge=1888, le=2100),
    limit: int = Query(10, ge=1, le=50)
):
    """Возвращает краткое описание и лучшего кандидата для данного запроса."""
    if not KINOPOISK_API_KEY:
        raise HTTPException(status_code=500, detail="Kinopoisk API key not configured")

    params: dict = {"query": query, "limit": limit}
    if type:
        params["type"] = type
    if year:
        params["year"] = year

    headers = {"X-API-KEY": KINOPOISK_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            r = await client.get(f"{BASE_URL}/movie/search", params=params, headers=headers)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Kinopoisk request timed out")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Kinopoisk connection error")

    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail="Kinopoisk API error")

    payload = r.json() or {}
    docs = payload.get("docs") or []

    if not docs:
        return {"match": None, "description": None, "candidates": []}

    qn = _norm(query)

    # Фильтрация по типу/году
    filtered = [
        d for d in docs
        if (not type or d.get("type") == type)
        and (not year or d.get("year") == year)
    ] or docs

    # Поиск точного совпадения названия
    def is_exact_title_match(d):
        titles = [d.get("name"), d.get("alternativeName"), d.get("enName")]
        # Также проверяем массив names
        api_names = d.get("names") or []
        for n_obj in api_names:
            if isinstance(n_obj, dict) and n_obj.get("name"):
                titles.append(n_obj.get("name"))
        
        return any(_norm(t) == qn for t in titles if t)

    exact = [d for d in filtered if is_exact_title_match(d)]
    best = exact[0] if exact else filtered[0]

    description = (
        best.get("description")
        or best.get("shortDescription")
        or best.get("plot")
        or best.get("synopsis")
        or None
    )

    return {
        "match": {
            "id": best.get("id"),
            "name": best.get("name") or best.get("alternativeName") or best.get("enName"),
            "type": best.get("type"),
            "year": best.get("year"),
            "rating": (best.get("rating") or {}).get("kp"),
            "poster": (best.get("poster") or {}).get("url"),
        },
        "description": description,
        "candidates": [
            {
                "id": d.get("id"),
                "name": d.get("name") or d.get("alternativeName") or d.get("enName"),
                "type": d.get("type"),
                "year": d.get("year"),
            } for d in filtered[:5]
        ],
    }