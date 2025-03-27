import asyncio
import json
import regex

from logging import getLogger
from multiprocessing import Queue
from queue import Empty
from typing import List, Optional


from sqlalchemy.dialects.postgresql import insert
from config import CLEANED_DATA_KEY, REDIS_CLIENT
from db_models import CleanedData
from utils.db import get_db_session
from .models import LLMExtractedObject, CleanedDataObject


logger = getLogger(__name__)


class Cleaner:
    """
    Cleans the extracted data and inserts it into the database

    Attributes:
        queue (Queue): - The queue to get the data from
        sleep (int): - The time to sleep between checking the queue if it's empty
    """

    def __init__(self, queue: Queue, *, sleep: int = 1) -> None:
        self._queue = queue
        self.sleep = sleep

    async def run(self) -> None:
        cleaned_data = []

        while True:
            try:
                extracted_data: List[LLMExtractedObject] = self._queue.get(block=True)
                logger.info(f"Cleaning {len(extracted_data)} items")

                for data in extracted_data:
                    cleaned_data.append(self.clean(data))

                logger.info("Finished cleaning data")
                if cleaned_data:
                    await self._persist(cleaned_data)
                    await self._transport(cleaned_data)
                    cleaned_data.clear()
            except Empty:
                await asyncio.sleep(self.sleep)

    def clean(self, data: LLMExtractedObject) -> dict:
        dumped = data.model_dump()
        dumped["salary"] = self._parse_salary(dumped["salary"])
        # print(dumped["salary"])
        return CleanedDataObject(**dumped).model_dump()

    def _parse_salary(self, salary: str) -> Optional[float]:
        # print(salary, end=" -> ")
        remove_accessories = (
            lambda x: x.replace("$", "")
            .replace("£", "")
            .replace("€", "")
            .replace(",", "")
        )

        # up to £60k
        k_exp = r"[£$€]\s*\d{1,3}k"
        if matched_string := regex.search(k_exp, salary):
            # print(" 4 ", end="")
            return (
                float(remove_accessories(matched_string.group()).replace("k", ""))
                * 1000
            )

        # £60,000 - £70,000 annually
        range_exp = r"[£$€]\d{1,3}(?:,\d{3})?\s*-\s*[£$€]?\d{1,3}(?:,\d{3})?"
        if matched_string := regex.search(range_exp, salary):
            # print(" 1 ", end="")
            num1, num2 = [
                (
                    float(remove_accessories(item))
                    if len(item) > 4
                    else float(remove_accessories(item)) * 1000
                )
                for item in matched_string.group().split("-")
            ]
            return (num1 + num2) / 2

        # you could make $60,000
        nested_exp = r"[£$€]\s*\d{1,3},?\d{3}(?:\s*-\s*[£$€]?\d{1,3},?\d{3})?"
        if matched_string := regex.search(nested_exp, salary):
            # print(" 3 ", end="")
            return float(remove_accessories(matched_string.group()))

        # £60,000 annually
        padding_exp = r"[£$€]\d{1,3}(?:,\d{3})?"
        if matched_string := regex.search(padding_exp, salary):
            # print(" 2 ", end="")
            return float(remove_accessories(matched_string.group()))

        return None

    async def _persist(self, data: List[dict]) -> None:
        logger.info("Inserting data into the database")
        async with get_db_session() as sess:
            await sess.execute(
                insert(CleanedData).values(data).on_conflict_do_nothing()
            )
            await sess.commit()

        logger.info("Data inserted into the database")

    async def _transport(self, data: List[dict]) -> None:
        logger.info("Transporting data to chart generator")
        await REDIS_CLIENT.publish(CLEANED_DATA_KEY, json.dumps(data))
