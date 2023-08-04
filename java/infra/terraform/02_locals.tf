locals {

  # S3 Bucket
  input_s3_bucket_name  = "utr1903-input-monitoring-lambda-with-opentelemetry-java"
  output_s3_bucket_name = "utr1903-output-monitoring-lambda-with-opentelemetry-java"

  # SQS
  sqs_queue_name = "java-sqs-queue.fifo"

  # API Gateway
  api_gateway_name       = "java_api_gateway"
  api_gateway_stage_name = "prod"

  # Lambda - create
  lambda_create_iam_role_name             = "java_lambda_create_iam_role"
  lambda_create_function_name             = "java-lambda-create-otel"
  lambda_create_function_jar_file_path    = "../../apps/create/target/create.jar"
  lambda_create_collector_config_dir_path = "../../apps/create/otel"
  lambda_create_collector_config_zip_path = "../../apps/create/otel/collector.zip"

  # Lambda - update
  lambda_update_iam_role_name             = "java_lambda_update_iam_role"
  lambda_update_function_name             = "java-lambda-update-otel"
  lambda_update_function_jar_file_path    = "../../apps/update/target/update.jar"
  lambda_update_collector_config_dir_path = "../../apps/update/otel"
  lambda_update_collector_config_zip_path = "../../apps/update/otel/collector.zip"

  # Lambda - delete
  lambda_delete_iam_role_name             = "java_lambda_delete_iam_role"
  lambda_delete_function_name             = "java-lambda-delete-otel"
  lambda_delete_function_jar_file_path    = "../../apps/delete/target/delete.jar"
  lambda_delete_collector_config_dir_path = "../../apps/delete/otel"
  lambda_delete_collector_config_zip_path = "../../apps/delete/otel/collector.zip"

  # Lambda - check
  lambda_check_iam_role_name             = "java_lambda_check_iam_role"
  lambda_check_function_name             = "java-lambda-check-otel"
  lambda_check_function_jar_file_path    = "../../apps/check/target/check.jar"
  lambda_check_collector_config_dir_path = "../../apps/check/otel"
  lambda_check_collector_config_zip_path = "../../apps/check/otel/collector.zip"
}
