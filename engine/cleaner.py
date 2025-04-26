import asyncio
import json
import logging
import multiprocessing
import regex

from queue import Empty
from typing import List, Optional
from sqlalchemy.dialects.postgresql import insert

from config import CLEANED_DATA_KEY, REDIS_CLIENT
from db_models import CleanedData
from utils.db import get_db_session
from .models import LLMExtractedObject


logger = logging.getLogger(__name__)


class Cleaner:
    """
    Cleans the extracted data and inserts it into the database.

    Attributes:
        queue (multiprocessing.Queue): The queue to get the data from.
        sleep (int): The time to sleep between checking the queue if it's empty.
    """

    def __init__(self, queue: multiprocessing.Queue, *, sleep: int = 1) -> None:
        self._queue = queue
        self.sleep = sleep

    async def run(self) -> None:
        cleaned_data = []
        dump_data: list[dict] = [] # temporary

        try:
            while True:
                try:
                    extracted_data: List[LLMExtractedObject] = self._queue.get(
                        block=True
                    )
                    logger.info(f"Cleaning {len(extracted_data)} items")

                    for data in extracted_data:
                        dump_data.append(data.model_dump())
                        cleaned_data.append(self.clean(data))

                    logger.info("Finished cleaning batch")
                    if cleaned_data:
                        await self._persist(cleaned_data)
                        await self._transport(cleaned_data)
                        cleaned_data.clear()
                except Empty:
                    await asyncio.sleep(self.sleep)
        finally:
            print("Cleaning finished")
            with open("data.json", "w") as f:
                json.dump(dump_data, f, indent=4)

    def clean(self, data: LLMExtractedObject) -> dict:
        dumped = data.model_dump()
        dumped["salary"] = self._parse_salary(dumped["salary"])
        return dumped

    def _parse_salary(self, salary: str) -> Optional[float]:
        remove_accessories = str.maketrans({"$": "", "£": "", "€": "", ",": ""})
        salary = salary.translate(remove_accessories).strip().lower()

        # Match "60k", "70k" (Ensure 5 digits at conversion)
        if matched := regex.fullmatch(r"(\d{1,3})k", salary):
            return float(matched.group(1)) * 1000

        # Match "60,000 - 70,000"(Ensure each is at least 5 digits)
        if matched := regex.fullmatch(
            r"(\d{1,3}(?:\d{3})?)\s*-\s*(\d{1,3}(?:\d{3})?)", salary
        ):
            num1, num2 = map(float, matched.groups())
            if num1 < 10000:
                num1 *= 1000
            if num2 < 10000:
                num2 *= 1000
            return (num1 + num2) / 2

        # Match "60,000" or similar (Ensure at least 5 digits)
        if matched := regex.fullmatch(r"\d{1,3}(?:\d{3})?", salary):
            num = float(matched.group())
            return num if num >= 10000 else num * 1000

        return None

    async def _persist(self, data: List[dict]) -> None:
        logger.info("Inserting cleaned data into the database")
        
        async with get_db_session() as sess:
            await sess.execute(
                insert(CleanedData)
                .values(data)
                .on_conflict_do_nothing("cleaned_data_url_key")
            )
            await sess.commit()

        logger.info("Cleaned data inserted into the database")

    async def _transport(self, data: List[dict]) -> None:
        logger.info("Transporting cleaned data to chart generator")
        await REDIS_CLIENT.publish(CLEANED_DATA_KEY, json.dumps(data))
