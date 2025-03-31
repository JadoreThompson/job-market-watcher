import json
from typing import List
from sqlalchemy import select, distinct, func

from db_models import CleanedData
from utils.db import get_db_session
from .models import Row


async def generate_plang_table_data() -> List[Row]:
    async with get_db_session() as sess:
        res = await sess.execute(
            select(CleanedData.programming_languages, CleanedData.salary)
        )
        data = res.all()

    rtn_value: dict[str, list[float]] = {}

    for tup in data:
        if tup[1] is None:
            continue

        for lang in json.loads(tup[0]):
            rtn_value.setdefault(lang, [])
            rtn_value[lang].append(tup[1])

    return [
        Row(
            name=lang,
            average_salary=sum(rtn_value[lang]) / len(rtn_value[lang]),
            median_salary=rtn_value[lang][len(rtn_value[lang]) // 2],
        )
        for lang in rtn_value
    ]


async def generate_industries_table_data() -> List[Row]:
    async with get_db_session() as sess:
        res = await sess.execute(
            select(
                distinct(CleanedData.industry),
                func.sum(CleanedData.salary) / func.count(CleanedData.industry),
                func.percentile_cont(0.5).within_group(CleanedData.salary),
            )
            .where(CleanedData.salary != None)
            .group_by(CleanedData.industry)
        )
        data = res.all()

    rtn_value: list[Row] = []

    for tup in data:
        print(tup)
        if tup[1] and tup[2]:
            rtn_value.append(
                Row(name=tup[0], average_salary=float(tup[1]), median_salary=tup[2])
            )

    return rtn_value
