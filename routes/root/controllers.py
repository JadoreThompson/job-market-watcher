import json
from typing import Optional
from sqlalchemy import select, distinct, func

from db_models import CleanedData
from utils.db import get_db_session
from .models import Row


async def fetch_plang_chart_data() -> dict:
    async with get_db_session() as sess:
        res = await sess.execute(select(distinct(CleanedData.programming_languages)))
        data: list[tuple[str]] = res.all()

    rtn_value: dict[str, int] = {}
    for (item,) in data:
        for key in json.loads(item):
            key = key.lower()
            rtn_value.setdefault(key, 0)
            rtn_value[key] += 1

    return rtn_value


async def fetch_industries_chart_data() -> dict:
    async with get_db_session() as sess:
        res = await sess.execute(select(distinct(CleanedData.industry)))
        data: list[tuple[str]] = res.all()

    rtn_value: dict[str, int] = {}
    for (ind,) in data:
        rtn_value.setdefault(ind, 0)
        rtn_value[ind] += 1

    return rtn_value


async def fetch_plang_table_data(
    location: Optional[str] = None,
) -> tuple[Optional[Row], ...]:
    query = select(CleanedData.programming_languages, CleanedData.salary).where(
        CleanedData.salary != None
    )

    if location is not None:
        query = query.where(CleanedData.location.like(f"{location.strip()}"))

    lang_map: dict[str, list[float]] = {}

    async with get_db_session() as sess:
        res = await sess.stream(query)

        async for langs, salary in res:
            for lang in json.loads(langs):
                lang_map.setdefault(lang, [])
                lang_map[lang].append(salary)

    return tuple(
        Row(
            name=lang,
            average_salary=sum(lang_map[lang]) / len(lang_map[lang]),
            median_salary=lang_map[lang][len(lang_map[lang]) // 2],
        )
        for lang in lang_map
    )


async def fetch_industries_table_data(
    location: Optional[str] = None,
) -> tuple[Optional[Row], ...]:
    query = select(
        distinct(CleanedData.industry),
        func.sum(CleanedData.salary) / func.count(CleanedData.industry),
        func.percentile_cont(0.5).within_group(CleanedData.salary),
    ).where(CleanedData.salary != None)

    if location is not None:
        query = query.where(CleanedData.location.like(location))

    async with get_db_session() as sess:
        res = await sess.stream(query.group_by(CleanedData.industry))

        return tuple(
            Row(name=name, average_salary=float(avg_sal), median_salary=med_sal)
            async for name, avg_sal, med_sal in res
            if avg_sal and med_sal
        )
