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

# Lambda - create
data "archive_file" "lambda_create_collector_config" {
  type        = "zip"
  source_dir  = local.lambda_create_collector_config_dir_path
  output_path = local.lambda_create_collector_config_zip_path
}

# Lambda - update
data "archive_file" "lambda_update_collector_config" {
  type        = "zip"
  source_dir  = local.lambda_update_collector_config_dir_path
  output_path = local.lambda_update_collector_config_zip_path
}

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
