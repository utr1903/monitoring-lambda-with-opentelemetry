##########
### S3 ###
##########

resource "aws_s3_bucket" "items" {
  bucket = local.s3_bucket_name

  force_destroy = true

  tags = {
    name = local.s3_bucket_name
  }
}
