##########
### S3 ###
##########

resource "aws_s3_bucket" "input" {
  bucket_prefix = local.input_s3_bucket_name

  force_destroy = true
}

resource "aws_s3_bucket" "output" {
  bucket_prefix = local.output_s3_bucket_name

  force_destroy = true
}