locals {

  ##############
  ### Python ###
  ##############

  # S3 Bucket
  python_input_s3_bucket_name  = "utr1903-input-monitoring-lambda-with-opentelemetry-python"
  python_output_s3_bucket_name = "utr1903-output-monitoring-lambda-with-opentelemetry-python"

  # API Gateway
  python_api_gateway_name       = "python_api_gateway"
  python_api_gateway_stage_name = "prod"

  # Lambda - create
  python_lambda_create_iam_role_name            = "python_lambda_create_iam_role"
  python_lambda_create_function_name            = "python-lambda-create-otel"
  python_lambda_create_function_source_dir_path = "../../apps/01_python/create"
  python_lambda_create_function_zip_file_path   = "../../tmp/python_lambda_create.zip"

  # Lambda - update
  python_lambda_update_iam_role_name            = "python_lambda_update_iam_role"
  python_lambda_update_function_name            = "python-lambda-update-otel"
  python_lambda_update_function_source_dir_path = "../../apps/01_python/update"
  python_lambda_update_function_zip_file_path   = "../../tmp/python_lambda_update.zip"

  # Lambda - delete
  python_lambda_delete_iam_role_name            = "python_lambda_delete_iam_role"
  python_lambda_delete_function_name            = "python-lambda-delete-otel"
  python_lambda_delete_function_source_dir_path = "../../apps/01_python/delete"
  python_lambda_delete_function_zip_file_path   = "../../tmp/python_lambda_delete.zip"
}