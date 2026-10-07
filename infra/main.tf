resource "aws_s3_bucket" "quotes" {
  bucket = "quotes-bucket-${random_id.suffix.hex}"
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_sqs_queue" "scraper" {
  name                       = "scraper-queue"
  visibility_timeout_seconds = 300
  message_retention_seconds  = 86400
}