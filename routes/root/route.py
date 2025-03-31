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
from .controllers import generate_industries_table_data, generate_plang_table_data
from .models import Row

root = APIRouter(prefix="", tags=["root"])


@root.get("/programming-languages-chart")
async def programming_languages_chart():
    prev: Optional[bytes] = await REDIS_CLIENT.get(PLANG_BAR_CHART_KEY)
    if prev:
        return json.loads(prev)


@root.get("/programming-languages")
async def programming_languages() -> list[Row | dict]:
    prev: Optional[bytes] = await REDIS_CLIENT.get(PLANG_TABLE_KEY)
    if prev:
        return json.loads(prev)

    data: list[Row] = await generate_plang_table_data()
    await REDIS_CLIENT.set(PLANG_TABLE_KEY, json.dumps([item.model_dump() for item in data]))
    return data


@root.get("/industries-chart")
async def industries():
    prev: Optional[bytes] = await REDIS_CLIENT.get(INDUSTRY_BAR_CHART_KEY)
    if prev:
        return json.loads(prev)


@root.get("/industries")
async def industries() -> list[Row | dict]:
    prev: Optional[bytes] = await REDIS_CLIENT.get(INDUSTRY_TABLE_KEY)
    if prev:
        return json.loads(prev)

    data: list[Row] = await generate_industries_table_data()
    await REDIS_CLIENT.set(
        INDUSTRY_TABLE_KEY, json.dumps([item.model_dump() for item in data])
    )
    return data
