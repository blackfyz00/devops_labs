import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime

import redis
from .scraper import QuotesScraper
from .models import ScrapingResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
RESULTS_DIR = os.getenv("RESULTS_DIR", "/srv/quotes-scraper/results")
STREAM_NAME = "jobs"
GROUP_NAME = "scrapers"
CONSUMER_NAME = f"consumer-{os.getpid()}"

def get_redis_client():
    return redis.from_url(
        REDIS_URL, 
        decode_responses=False,
        protocol=2
    )

async def process_job(r: redis.Redis, msg_id: bytes, data: dict):
    """Обрабатывает одно задание."""
    job_id = data[b"job_id"].decode()
    url = data[b"url"].decode()
    
    logger.info(f"Processing job {job_id} for URL: {url}")
    
    try:
        async with QuotesScraper(headless=True) as scraper:
            quotes = await scraper.scroll_and_extract() 
            
            result = ScrapingResult(quotes=quotes, total_count=len(quotes))
            json_data = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
            
            tmp_path = os.path.join(RESULTS_DIR, f".tmp-{job_id}.json")
            final_path = os.path.join(RESULTS_DIR, f"{job_id}.json")
            
            os.makedirs(RESULTS_DIR, exist_ok=True)
            
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(json_data)
            
            os.replace(tmp_path, final_path)
            logger.info(f"Saved result to {final_path}")
            
            r.xack(STREAM_NAME, GROUP_NAME, msg_id)
            logger.info(f"Acked message {msg_id.decode()}")
            
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}", exc_info=True)

def consume_loop():
    """Основной цикл потребления сообщений."""
    r = get_redis_client()
    
    try:
        r.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
        logger.info(f"Created consumer group '{GROUP_NAME}' on stream '{STREAM_NAME}'")
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP Consumer Group name already exists" not in str(e):
            raise
    
    logger.info(f"Consumer '{CONSUMER_NAME}' started.")
    
    while True:
        try:
            messages = r.xreadgroup(GROUP_NAME, CONSUMER_NAME, {STREAM_NAME: ">"}, count=1, block=5000)
            
            if not messages:
                continue
            
            for stream_name, entries in messages:
                for msg_id, data in entries:
                    asyncio.run(process_job(r, msg_id, data))
                    
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Critical error in consumer loop: {e}", exc_info=True)
            time.sleep(1)

if __name__ == "__main__":
    consume_loop()
