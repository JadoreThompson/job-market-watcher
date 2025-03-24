import asyncio
import logging
from collections import deque
from random import random
from typing import List
from playwright.async_api import async_playwright, Page, Locator
from config import CANARY_EXE_PATH, CANARY_USER_DATA_PATH

logger = logging.getLogger(__name__)


class Scraper:
    def __init__(
        self, url: str, *, batch_size: int = 50, sleep: int = 2, timeout: int = 5
    ) -> None:
        self._url = url
        self.batch_size = batch_size
        self._collection = deque()
        self._sleep = sleep
        self._timeout = timeout

    async def run(self) -> None:
        await asyncio.sleep(random() * 100)
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=CANARY_USER_DATA_PATH,
                headless=False,
                executable_path=CANARY_EXE_PATH,
            )
            logger.info("Browser initialised")
            page = await browser.new_page()
            logger.info("Page initialised")

            logger.info("Heading to URL")
            await page.goto(self._url)
            await self._handle(page)
            logger.info("Scraping finished")

    async def _handle(self, page: Page) -> None:
        cur_page = 1
        finished = False

        while not finished:
            await page.wait_for_selector(".scaffold-layout__list")
            await self._scrape_page(page)
            logger.info("Finished scrape on individual cards " + __name__)

            paginations: List[Locator] = await page.locator(
                "ul.artdeco-pagination__pages.artdeco-pagination__pages--number li"
            ).all()

            found_next_page = False
            for pbtn in paginations:
                if (
                    await pbtn.get_attribute("data-test-pagination-page-btn")
                    == f"{cur_page + 1}"
                ):
                    found_next_page = True
                    await asyncio.sleep(self._timeout)
                    await pbtn.click()
                    cur_page += 1
                    break

            if not found_next_page:
                break

    async def _locate_cards(self, page: Page) -> List[Locator]:
        parent_container = page.locator(".wWyJsWGiVbcipleFlmnygUjvgjBqenBxXbso")
        cards = await parent_container.locator("li.ember-view").all()
        logger.info(f"Found {len(cards)} cards")
        return cards

    async def _scrape_page(self, page: Page) -> None:
        cards = await self._locate_cards(page)

        if not cards:
            logger.info("Shutting down - No cards located")

        logger.info("Beginning scrape on individual cards")

        for card in cards:
            await self._scrape_card(page, card)
            await asyncio.sleep(self._sleep)

            if dimensions := await card.bounding_box():
                await page.mouse.wheel(0, dimensions["height"])

    async def _scrape_card(self, page: Page, li_card: Locator) -> None:
        await li_card.click()

        payload = {
            "url": page.url,
            "title": await page.locator(
                ".t-24.job-details-jobs-unified-top-card__job-title a"
            ).text_content(),
        }
        self._collection.append(payload)
        print(payload)

    @property
    def url(self) -> str:
        return self._url


if __name__ == "__main__":
    asyncio.run(
        Scraper(
            "https://www.linkedin.com/jobs/search/?&keywords=software%20engineer"
            # "https://www.linkedin.com/jobs/search/?currentJobId=4191954411&f_E=5&f_TPR=r86400&keywords=software%20engineer&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&sortBy=R"
        ).run()
    )
