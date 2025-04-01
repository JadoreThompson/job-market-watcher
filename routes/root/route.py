import json

from typing import Optional
from fastapi import APIRouter

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
from .models import Row

root = APIRouter(prefix="", tags=["root"])


@root.get("/programming-languages-chart")
async def programming_languages_chart() -> dict:
    prev: Optional[bytes] = await REDIS_CLIENT.get(PLANG_BAR_CHART_KEY)
    if prev:
        return json.loads(prev)

    data: dict = await fetch_plang_chart_data()
    await REDIS_CLIENT.set(PLANG_BAR_CHART_KEY, json.dumps(data))
    return data


@root.get("/programming-languages")
async def programming_languages(
    location: Optional[str] = None,
) -> tuple[Optional[Row | dict], ...]:
    key = f"{PLANG_TABLE_KEY}:{location}"
    
    prev: Optional[bytes] = await REDIS_CLIENT.get(key)
    if prev is not None:
        print(prev)
        print("--------------------------")
        return json.loads(prev)

    data: list[Row] = await fetch_plang_table_data(location)
    await REDIS_CLIENT.set(
        key, json.dumps([item.model_dump() for item in data]), ex=300
    )
    return data


@root.get("/industries-chart")
async def industries() -> dict:
    prev: Optional[bytes] = await REDIS_CLIENT.get(INDUSTRY_BAR_CHART_KEY)
    if prev:
        return json.loads(prev)

    data: dict = await fetch_industries_chart_data()
    await REDIS_CLIENT.set(INDUSTRY_BAR_CHART_KEY, json.dumps(data), ex=300)
    return data


@root.get("/industries")
async def industries(
    location: Optional[str] = None,
) -> tuple[Optional[Row | dict], ...]:
    key = f"{INDUSTRY_TABLE_KEY}:{location}"
    
    prev: Optional[bytes] = await REDIS_CLIENT.get(key)
    if prev is not None:
        return json.loads(prev)

    data: list[Row] = await fetch_industries_table_data(location)
    await REDIS_CLIENT.set(key, json.dumps([item.model_dump() for item in data]))
    return data
