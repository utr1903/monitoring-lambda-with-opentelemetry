############
### Data ###
############

# Lambda - create
data "archive_file" "python_lambda_create" {
  type        = "zip"
  source_dir  = local.python_lambda_create_function_source_dir_path
  output_path = local.python_lambda_create_function_zip_file_path
}

# Lambda - update
data "archive_file" "python_lambda_update" {
  type        = "zip"
  source_dir  = local.python_lambda_update_function_source_dir_path
  output_path = local.python_lambda_update_function_zip_file_path
}
