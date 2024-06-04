locals {

  # S3 Bucket
  input_s3_bucket_name  = "utr1903-input-python"
  output_s3_bucket_name = "utr1903-output-python"

  # SQS
  sqs_queue_name = "python-sqs-queue.fifo"

  # API Gateway
  api_gateway_name       = "python_api_gateway"
  api_gateway_stage_name = "prod"

  # Lambda - create
  lambda_create_iam_role_name            = "python_lambda_create_iam_role"
  lambda_create_function_name            = "python-lambda-create-otel"
  lambda_create_function_source_dir_path = "../../apps/create"
  lambda_create_function_zip_file_path   = "../../../tmp/python_lambda_create.zip"

  # Lambda - update
  lambda_update_iam_role_name            = "python_lambda_update_iam_role"
  lambda_update_function_name            = "python-lambda-update-otel"
  lambda_update_function_source_dir_path = "../../apps/update"
  lambda_update_function_zip_file_path   = "../../../tmp/python_lambda_update.zip"

  # Lambda - delete
  lambda_delete_iam_role_name            = "python_lambda_delete_iam_role"
  lambda_delete_function_name            = "python-lambda-delete-otel"
  lambda_delete_function_source_dir_path = "../../apps/delete"
  lambda_delete_function_zip_file_path   = "../../../tmp/python_lambda_delete.zip"

  # Lambda - check
  lambda_check_iam_role_name            = "python_lambda_check_iam_role"
  lambda_check_function_name            = "python-lambda-check-otel"
  lambda_check_function_source_dir_path = "../../apps/check"
  lambda_check_function_zip_file_path   = "../../../tmp/python_lambda_check.zip"
}
