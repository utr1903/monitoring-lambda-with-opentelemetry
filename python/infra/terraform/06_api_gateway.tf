###################
### API Gateway ###
###################

# API gateway
resource "aws_apigatewayv2_api" "python" {
  name          = local.python_api_gateway_name
  protocol_type = "HTTP"
}

# Cloudwatch log group
resource "aws_cloudwatch_log_group" "api_gateway_python" {
  name              = "/aws/api_gateway_python/${aws_apigatewayv2_api.python.name}"
  retention_in_days = 7
}

# API gateway stage
resource "aws_apigatewayv2_stage" "python" {
  api_id = aws_apigatewayv2_api.python.id

  name        = local.python_api_gateway_stage_name
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_python.arn

    format = jsonencode({
      requestId               = "$context.requestId"
      sourceIp                = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      protocol                = "$context.protocol"
      httpMethod              = "$context.httpMethod"
      resourcePath            = "$context.resourcePath"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
      }
    )
  }
}

# API gateway integration
resource "aws_apigatewayv2_integration" "python" {
  api_id = aws_apigatewayv2_api.python.id

  integration_uri    = aws_lambda_function.python_create.invoke_arn
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
}

# API gateway route
resource "aws_apigatewayv2_route" "create" {
  api_id = aws_apigatewayv2_api.python.id

  route_key = "POST /create"
  target    = "integrations/${aws_apigatewayv2_integration.python.id}"
}

# Lambda permission for API gateway to invoke
resource "aws_lambda_permission" "allow_api_gateway_for_python_create" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.python_create.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.python.execution_arn}/*/*"
}

# API gateway invoke URL
output "python_api_gateway_invoke_url" {
  value = aws_apigatewayv2_stage.python.invoke_url
}
