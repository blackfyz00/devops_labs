# src/main.py
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from .scraper import QuotesScraper
from .models import ScrapingResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Конфигурация из переменных окружения
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))

def get_sqs_client():
    """Создает клиент SQS с настройками для локального Floci."""
    return boto3.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )

def get_s3_client():
    """Создает клиент S3 с настройками для локального Floci."""
    return boto3.client(
        "s3",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )

async def process_message(message_body: str) -> None:
    """Обрабатывает сообщение: скрапит данные и сохраняет в S3."""
    logger.info(f"Processing message: {message_body}")
    
    try:
        # Запускаем скрапер
        async with QuotesScraper(headless=True) as scraper:
            quotes = await scraper.scroll_and_extract()
            
            result = ScrapingResult(quotes=quotes, total_count=len(quotes))
            
            # Сериализуем в JSON
            json_data = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
            
            # Генерируем уникальный ключ
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
            s3_key = f"quotes/{timestamp}.json"
            
            # Загружаем в S3
            s3_client = get_s3_client()
            s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=s3_key,
                Body=json_data,
                ContentType="application/json",
            )
            
            logger.info(f"Successfully saved to S3: s3://{S3_BUCKET_NAME}/{s3_key}")
            
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        raise  # Пробрасываем исключение, чтобы сообщение не удалилось из очереди

def poll_sqs():
    """Бесконечный цикл опроса SQS очереди."""
    if not SQS_QUEUE_URL or not S3_BUCKET_NAME:
        logger.error("SQS_QUEUE_URL и S3_BUCKET_NAME должны быть установлены")
        sys.exit(1)
    
    sqs_client = get_sqs_client()
    logger.info(f"Starting SQS polling for queue: {SQS_QUEUE_URL}")
    
    while True:
        try:
            # Long polling (ждем до 20 секунд)
            response = sqs_client.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,
            )
            
            messages = response.get("Messages", [])
            
            if not messages:
                logger.debug("No messages received, waiting...")
                continue
            
            for message in messages:
                receipt_handle = message["ReceiptHandle"]
                message_body = message["Body"]
                
                try:
                    # Обрабатываем сообщение
                    asyncio.run(process_message(message_body))
                    
                    # ТОЛЬКО после успешной обработки удаляем из очереди
                    sqs_client.delete_message(
                        QueueUrl=SQS_QUEUE_URL,
                        ReceiptHandle=receipt_handle,
                    )
                    logger.info("Message deleted from queue")
                    
                except Exception as e:
                    logger.error(f"Failed to process message, it will be retried: {e}")
                    # Не удаляем сообщение - оно вернется в очередь
                
        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
            break
        except Exception as e:
            logger.error(f"Error in polling loop: {e}", exc_info=True)
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    poll_sqs()
