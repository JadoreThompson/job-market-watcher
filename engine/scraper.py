import asyncio
import json
import logging

from httpx import AsyncClient, ReadTimeout
from random import random
from playwright.async_api import async_playwright, Page, Locator
from sqlalchemy import insert
from typing import List

from config import CANARY_EXE_PATH, CANARY_USER_DATA_PATH, LLM_API_KEY, LLM_BASE_URL
from db_models import ScrapedData
from utils.db import get_db_session
from .models import LLMExtractedObject, InitialExtractedObject
from .exc import LLMAPIError

logger = logging.getLogger(__name__)


class Scraper:
    def __init__(self, url: str, *, sleep: int = 2, timeout: int = 5) -> None:
        self._url = url
        self._sleep = sleep
        self._timeout = timeout
        self._queue = asyncio.Queue()

    async def init(self) -> None:
        asyncio.create_task(self._handle_llm())
        await self.run_scraper()

    async def run_scraper(self) -> None:
        await asyncio.sleep(random() * 50)
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

    async def _scrape_page(self, page: Page) -> None:
        cards = await self._locate_cards(page)

        if not cards:
            logger.info("No cards located")

        logger.info("Beginning scrape on individual cards")

        data: List[InitialExtractedObject] = []

        for card in cards:
            data.append(await self._scrape_card(page, card))
            await asyncio.sleep(self._sleep)

            if dimensions := await card.bounding_box():
                await page.mouse.wheel(0, dimensions["height"])

        self._queue.put_nowait(data)

    async def _locate_cards(self, page: Page) -> List[Locator]:
        cards = await page.locator("li[data-occludable-job-id]").all()
        logger.info(f"Found {len(cards)} cards")
        return cards

    async def _scrape_card(
        self, page: Page, li_card: Locator
    ) -> InitialExtractedObject:
        await li_card.click()

        payload = InitialExtractedObject(
            url=page.url,
            title=await page.locator(
                ".t-24.job-details-jobs-unified-top-card__job-title a"
            ).text_content(),
            company=await page.locator(
                "div.job-details-jobs-unified-top-card__company-name a"
            ).text_content(),
            content=await page.locator("div.jobs-box__html-content").inner_html(),
        )

        return payload

    async def _fetch_attributes(
        self, payload: InitialExtractedObject, session: AsyncClient
    ) -> dict:
        template = """"\
        You're an expert JSON parser, able to extract the following attributes from
        the data I've attached.\
        
        Attributes:
            - salary of the role. For example "$100,000 - $120,000" or "Competitive" 
            or "Not specified" or "$500 per hour"
            - location of the role
            - responsibilities of the role as a list of strings. For example 
            ["Designing and developing applications", "Writing clean code"]
            - requirements of the role as a list of strings. For example 
            ["3+ years of experience", "Strong communication skills"]
            
        Ensure you extract the attributes and send them back to me in a JSON with keys. 
        This is a strict response schema. I only want this JSON schema within the response. 

        The only keys you should have in the JSON are:
            - salary
            - location
            - responsibilities
            - requirements
            
        This is a strict requirement. Failure to follow this schema will result in a failed response.
            
        Here's an example of the JSON schema:
        Ensure you follow the JSON schema above.
            
        I've attached the data for you to parse below:
        {data}
        """
        rsp = await session.post(
            LLM_BASE_URL + "/agents/completions",
            json={
                "agent_id": "ag:a205eb03:20250326:untitled-agent:a2ed9362",
                "messages": [
                    {"role": "user", "content": template.format(data=payload.content)}
                ],
            },
        )

        if rsp.status_code != 200:
            raise LLMAPIError(f"Failed to fetch attributes. Status: {rsp.status_code}")

        content = (
            rsp.json()["choices"][0]["message"]["content"]
            .replace("```json", "")
            .replace("```", "")
        )

        return json.loads(content)

    async def _handle_llm(self) -> None:
        cleaned_data: List[LLMExtractedObject] = []

        while True:
            payloads: List[InitialExtractedObject] = await self._queue.get()

            async with AsyncClient(
                headers={"Authorization": f"Bearer {LLM_API_KEY}"}
            ) as session:
                for payload in payloads:
                    try:
                        extracted_data: dict = await self._fetch_attributes(
                            payload, session
                        )
                        cleaned_data.append(
                            LLMExtractedObject(**payload.model_dump(), **extracted_data)
                        )
                    except (ReadTimeout, LLMAPIError):
                        pass

            if len(cleaned_data):
                logger.info("Finished processing data")
                logger.info("Inserting data into database")
                async with get_db_session() as sess:
                    await sess.execute(
                        insert(ScrapedData).values(
                            [data.model_dump() for data in cleaned_data]
                        )
                    )
                    await sess.commit()
                logger.info("Data inserted into database")

    @property
    def url(self) -> str:
        return self._url


if __name__ == "__main__":
    asyncio.run(
        Scraper(
            "https://www.linkedin.com/jobs/search/?&keywords=software%20engineer"
        ).run_scraper()
    )
