# =============================================================================
# VSM Agent Lambda - Main Infrastructure
# =============================================================================

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "vsm-agent"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# =============================================================================
# Data Sources
# =============================================================================

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Lambda deployment package
data "archive_file" "lambda_package" {
  type        = "zip"
  source_dir  = "${path.module}/.."
  output_path = "${path.module}/../dist/lambda-${var.environment}.zip"
  
  excludes = [
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    "tests",
    "*.dist-info",
    "dist",
    "infra",
    "*.tf",
    "*.tfvars",
    "*.tfstate",
    "*.tfplan",
    ".git",
    ".gitignore"
  ]
}

# =============================================================================
# IAM Role for Lambda
# =============================================================================

resource "aws_iam_role" "lambda_execution" {
  name = "vsm-agent-lambda-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_logs" {
  name = "vsm-agent-lambda-logs-${var.environment}"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Additional IAM policy for DynamoDB (if mock store uses DynamoDB)
resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "vsm-agent-lambda-dynamodb-${var.environment}"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          "arn:aws:dynamodb:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/vsm-mocks-*"
        ]
      }
    ]
  })
}

# IAM policy for invoking vsm-mcp-jira Lambda
resource "aws_iam_role_policy" "lambda_invoke_jira_mcp" {
  name = "vsm-agent-lambda-invoke-jira-mcp-${var.environment}"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:vsm-mcp-jira-*"
        ]
      }
    ]
  })
}

# =============================================================================
# Lambda Function
# =============================================================================

resource "aws_lambda_function" "agent" {
  function_name = "vsm-agent-${var.environment}"
  description   = "VSM Agent Orchestrator Lambda - Main agent orchestration service"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size

  filename         = data.archive_file.lambda_package.output_path
  source_code_hash = data.archive_file.lambda_package.output_base64sha256

  environment {
    variables = {
      ENVIRONMENT          = var.environment
      LOG_LEVEL            = var.log_level
      MOCK_MODE            = tostring(var.mock_mode)
      JIRA_MCP_LAMBDA_NAME = var.jira_mcp_lambda_name
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = {
    Name = "vsm-agent-${var.environment}"
  }
}

# =============================================================================
# CloudWatch Log Group
# =============================================================================

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.agent.function_name}"
  retention_in_days = var.log_retention_days
}

# =============================================================================
# Cognito User Pool (if not provided)
# =============================================================================

resource "aws_cognito_user_pool" "main" {
  count = var.cognito_user_pool_id == "" ? 1 : 0
  
  name = "vsm-agent-users-${var.environment}"

  username_attributes = ["email"]
  
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true
  }

  tags = {
    Name = "vsm-agent-users-${var.environment}"
  }
}

resource "aws_cognito_user_pool_client" "main" {
  count = var.cognito_user_pool_id == "" ? 1 : 0
  
  name         = "vsm-agent-client-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main[0].id

  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code", "implicit"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  supported_identity_providers        = ["COGNITO"]

  callback_urls = var.cognito_callback_urls
  logout_urls   = var.cognito_logout_urls

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]
}

# =============================================================================
# Cognito Users
# =============================================================================

resource "aws_cognito_user" "develop" {
  user_pool_id = local.cognito_user_pool_id_value
  username     = "develop@agentvsm.ia"
  
  attributes = {
    email          = "develop@agentvsm.ia"
    email_verified = "true"
  }

  # User will be created in FORCE_CHANGE_PASSWORD status
  # Password will be set via AWS CLI after user creation
  temporary_password = "Develop1!"
  
  lifecycle {
    prevent_destroy = false
  }
}

# Set permanent password using AWS CLI
# Note: This requires AWS CLI to be installed and configured
resource "null_resource" "set_user_password" {
  depends_on = [aws_cognito_user.develop]
  
  triggers = {
    user_pool_id = local.cognito_user_pool_id_value
    username     = aws_cognito_user.develop.username
  }

  provisioner "local-exec" {
    command     = "aws cognito-idp admin-set-user-password --user-pool-id ${local.cognito_user_pool_id_value} --username ${replace(aws_cognito_user.develop.username, "@", "@")} --password 'Develop1!' --permanent --region ${var.aws_region} --profile ${var.aws_profile}"
    interpreter = ["PowerShell", "-Command"]
    on_failure  = continue
  }
}

# =============================================================================
# API Gateway HTTP API
# =============================================================================

resource "aws_apigatewayv2_api" "main" {
  name          = "vsm-agent-${var.environment}"
  description   = "API Gateway for VSM Agent Lambda"
  protocol_type = "HTTP"

  cors_configuration {
    allow_credentials = length(var.cors_allowed_origins) > 0 && var.cors_allowed_origins[0] != "*" ? true : false
    allow_headers     = ["*"]
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    allow_origins     = var.cors_allowed_origins
    expose_headers    = ["x-trace-id", "x-correlation-id"]
    max_age           = 86400
  }
}

# Cognito Authorizer
locals {
  cognito_user_pool_id_value = var.cognito_user_pool_id != "" ? var.cognito_user_pool_id : aws_cognito_user_pool.main[0].id
  cognito_client_id_value    = var.cognito_user_pool_id != "" ? var.cognito_user_pool_client_id : aws_cognito_user_pool_client.main[0].id
}

resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.main.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "cognito-authorizer-${var.environment}"

  jwt_configuration {
    audience = [local.cognito_client_id_value]
    issuer   = "https://cognito-idp.${var.aws_region}.amazonaws.com/${local.cognito_user_pool_id_value}"
  }
}

# Lambda Integration
resource "aws_apigatewayv2_integration" "lambda" {
  api_id           = aws_apigatewayv2_api.main.id
  integration_type = "AWS_PROXY"

  integration_uri        = aws_lambda_function.agent.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# =============================================================================
# API Gateway Routes
# =============================================================================

# Main Agent Invocation Endpoint
resource "aws_apigatewayv2_route" "invoke" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /v1/agent/invoke"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

# Sprint Planning
resource "aws_apigatewayv2_route" "sprint_plan" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /v1/agent/sprint/plan"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

# Sprint Review
resource "aws_apigatewayv2_route" "sprint_review" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /v1/agent/sprint/review"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

# Sprint Status
resource "aws_apigatewayv2_route" "sprint_status" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /v1/agent/sprint/{sprintId}/status"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

# Backlog Refinement
resource "aws_apigatewayv2_route" "backlog_refine" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /v1/agent/backlog/refine"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

# Standup Analysis
resource "aws_apigatewayv2_route" "standup_analyze" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /v1/agent/standup/analyze"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

# Decision Log Create
resource "aws_apigatewayv2_route" "decision_log_create" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /v1/agent/decision-log/create"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

# Agent Query
resource "aws_apigatewayv2_route" "agent_query" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /v1/agent/query"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

# Agent Chat (Simple prompt endpoint)
resource "aws_apigatewayv2_route" "agent_chat" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /v1/agent/chat"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

# Mock Management Routes
resource "aws_apigatewayv2_route" "mocks_config" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /v1/agent/mocks/config"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "mocks_list" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /v1/agent/mocks"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "mocks_create" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /v1/agent/mocks"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "mocks_get" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /v1/agent/mocks/{mockId}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "mocks_update" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "PUT /v1/agent/mocks/{mockId}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "mocks_delete" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "DELETE /v1/agent/mocks/{mockId}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "mocks_clear" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "DELETE /v1/agent/mocks"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "mocks_export" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /v1/agent/mocks/export"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "mocks_import" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /v1/agent/mocks/import"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "mocks_test" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /v1/agent/mocks/test"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "mocks_reset_hits" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /v1/agent/mocks/reset-hits"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "mocks_load_defaults" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /v1/agent/mocks/load-defaults"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

# OPTIONS route for CORS preflight (no authorizer needed)
resource "aws_apigatewayv2_route" "options_catchall" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "OPTIONS /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# Catch-all route for any other paths (with authorizer)
resource "aws_apigatewayv2_route" "catchall" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

# =============================================================================
# API Gateway Stage
# =============================================================================

resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
}

# =============================================================================
# Lambda Permission for API Gateway
# =============================================================================

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.agent.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

