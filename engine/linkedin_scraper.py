import asyncio
import json
import logging
import warnings

from httpx import AsyncClient, ReadTimeout
from multiprocessing import Queue
from random import random
from playwright.async_api import async_playwright, Page, Locator, TimeoutError
from sqlalchemy import insert
from typing import List

from config import CANARY_EXE_PATH, CANARY_USER_DATA_PATH, LLM_API_KEY, LLM_BASE_URL
from db_models import ScrapedData
from utils.db import get_db_session
from .models import LLMExtractedObject, InitialExtractedObject
from .exc import LLMError, ScrapingError
from .utils import PROGRAMMING_LANGUAGES

logger = logging.getLogger(__name__)


class LinkedInScraper:
    """
    Scraper designed to scrape LinkedIn job listings.

    Attributes:
        url (str): The URL to scrape
        clean_queue (Queue): The queue used to transport data to the cleaner
        sleep (int): The time to sleep between scraping individual cards
        timeout (int): The time to wait before going to the next page
        queue (asyncio.Queue): The queue used to transport data to the LLM handler
        llm_rate_limit (int): The rate limit in seconds for LLM API requests
    """

    def __init__(
        self,
        url: str,
        clean_queue: Queue,
        *,
        sleep: int = 2,
        timeout: int = 5,
        llm_rate_limit: int = 1,
    ) -> None:
        self._url = url
        self._sleep = sleep
        self._timeout = timeout
        self._queue = asyncio.Queue()
        self._clean_queue = clean_queue
        self._llm_rate_limit = llm_rate_limit
        self._is_running = False

    async def init(self) -> None:
        asyncio.create_task(self._handle_llm())
        await self.run_scraper()

    async def run_scraper(self) -> None:
        await asyncio.sleep(random() * 50)  # Rate limit prevention

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch_persistent_context(
                    user_data_dir=CANARY_USER_DATA_PATH,
                    headless=False,
                    executable_path=CANARY_EXE_PATH,
                )
                self._is_running = True
                logger.info("Browser initialised")

                page = await browser.new_page()
                logger.info("Page initialised")

                logger.info("Heading to URL")
                await page.goto(self._url)
                await self._handle(page)
                logger.info("Scraping finished")
                await asyncio.sleep(10**10)
        except Exception as e:
            logger.error(f"An error occurred: {e}")
        finally:
            self._is_running = False

    async def _handle(self, page: Page) -> None:
        cur_page = 0
        finished = False

        while not finished:
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

        data: List[InitialExtractedObject] = []

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

    async def _locate_cards(self, page: Page) -> List[Locator]:
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

    async def _fetch_attributes(
        self, payload: InitialExtractedObject, session: AsyncClient
    ) -> dict:
        template = f""""\
        You're an expert JSON parser, able to extract key insights from HTML code
        . Your job is to extract the following insights from
        the data I've attached.
        
        Attributes:
            - salary of the role. For example "$100,000 - $120,000" or "Competitive" 
            or "Not specified" or "$500 per hour"
            - programming languages required for the role. You must only include these languages {PROGRAMMING_LANGUAGES}
            - responsibilities of the role as a list of strings. For example 
            ["Designing and developing applications", "Writing clean code"]
            - requirements of the role as a list of strings. For example 
            ["3+ years of experience", "Strong communication skills"]
            - extras. These are a collection of keywords that can be used to associate the job positing.
            For example ["quantitative development", "fintech"].
            
        Ensure you extract the attributes and send them back to me in a JSON with keys. 
        This is a strict response schema. I only want this JSON schema within the response. 

        I'm now going to show you the only JSON schema I will accept along with their
        associated python type.
            - salary: str
            - programming_languages: List[str]
            - responsibilities: List[str]
            - requirements: List[str]
            - extras: List[str]
            
        This is a strict requirement. Failure to follow this schema will result in a failed response.
            
        Here's an example of the JSON schema:
        Ensure you follow the JSON schema above.
            
        I've attached the data for you to parse below:
        {{data}}
        
        Here is the job tite: {{job_title}}
        
        You must ensure all keys I specified are within the JSON
        """
        try:
            rsp = await session.post(
                LLM_BASE_URL + "/agents/completions",
                json={
                    "agent_id": "ag:a205eb03:20250326:untitled-agent:a2ed9362",
                    "messages": [
                        {
                            "role": "user",
                            "content": template.format(
                                data=payload.content, job_title=payload.title
                            ),
                        }
                    ],
                },
            )

            if rsp.status_code != 200:
                raise LLMError(f"Failed to fetch attributes. Status: {rsp.status_code}")

            content = (
                rsp.json()["choices"][0]["message"]["content"]
                .replace("```json", "")
                .replace("```", "")
            )

            rtn_value = json.loads(content)
            # print(rtn_value.keys())
            return rtn_value
        except (LLMError, json.JSONDecodeError) as e:
            raise LLMError(("" if isinstance(e, LLMError) else f"{type(e)}") + str(e))

    async def _handle_llm(self) -> None:
        cleaned_data: List[LLMExtractedObject] = []

        while not self._is_running:
            await asyncio.sleep(1)

        while self._is_running:
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
                    except (ReadTimeout, LLMError):
                        pass

                    await asyncio.sleep(self._llm_rate_limit * (1 + random()))

            logger.info("Finished processing data")

            if cleaned_data:
                logger.info("Inserting data into database")
                # async with get_db_session() as sess:
                #     await sess.execute(
                #         insert(ScrapedData).values(
                #             [data.model_dump() for data in cleaned_data]
                #         )
                #     )
                #     await sess.commit()

                self._clean_queue.put_nowait(cleaned_data.copy())
                logger.info("Data inserted into database")
                cleaned_data.clear()

    @property
    def url(self) -> str:
        return self._url
