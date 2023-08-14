###################
### API Gateway ###
###################

# API gateway
resource "aws_apigatewayv2_api" "apigw" {
  name          = local.api_gateway_name
  protocol_type = "HTTP"
}

# Cloudwatch log group
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/api_gateway_java/${aws_apigatewayv2_api.apigw.name}"
  retention_in_days = 7
}

# API gateway stage
resource "aws_apigatewayv2_stage" "apigw_stage" {
  api_id = aws_apigatewayv2_api.apigw.id

  name        = local.api_gateway_stage_name
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn

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
resource "aws_apigatewayv2_integration" "apigw_integration" {
  api_id = aws_apigatewayv2_api.apigw.id

  integration_uri    = aws_lambda_function.create.invoke_arn
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
}

# API gateway route
resource "aws_apigatewayv2_route" "create" {
  api_id = aws_apigatewayv2_api.apigw.id

  route_key = "POST /create"
  target    = "integrations/${aws_apigatewayv2_integration.apigw_integration.id}"
}

# Lambda permission for API gateway to invoke
resource "aws_lambda_permission" "allow_api_gateway_for_create" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.apigw.execution_arn}/*/*"
}

# API gateway invoke URL
output "api_gateway_invoke_url" {
  value = aws_apigatewayv2_stage.apigw_stage.invoke_url
}
