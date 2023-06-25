locals {

  ##############
  ### Python ###
  ##############

  # S3 Bucket
  s3_bucket_name = "monitoring-lambda-with-opentelemetry"

  # API Gateway
  python_api_gateway_name       = "python_api_gateway"
  python_api_gateway_stage_name = "prod"

  # Lambda
  python_lambda_iam_role_name                   = "python_lambda_create_iam_role"
  python_lambda_create_function_name            = "python-lambda-create-otel"
  python_lambda_create_function_source_dir_path = "../../apps/python/create"
  python_lambda_create_function_zip_file_path   = "../../tmp/python_lambda_create.zip"
}
