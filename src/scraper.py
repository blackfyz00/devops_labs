# src/scraper.py
import logging
from typing import List

from playwright.async_api import async_playwright, Page, BrowserContext
from .models import Quote

logger = logging.getLogger(__name__)

class QuotesScraper:
    URL = "https://quotes.toscrape.com/scroll"
    QUOTE_SELECTOR = ".quote"
    TEXT_SELECTOR = ".text"
    AUTHOR_SELECTOR = ".author"
    TAG_SELECTOR = ".tag"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._context: BrowserContext | None = None

    async def __aenter__(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless, 
            args=["--no-sandbox"]
        )
        self._context = await self._browser.new_context()
        return self

    async def __aexit__(self, *exc):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def scroll_and_extract(self, max_scrolls: int = 50) -> List[Quote]:
        """Скроллит страницу и собирает все цитаты."""
        page = await self._context.new_page()
        await page.goto(self.URL, wait_until="networkidle")

        seen_texts: set[str] = set()
        quotes: List[Quote] = []
        prev_count = 0

        for i in range(max_scrolls):
            current_quotes = await self._parse_quotes(page, seen_texts)
            quotes.extend(current_quotes)

            if len(quotes) == prev_count:
                logger.info("Новых цитат не найдено после %d скроллов", i)
                break

            prev_count = len(quotes)
            logger.info("Скролл %d: собрано %d цитат", i + 1, len(quotes))

            # Скроллим вниз и ждём подгрузки нового контента
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)

        await page.close()
        return quotes

    async def _parse_quotes(self, page: Page, seen: set[str]) -> List[Quote]:
        """Парсит цитаты со страницы, пропуская дубликаты."""
        elements = await page.query_selector_all(self.QUOTE_SELECTOR)
        new_quotes: List[Quote] = []

        for el in elements:
            text_el = await el.query_selector(self.TEXT_SELECTOR)
            author_el = await el.query_selector(self.AUTHOR_SELECTOR)
            tag_els = await el.query_selector_all(self.TAG_SELECTOR)

            text = (await text_el.inner_text()).strip() if text_el else ""
            author = (await author_el.inner_text()).strip() if author_el else ""
            tags = [(await t.inner_text()).strip() for t in tag_els]

            if not text or text in seen:
                continue

            seen.add(text)
            new_quotes.append(Quote(text=text, author=author, tags=tags))

        return new_quotes