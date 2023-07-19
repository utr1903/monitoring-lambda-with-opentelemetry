##############
### Lambda ###
##############

# IAM role for Lambda
resource "aws_iam_role" "lambda_delete_iam" {
  name               = local.lambda_delete_iam_role_name
  assume_role_policy = data.aws_iam_policy_document.assume_role_lambda.json
}

# IAM policy attachment for Lambda to have full S3 access
resource "aws_iam_role_policy_attachment" "lambda_delete_s3_full_access" {
  role       = aws_iam_role.lambda_delete_iam.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# Cloudwatch log group for Lambda
resource "aws_cloudwatch_log_group" "lambda_delete" {
  name              = "/aws/lambda/${local.lambda_delete_function_name}"
  retention_in_days = 7
}

# IAM policy for Lambda logging
resource "aws_iam_policy" "lambda_delete_logging" {
  name        = "python_lambda_delete_logging"
  path        = "/"
  description = "IAM policy for logging from a lambda"
  policy      = data.aws_iam_policy_document.lambda_logging.json
}

# IAM policy attachment for Lambda to log to CloudWatch
resource "aws_iam_role_policy_attachment" "lambda_delete_logging" {
  role       = aws_iam_role.lambda_delete_iam.name
  policy_arn = aws_iam_policy.lambda_delete_logging.arn
}

# Lambda function
resource "aws_lambda_function" "delete" {
  filename      = local.lambda_delete_function_zip_file_path
  function_name = local.lambda_delete_function_name

  role    = aws_iam_role.lambda_delete_iam.arn
  handler = "lambda_function.lambda_handler"

  source_code_hash = data.archive_file.lambda_delete.output_base64sha256

  runtime = "python3.10"
  timeout = 10

  layers = [
    "arn:aws:lambda:${var.AWS_REGION}:901920570463:layer:aws-otel-python-amd64-ver-1-14-0:1"
  ]

  environment {
    variables = {
      AWS_LAMBDA_EXEC_WRAPPER             = "/opt/otel-instrument"
      OPENTELEMETRY_COLLECTOR_CONFIG_FILE = "/var/task/otel/collector.yaml"
      NEWRELIC_OTLP_ENDPOINT              = substr(var.NEWRELIC_LICENSE_KEY, 0, 2) == "eu" ? "otlp.eu01.nr-data.net:4317" : "otlp.nr-data.net:4317"
      NEWRELIC_LICENSE_KEY                = var.NEWRELIC_LICENSE_KEY
      INPUT_S3_BUCKET_NAME                = aws_s3_bucket.input.id
      OUTPUT_S3_BUCKET_NAME               = aws_s3_bucket.output.id
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_delete_logging,
    aws_cloudwatch_log_group.lambda_delete,
  ]
}

# CloudWatch cronjob event
resource "aws_cloudwatch_event_rule" "delete_cronjob" {
  name                = "python-delete-cronjob-event-rule"
  schedule_expression = "rate(1 minute)"
}

# Couple CloudWatch event with Lambda
resource "aws_cloudwatch_event_target" "profile_generator_lambda_target" {
  arn  = aws_lambda_function.delete.arn
  rule = aws_cloudwatch_event_rule.delete_cronjob.name
}

# Lambda permission for CloudWatch to invoke
resource "aws_lambda_permission" "allow_cloudwatch_for_delete" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.delete.arn
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.delete_cronjob.arn
}
