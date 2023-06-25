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
data "archive_file" "python_lambda" {
  type        = "zip"
  source_dir  = "../../apps/python"
  output_path = local.python_lambda_function_zip_file_path
}
