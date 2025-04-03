import asyncio
import multiprocessing
from .base_scraper import BaseScraper


class IndeedScraper(BaseScraper):
    def __init__(
        self,
        url: str,
        clean_queue: multiprocessing.Queue,
        *,
        sleep: float = 2,
        timeout: float = 5,
        llm_rate_limit: int = 1
    ) -> None:
        super().__init__(
            url,
            clean_queue,
            sleep=sleep,
            timeout=timeout,
            llm_rate_limit=llm_rate_limit,
        )

    async def _run_scraper(self) -> None:
        async with self._init_browser():
            page = await self._browser.new_page()
            await page.goto(self._url)
            await asyncio.sleep(10**3)
