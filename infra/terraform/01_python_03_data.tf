############
### Data ###
############

# Lambda - Python
data "archive_file" "python_lambda_create" {
  type        = "zip"
  source_dir  = local.python_lambda_create_function_source_dir_path
  output_path = local.python_lambda_create_function_zip_file_path
}
