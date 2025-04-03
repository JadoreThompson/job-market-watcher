import json

from fastapi import APIRouter
from typing import Optional

from config import (
    INDUSTRY_BAR_CHART_KEY,
    INDUSTRY_TABLE_KEY,
    PLANG_BAR_CHART_KEY,
    PLANG_TABLE_KEY,
    REDIS_CLIENT,
)
from .controllers import (
    fetch_industries_chart_data,
    fetch_industries_table_data,
    fetch_plang_chart_data,
    fetch_plang_table_data,
)
from .models import MaxPagesPaginatedResponse

root = APIRouter(prefix="", tags=["root"])


@root.get("/programming-languages-chart")
async def programming_languages_chart() -> dict:
    prev: Optional[bytes] = await REDIS_CLIENT.get(PLANG_BAR_CHART_KEY)
    if prev:
        return json.loads(prev)

    data: dict = await fetch_plang_chart_data()
    await REDIS_CLIENT.set(PLANG_BAR_CHART_KEY, json.dumps(data))
    return data


@root.get("/industries-chart")
async def industries() -> dict:
    prev: Optional[bytes] = await REDIS_CLIENT.get(INDUSTRY_BAR_CHART_KEY)
    if prev:
        return json.loads(prev)

    data: dict = await fetch_industries_chart_data()
    await REDIS_CLIENT.set(INDUSTRY_BAR_CHART_KEY, json.dumps(data), ex=300)
    return data


@root.get("/programming-languages")
async def programming_languages(
    location: Optional[str] = None, page: Optional[int] = 0
) -> MaxPagesPaginatedResponse | dict:
    key = f"{PLANG_TABLE_KEY}:{location}:{page}"

    prev: Optional[bytes] = await REDIS_CLIENT.get(key)
    if prev is not None:
        return json.loads(prev)

    rows, max_pages = await fetch_plang_table_data(location, page)
    rtn = MaxPagesPaginatedResponse(
        data=rows[:10], has_next_page=len(rows) > 10, max_pages=max_pages
    )
    await REDIS_CLIENT.set(key, json.dumps(rtn.model_dump()))
    return rtn


@root.get("/industries")
async def industries(
    location: Optional[str] = None,
    page: Optional[int] = 0,
) -> MaxPagesPaginatedResponse | dict:
    key = f"{INDUSTRY_TABLE_KEY}:{location}:{page}"

    prev: Optional[bytes] = await REDIS_CLIENT.get(key)
    if prev is not None:
        return json.loads(prev)

    rows, max_pages = await fetch_industries_table_data(location, page)
    rtn = MaxPagesPaginatedResponse(
        data=rows[:10], has_next_page=len(rows) > 10, max_pages=max_pages
    )
    await REDIS_CLIENT.set(key, json.dumps(rtn.model_dump()))
    return rtn
