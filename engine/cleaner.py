import asyncio
from multiprocessing import Queue
from queue import Empty
from typing import List
from .models import LLMExtractedObject

# Designed to be ran within it's own process
class Cleaner:
    def __init__(self, queue: Queue, *, sleep: int = 1) -> None:
        self._queue = queue
        self.sleep = sleep

    async def run(self) -> None:
        while True:
            try:
                data: List[LLMExtractedObject] = self._queue.get(block=True)
                for d in data:
                    self.clean(d)
            except Empty:
                await asyncio.sleep(self.sleep)
                
    def clean(self, data: LLMExtractedObject):
        print(data.salary)
        ...