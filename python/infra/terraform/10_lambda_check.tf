##############
### Lambda ###
##############

# IAM role for Lambda
resource "aws_iam_role" "lambda_check_iam" {
  name               = local.lambda_check_iam_role_name
  assume_role_policy = data.aws_iam_policy_document.assume_role_lambda.json
}

# IAM policy attachment for Lambda to have full S3 access
resource "aws_iam_role_policy_attachment" "lambda_check_s3_full_access" {
  role       = aws_iam_role.lambda_check_iam.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# IAM policy attachment for Lambda to have full SQS access
resource "aws_iam_role_policy_attachment" "lambda_check_sqs_full_access" {
  role       = aws_iam_role.lambda_check_iam.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSQSFullAccess"
}

# Cloudwatch log group for Lambda
resource "aws_cloudwatch_log_group" "lambda_check" {
  name              = "/aws/lambda/${local.lambda_check_function_name}"
  retention_in_days = 7
}

# IAM policy for Lambda logging
resource "aws_iam_policy" "lambda_check_logging" {
  name        = "python_lambda_check_logging"
  path        = "/"
  description = "IAM policy for logging from a lambda"
  policy      = data.aws_iam_policy_document.lambda_logging.json
}

# IAM policy attachment for Lambda to log to CloudWatch
resource "aws_iam_role_policy_attachment" "lambda_check_logging" {
  role       = aws_iam_role.lambda_check_iam.name
  policy_arn = aws_iam_policy.lambda_check_logging.arn
}

# Lambda function
resource "aws_lambda_function" "check" {
  filename      = local.lambda_check_function_zip_file_path
  function_name = local.lambda_check_function_name

  role    = aws_iam_role.lambda_check_iam.arn
  handler = "lambda_function.lambda_handler"

  source_code_hash = data.archive_file.lambda_check.output_base64sha256

  runtime = "python3.10"
  timeout = 10

  layers = [
    "arn:aws:lambda:${var.AWS_REGION}:901920570463:layer:aws-otel-python-amd64-ver-1-24-0:1"
  ]

  environment {
    variables = {
      AWS_LAMBDA_EXEC_WRAPPER             = "/opt/otel-instrument"
      OPENTELEMETRY_COLLECTOR_CONFIG_FILE = "/var/task/otel/collector.yaml"
      NEWRELIC_OTLP_ENDPOINT              = substr(var.NEWRELIC_LICENSE_KEY, 0, 2) == "eu" ? "otlp.eu01.nr-data.net:4317" : "otlp.nr-data.net:4317"
      NEWRELIC_LICENSE_KEY                = var.NEWRELIC_LICENSE_KEY
      OUTPUT_S3_BUCKET_NAME               = aws_s3_bucket.output.id
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_check_logging,
    aws_cloudwatch_log_group.lambda_check,
  ]
}

# Lambda trigger for SQS
resource "aws_lambda_event_source_mapping" "sqs_trigger_for_lambda" {
  event_source_arn = aws_sqs_queue.queue.arn
  function_name    = aws_lambda_function.check.arn
}
