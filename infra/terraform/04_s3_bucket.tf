##########
### S3 ###
##########

resource "aws_s3_bucket" "items" {
  bucket = "monitoring-lambda-with-opentelemetry"

  force_destroy = true

  tags = {
    Name = "monitoring-lambda-with-opentelemetry"
  }
}
