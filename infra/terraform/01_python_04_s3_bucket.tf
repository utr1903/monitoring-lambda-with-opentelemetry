##########
### S3 ###
##########

resource "aws_s3_bucket" "python_input" {
  bucket = local.python_input_s3_bucket_name

  force_destroy = true
}

resource "aws_s3_bucket" "python_output" {
  bucket = local.python_output_s3_bucket_name

  force_destroy = true
}