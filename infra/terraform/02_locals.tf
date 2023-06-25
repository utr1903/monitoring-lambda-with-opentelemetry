locals {

  ##############
  ### Python ###
  ##############

  # API Gateway
  python_api_gateway_name       = "python_api_gateway"
  python_api_gateway_stage_name = "prod"

  # Lambda
  python_lambda_iam_role_name          = "python_iam_for_lambda"
  python_lambda_function_name          = "lambda-python-otel"
  python_lambda_function_zip_file_path = "../../tmp/python_lambda.zip"
}
