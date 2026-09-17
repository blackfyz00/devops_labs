# src/main.py
import asyncio
import json
import logging
import sys
from pathlib import Path

from .scraper import QuotesScraper
from .models import ScrapingResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("out") 
OUTPUT_FILE = OUTPUT_DIR / "result.json"

async def main():
    logger.info("Запуск скрапера цитат...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        async with QuotesScraper(headless=True) as scraper:
            quotes = await scraper.scroll_and_extract()
            
            result = ScrapingResult(quotes=quotes, total_count=len(quotes))
            
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            
            logger.info(f"Успешно сохранено {result.total_count} цитат в {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Ошибка при скрапинге: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
