import json
from typing import Optional
from sqlalchemy import select, distinct, func

from db_models import CleanedData
from utils.db import get_db_session
from .models import Row

PAGE_SIZE = 10
LANG_MAP: dict[str, list[float]] = {}


def calc_pages(total_rows: int) -> int:
    try:
        return total_rows // PAGE_SIZE + (0 if total_rows % PAGE_SIZE == 0 else 1)
    except ZeroDivisionError:
        return 0


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
    location: Optional[str] = None, page: Optional[int] = 0
) -> tuple[tuple[Row], int]:
    global LANG_MAP

    if page == 0 or not LANG_MAP:
        query = select(CleanedData.programming_languages, CleanedData.salary).where(
            CleanedData.salary != None
        )

        if location is not None:
            query = query.where(CleanedData.location.like(f"{location.strip()}"))

        async with get_db_session() as sess:
            res = await sess.stream(query)

            async for langs, salary in res:
                for lang in json.loads(langs):
                    LANG_MAP.setdefault(lang.lower(), [])
                    LANG_MAP[lang.lower()].append(salary)

    return tuple(
        Row(
            name=key,
            average_salary=sum(LANG_MAP[key]) / len(LANG_MAP[key]),
            median_salary=LANG_MAP[key][len(LANG_MAP[key]) // 2],
        )
        for key in list(LANG_MAP.keys())[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
    ), calc_pages(len(LANG_MAP))


async def fetch_industries_table_data(
    location: Optional[str] = None, page: Optional[int] = 0
) -> tuple[tuple[Row, ...], int]:
    query = select(
        distinct(CleanedData.industry),
        func.sum(CleanedData.salary) / func.count(CleanedData.industry),
        func.percentile_cont(0.5).within_group(CleanedData.salary),
    ).where(CleanedData.salary != None)

    if location is not None:
        query = query.where(CleanedData.location.like(location))
    query = query.group_by(CleanedData.industry)

    async with get_db_session() as sess:
        data_result = await sess.stream(
            query.offset(page * PAGE_SIZE).limit(PAGE_SIZE + 1)
        )

        result: list[Row] = []
        async for name, avg_sal, med_sal in data_result:
            if avg_sal and med_sal:
                result.append(
                    Row(name=name, average_salary=float(avg_sal), median_salary=med_sal)
                )

        row_count: int = (
            await sess.execute(select(func.count()).select_from(query.subquery()))
        ).first()[0]

    return tuple(result), calc_pages(row_count)
