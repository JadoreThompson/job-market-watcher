import json
from typing import List, Optional
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


async def fetch_plang_table_data(location: Optional[str] = None) -> List[Row]:
    query = select(CleanedData.programming_languages, CleanedData.salary)
    if location is not None:
        query = query.where(CleanedData.location.like(f"'%{location.strip()}'%"))

    async with get_db_session() as sess:
        res = await sess.execute(query)
        data = res.all()
    print(data)
    print("******************")
    rtn_value: dict[str, list[float]] = {}

    for tup in data:
        if tup[1] is None:
            continue

        for lang in json.loads(tup[0]):
            rtn_value.setdefault(lang, [])
            rtn_value[lang].append(tup[1])

    return (
        [
            Row(
                name=lang,
                average_salary=sum(rtn_value[lang]) / len(rtn_value[lang]),
                median_salary=rtn_value[lang][len(rtn_value[lang]) // 2],
            )
            for lang in rtn_value
        ]
        if rtn_value
        else []
    )


async def fetch_industries_table_data(location: Optional[str] = None) -> List[Row]:
    query = select(
        distinct(CleanedData.industry),
        func.sum(CleanedData.salary) / func.count(CleanedData.industry),
        func.percentile_cont(0.5).within_group(CleanedData.salary),
    ).where(CleanedData.salary != None)

    if location is not None:
        query = query.where(CleanedData.location.like(location))

    async with get_db_session() as sess:
        res = await sess.execute(query.group_by(CleanedData.industry))
        data = res.all()

    rtn_value: list[Row] = []

    for name, avg_sal, med_sal in data:
        if avg_sal and med_sal:
            rtn_value.append(
                Row(name=name, average_salary=float(avg_sal), median_salary=med_sal)
            )

    return rtn_value
