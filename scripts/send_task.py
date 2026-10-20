"""Скрипт для отправки тестового задания в SQS очередь."""
import os
import json
import boto3

SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")

def send_test_message():
    """Отправляет тестовое сообщение в SQS."""
    if not SQS_QUEUE_URL:
        print("ERROR: SQS_QUEUE_URL не установлен")
        return

    client = boto3.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )

    message_body = json.dumps({"action": "scrape_quotes"})

    response = client.send_message(
        QueueUrl=SQS_QUEUE_URL,
        MessageBody=message_body,
    )

    print(f"Message sent! ID: {response['MessageId']}")

if __name__ == "__main__":
    send_test_message()
