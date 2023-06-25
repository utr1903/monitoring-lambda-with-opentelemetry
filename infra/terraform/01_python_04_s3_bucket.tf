##########
### S3 ###
##########

resource "aws_s3_bucket" "python" {
  bucket = local.python_s3_bucket_name

  force_destroy = true

  tags = {
    name = local.python_s3_bucket_name
  }
}
