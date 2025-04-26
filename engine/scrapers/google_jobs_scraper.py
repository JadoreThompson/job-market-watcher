import asyncio

from multiprocessing import Queue
from playwright.async_api import ElementHandle, Page, TimeoutError

from engine.exc import ScrapingError

from .base_scraper import BaseScraper
from ..models import InitialExtractedObject


class GoogleJobsScraper(BaseScraper):
    def __init__(
        self,
        url: str,
        clean_queue: Queue,
        *,
        sleep: float = 0.5,
        timeout: float = 1.0,
        llm_rate_limit: int = 1,
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
            print("Pages initialised")

            print("Heading to URL")
            await page.goto(self._url)

            await self._handle(page)
            print("Scraping Finished")

    async def _handle(self, page: Page) -> None:
        # try:
        #     # Clicking got it button
        #     await page.locator("g-raised-button[jsaction='G4Tkof']").click()
        # except TimeoutError:
        #     pass

        prev_cards: set[str] = set()
        strike: int = 0

        while strike < 3:
            cards: list[ElementHandle] = await self._locate_cards(page)

            if not cards:
                print("No cards found")
                break

            to_queue: list[InitialExtractedObject] = []

            for card in cards:
                if (href := await card.get_attribute("href")) not in prev_cards:
                    try:
                        to_queue.append(await self._scrape_card(card, page))
                        await asyncio.sleep(self._sleep)
                    except ScrapingError:
                        pass
                    finally:
                        prev_cards.add(href)
                        await page.locator("div#center_col").hover()
                        await page.mouse.wheel(0, (await card.bounding_box())["height"])

            if to_queue:
                self._queue.put_nowait(to_queue)
            else:
                strike += 1

            await asyncio.sleep(self._timeout)

    async def _locate_cards(self, page: Page) -> list[ElementHandle]:
        return await page.query_selector_all("a.MQUd2b")

    async def _scrape_card(
        self, card: ElementHandle, page: Page
    ) -> InitialExtractedObject:
        location: str = await (
            await card.query_selector("div.wHYlTd.FqK3wc.MKCbgd")
        ).text_content()

        if "london" not in location.lower():
            raise ScrapingError("Location not in London")

        await card.click()

        return InitialExtractedObject(
            url=await card.get_attribute("href"),
            title=await (await card.query_selector("div.tNxQIb.PUpOsf")).text_content(),
            company=await (
                await card.query_selector("div.wHYlTd.MKCbgd.a3jPc")
            ).text_content(),
            location=location,
            content=await page.locator("div#Sva75c div.NgUYpe").nth(0).inner_html(),
        )
