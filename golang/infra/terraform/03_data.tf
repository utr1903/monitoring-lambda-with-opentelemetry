############
### Data ###
############

# Caller identity
data "aws_caller_identity" "current" {}

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

# Lambda - create
data "archive_file" "lambda_create" {
  type        = "zip"
  source_dir  = local.lambda_create_function_source_dir_path
  output_path = local.lambda_create_function_zip_file_path
}

# Lambda - update
data "archive_file" "lambda_update" {
  type        = "zip"
  source_dir  = local.lambda_update_function_source_dir_path
  output_path = local.lambda_update_function_zip_file_path
}

# # Lambda - delete
# data "archive_file" "lambda_delete" {
#   type        = "zip"
#   source_dir  = local.lambda_delete_function_source_dir_path
#   output_path = local.lambda_delete_function_zip_file_path
# }

# # Lambda - check
# data "archive_file" "lambda_check" {
#   type        = "zip"
#   source_dir  = local.lambda_check_function_source_dir_path
#   output_path = local.lambda_check_function_zip_file_path
# }

# IAM policy doc for Lambda logging
data "aws_iam_policy_document" "lambda_logging" {
  statement {
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["arn:aws:logs:*:*:*"]
  }
}
