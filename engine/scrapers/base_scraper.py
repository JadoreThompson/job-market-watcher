import asyncio
import json
import logging
import multiprocessing
import warnings

from contextlib import asynccontextmanager
from httpx import AsyncClient, ReadTimeout
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright
from random import random
from sqlalchemy import insert
from typing import AsyncGenerator, overload

from config import CANARY_EXE_PATH, CANARY_USER_DATA_PATH, LLM_API_KEY, LLM_BASE_URL
from db_models import ScrapedData
from engine.utils import PROGRAMMING_LANGUAGES
from utils.db import get_db_session
from ..exc import LLMError
from ..models import InitialExtractedObject, LLMExtractedObject


logger = logging.getLogger(__name__)


class BaseScraper:
    def __init__(
        self,
        url: str,
        clean_queue: multiprocessing.Queue,
        *,
        sleep: float = 2.0,
        timeout: float = 5.0,
        llm_rate_limit: int = 1,
    ) -> None:
        self._url = url
        self._sleep = sleep
        self._timeout = timeout
        self._queue = asyncio.Queue()
        self._clean_queue = clean_queue
        self._llm_rate_limit = llm_rate_limit
        self._is_running = False
        self._browser: BrowserContext = None
        self._industry_page: Page = None

    async def run(self) -> None:
        try:
            asyncio.create_task(self._handle_llm())
            await self._run_scraper()
        except Exception as e:
            msg = f"An error occurred casuing browser to collapse: {type(e)} {e}"
            logger.error(msg)
        finally:
            while not self._queue.empty():
                await asyncio.sleep(1)
            self._is_running = False
            
    @asynccontextmanager
    async def _init_browser(self) -> AsyncGenerator[Playwright, None]:
        await asyncio.sleep(random() * 10)  # Rate limit prevention
        async with async_playwright() as p:
            try:
                self._browser = await p.chromium.launch_persistent_context(
                    user_data_dir=CANARY_USER_DATA_PATH,
                    headless=False,
                    executable_path=CANARY_EXE_PATH,
                )
                self._is_running = True
                yield p
            except Exception as e:
                msg = f"An error occurred casuing browser to collapse: {type(e)} {e}"
                warnings.warn(msg)
                await asyncio.sleep(10**10)

    # Function to create page and other class specific data
    # as well as calling self._handle.
    @overload
    async def _run_scraper(self) -> None: ...

    # Infinite loop function to scrape all cards and pages
    @overload
    async def _handle(self, page: Page) -> None: ...

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
            - programming languages required for the role. You must only include these languages {PROGRAMMING_LANGUAGES}.
            If you see swiftui, put swift into the list instead
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

            content: str = (
                rsp.json()["choices"][0]["message"]["content"]
                .replace("```json", "")
                .replace("```", "")
            )

            rtn_value: dict = json.loads(content)

            return rtn_value
        except (LLMError, json.JSONDecodeError) as e:
            raise LLMError(("" if isinstance(e, LLMError) else f"{type(e)}") + str(e))

    async def _handle_llm(self) -> None:
        cleaned_data: list[LLMExtractedObject] = []

        while not self._is_running:
            await asyncio.sleep(1)

        while self._is_running:
            payloads: list[InitialExtractedObject] = await self._queue.get()

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
                await self._persist(cleaned_data)
                cleaned_data.clear()

    async def _persist(self, data: list[LLMExtractedObject]) -> None:
        logger.info("Inserting scraped data into database")
        async with get_db_session() as sess:
            await sess.execute(
                insert(ScrapedData).values(
                    [d.model_dump() for d in data]
                )
            )
            await sess.commit()

        print(f"Pushing {len(data)} items to clean queue")
        self._clean_queue.put_nowait(data.copy())
        logger.info("Scraped data ata inserted into database")

    @property
    def url(self) -> str:
        return self._url
