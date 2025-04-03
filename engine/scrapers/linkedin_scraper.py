import asyncio
import logging
import multiprocessing
import warnings

from playwright.async_api import (
    Page,
    Locator,
    TimeoutError,
)
from .base_scraper import BaseScraper
from ..exc import ScrapingError
from ..models import InitialExtractedObject

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    """
    Scraper designed to scrape LinkedIn job listings.

    Attributes:
        url (str): The URL to scrape.
        clean_queue (multiprocessing.Queue): The queue used to transport data to the cleaner.
        sleep (int): The time to sleep between scraping individual cards.
        timeout (int): The time to wait before going to the next page.
        queue (asyncio.Queue): The queue used to transport data to the LLM handler.
        llm_rate_limit (int): The rate limit in seconds for LLM API requests.
    """

    def __init__(
        self,
        url: str,
        clean_queue: multiprocessing.Queue,
        *,
        sleep: float = 2.0,
        timeout: float = 5.0,
        llm_rate_limit: int = 1,
    ) -> None:
        super().__init__(
            url,
            clean_queue,
            sleep=sleep,
            timeout=timeout,
            llm_rate_limit=llm_rate_limit,
        )
        self._industry_page: Page = None

    async def _run_scraper(self) -> None:
        async with self._init_browser():
            page = await self._browser.new_page()
            self._industry_page = await self._browser.new_page()
            logger.info("Pages initialised")

            logger.info("Heading to URL")
            await page.goto(self._url)
            await self._handle(page)
            print("Sraping Finished")
            logger.info("Scraping finished")

    async def _handle(self, page: Page) -> None:
        cur_page = 0

        while True:
            await page.wait_for_selector(".scaffold-layout__list")

            if not await self._scrape_page(page):
                break

            logger.info("Finished scrape on individual cards ")

            await asyncio.sleep(self._timeout)
            cur_page += 1
            await page.goto(self._url + f"&start={cur_page * 25}")

    async def _scrape_page(self, page: Page) -> None:
        cards = await self._locate_cards(page)
        if not cards:
            logger.info("No cards located")
            return False

        logger.info("Beginning scrape on individual cards")

        data: list[InitialExtractedObject] = []

        for card in cards:
            try:
                data.append(await self._scrape_card(page, card))
                await asyncio.sleep(self._sleep)

                if dimensions := await card.bounding_box():
                    await page.mouse.wheel(0, dimensions["height"])
            except ScrapingError as e:
                m = f"Error whilst scraping: {str(e)}"
                warnings.warn(m)

        if data:
            self._queue.put_nowait(data)

        return True

    async def _locate_cards(self, page: Page) -> list[Locator]:
        cards = await page.locator("li[data-occludable-job-id]").all()
        logger.info(f"Found {len(cards)} cards")
        return cards

    async def _scrape_card(
        self, page: Page, li_card: Locator
    ) -> InitialExtractedObject:
        await li_card.click()

        try:
            payload = InitialExtractedObject(
                url=page.url,
                title=await page.locator(
                    ".t-24.job-details-jobs-unified-top-card__job-title a"
                ).text_content(),
                company=await page.locator(
                    ".job-details-jobs-unified-top-card__company-name a"
                ).text_content(),
                industry=await self._fetch_industry(page),
                location=await (
                    await page.locator(
                        ".t-black--light.mt2.job-details-jobs-unified-top-card__tertiary-description-container span"
                    ).all()
                )[0].text_content(),
                content=await page.locator("div.jobs-box__html-content").inner_html(),
            )
        except (TimeoutError, IndexError) as e:
            raise ScrapingError(str(e))

        return payload

    async def _fetch_industry(self, cur_page: Page) -> str:
        url: str = await cur_page.locator(
            ".job-details-jobs-unified-top-card__company-name a"
        ).get_attribute("href")
        await self._industry_page.goto(url)
        industry = await (
            await self._industry_page.locator(
                ".org-top-card-summary-info-list div"
            ).all()
        )[0].text_content()
        return industry
