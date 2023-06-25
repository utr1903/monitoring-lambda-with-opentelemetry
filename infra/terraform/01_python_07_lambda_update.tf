##############
### Lambda ###
##############

resource "aws_iam_role" "python_lambda_update_iam" {
  name               = local.python_lambda_update_iam_role_name
  assume_role_policy = data.aws_iam_policy_document.assume_role_lambda.json
}

resource "aws_iam_role_policy_attachment" "python_lambda_update_s3_full_access" {
  role       = aws_iam_role.python_lambda_update_iam.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_lambda_function" "python_update" {
  filename      = local.python_lambda_update_function_zip_file_path
  function_name = local.python_lambda_update_function_name

  role    = aws_iam_role.python_lambda_update_iam.arn
  handler = "lambda_function.lambda_handler"

  source_code_hash = data.archive_file.python_lambda_update.output_base64sha256

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
      S3_BUCKET_NAME                      = aws_s3_bucket.python.id
    }
  }
}

resource "aws_lambda_permission" "allow_s3_bucket_for_python_update" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.python_update.arn
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.python.arn
}

resource "aws_s3_bucket_notification" "thumbnail_notification" {
  bucket = aws_s3_bucket.python.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.python_update.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [
    aws_lambda_permission.allow_s3_bucket_for_python_update
  ]
}
