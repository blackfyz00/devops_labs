output "bucket_name" {
  value = aws_s3_bucket.quotes.bucket
}

output "queue_url" {
  value = aws_sqs_queue.scraper.url
}