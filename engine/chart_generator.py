import json
from typing import Dict, List, Optional
from config import BAR_CHART_KEY, BAR_CHART_KEY_LIVE, CLEANED_DATA_KEY, REDIS_CLIENT


class ChartGenerator:
    def __init__(self) -> None:
        self._curr_bar_chart_data: Dict[str, int] = {}

    async def run(self) -> None:
        await self._init()
        await self._listen()

    async def _init(self) -> None:
        prev: Optional[bytes] = await REDIS_CLIENT.get(BAR_CHART_KEY)
        if prev is not None:
            self._curr_bar_chart_data = json.loads(prev)

    async def _listen(self) -> None:
        async with REDIS_CLIENT.pubsub() as ps:
            await ps.subscribe(CLEANED_DATA_KEY)

            async for message in ps.listen():
                if message["type"] == "message":
                    await self._generate_plang_bar_chart(message["data"])

    async def _generate_plang_bar_chart(self, data: List[dict]) -> None:
        loaded_data: List[dict] = json.loads(data)
        counts: dict = self._get_plang_counts(loaded_data)

        for key in counts:
            self._curr_bar_chart_data.setdefault(key, 0)
            self._curr_bar_chart_data[key] += counts[key]

        print(self._curr_bar_chart_data)
        dumped: str = json.dumps(self._curr_bar_chart_data)
        await REDIS_CLIENT.set(BAR_CHART_KEY, dumped)
        await REDIS_CLIENT.publish(BAR_CHART_KEY_LIVE, dumped)

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

        counts["typescript"] += counts.get("javascript", 0)
        counts["go"] += counts.get("golang", 0)

        return counts
