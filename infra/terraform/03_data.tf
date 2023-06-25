############
### Data ###
############

# IAM policy doc for Lambda
data "aws_iam_policy_document" "assume_role_lambda" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

# Lambda - Python
data "archive_file" "python_lambda_create" {
  type        = "zip"
  source_dir  = local.python_lambda_create_function_source_dir_path
  output_path = local.python_lambda_create_function_zip_file_path
}
