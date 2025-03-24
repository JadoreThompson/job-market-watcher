import asyncio
from httpx import AsyncClient
from playwright.async_api import async_playwright

from config import CANARY_EXE_PATH, CANARY_USER_DATA_PATH


async def test_p() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=CANARY_USER_DATA_PATH,
            headless=False,
            executable_path=CANARY_EXE_PATH,
        )
        page = await browser.new_page()
        
        await page.goto("https://www.linkedin.com/jobs/")
        await asyncio.sleep(1000)


if __name__ == "__main__":
    asyncio.run(test_p())
