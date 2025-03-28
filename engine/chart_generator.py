import asyncio
import json
from typing import Dict, List, Optional
from config import (
    INDUSTRY_BAR_CHART_KEY,
    INDUSTRY_BAR_CHART_KEY_LIVE,
    PLANG_BAR_CHART_KEY,
    PLANG_BAR_CHART_KEY_LIVE,
    CLEANED_DATA_KEY,
    REDIS_CLIENT,
)


class ChartGenerator:
    def __init__(self) -> None:
        self._curr_plang_bar_chart_data: Dict[str, int] = {}
        self._curr_industry_bar_chart_data: Dict[str, int] = {}

    async def run(self) -> None:
        await self._init()
        await self._listen()

    async def _init(self) -> None:
        prev: Optional[bytes] = await REDIS_CLIENT.get(PLANG_BAR_CHART_KEY)
        if prev is not None:
            self._curr_plang_bar_chart_data = json.loads(prev)

        prev: Optional[bytes] = await REDIS_CLIENT.get(INDUSTRY_BAR_CHART_KEY)
        if prev is not None:
            self._curr_industry_bar_chart_data = json.loads(prev)

    async def _listen(self) -> None:
        async with REDIS_CLIENT.pubsub() as ps:
            await ps.subscribe(CLEANED_DATA_KEY)

            async for message in ps.listen():
                if message["type"] == "message":
                    loaded_data: List[dict] = json.loads(message["data"])
                    await asyncio.gather(
                        self._gen_industry_bar_chart(loaded_data),
                        self._gen_plang_bar_chart(loaded_data),
                    )

    async def _gen_plang_bar_chart(self, data: List[dict]) -> None:
        counts: dict = self._get_plang_counts(data)

        for key in counts:
            self._curr_plang_bar_chart_data.setdefault(key, 0)
            self._curr_plang_bar_chart_data[key] += counts[key]

        dumped: str = json.dumps(self._curr_plang_bar_chart_data)
        await REDIS_CLIENT.set(PLANG_BAR_CHART_KEY, dumped)
        await REDIS_CLIENT.publish(PLANG_BAR_CHART_KEY_LIVE, dumped)

    def _get_plang_counts(self, data: List[dict]) -> dict:
        programming_languages: List[str] = [
            lang.lower()
            for d in data
            for lang in json.loads(d["programming_languages"])
        ]

        counts: dict[str, int] = {}

        for lang in programming_languages:
            counts.setdefault(lang, 0)
            counts[lang] += 1

        if "typescript" in counts:
            counts["typescript"] += counts.get("javascript", 0)
        if "go" in counts:
            counts["go"] += counts.get("golang", 0)

        return counts

    async def _gen_industry_bar_chart(self, data: List[dict]) -> None:
        industries: List[str] = [d["industry"] for d in data]

        for ind in industries:
            self._curr_industry_bar_chart_data.setdefault(ind, 0)
            self._curr_industry_bar_chart_data[ind] += 1

        dumped: str = json.dumps(self._curr_industry_bar_chart_data)
        await REDIS_CLIENT.set(INDUSTRY_BAR_CHART_KEY, dumped)
        await REDIS_CLIENT.publish(INDUSTRY_BAR_CHART_KEY_LIVE, dumped)
