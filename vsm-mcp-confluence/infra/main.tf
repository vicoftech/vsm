# =============================================================================
# VSM MCP Confluence Lambda - Main Infrastructure
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
      Project     = "vsm-mcp-confluence"
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

# Build Lambda package with dependencies
resource "null_resource" "lambda_build" {
  triggers = {
    source_hash = sha256(join("", [
      for f in fileset("${path.module}/../src", "**") : filesha256("${path.module}/../src/${f}")
    ]))
    requirements_hash = filesha256("${path.module}/../requirements-lambda.txt")
  }

  provisioner "local-exec" {
    command     = "powershell.exe -ExecutionPolicy Bypass -File ${path.module}/build-lambda.ps1"
    working_dir = path.module
  }
}

# Lambda deployment package
data "archive_file" "lambda_package" {
  depends_on = [null_resource.lambda_build]
  
  type        = "zip"
  source_dir  = "${path.module}/../dist/build"
  output_path = "${path.module}/../dist/lambda-${var.environment}.zip"
  
  excludes = [
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    "tests",
    "*.dist-info"
  ]
}

# =============================================================================
# IAM Role for Lambda
# =============================================================================

resource "aws_iam_role" "lambda_execution" {
  name = "vsm-mcp-confluence-lambda-${var.environment}"

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
  name = "vsm-mcp-confluence-lambda-logs-${var.environment}"
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

resource "aws_iam_role_policy" "lambda_secrets" {
  name = "vsm-mcp-confluence-lambda-secrets-${var.environment}"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.confluence_credentials.arn
      }
    ]
  })
}

# =============================================================================
# Secrets Manager
# =============================================================================

resource "aws_secretsmanager_secret" "confluence_credentials" {
  name        = "vsm-mcp-confluence-credentials-${var.environment}"
  description = "Confluence API credentials for VSM MCP Confluence Lambda"

  tags = {
    Name = "vsm-mcp-confluence-credentials-${var.environment}"
  }
}

resource "aws_secretsmanager_secret_version" "confluence_credentials" {
  secret_id = aws_secretsmanager_secret.confluence_credentials.id
  secret_string = jsonencode({
    CONFLUENCE_DOMAIN   = var.confluence_domain
    CONFLUENCE_EMAIL    = var.confluence_email
    CONFLUENCE_API_TOKEN = var.confluence_api_token
  })
}

# =============================================================================
# Lambda Function
# =============================================================================

resource "aws_lambda_function" "mcp_confluence" {
  function_name = "vsm-mcp-confluence-${var.environment}"
  description   = "VSM MCP Confluence Lambda - Exposes Confluence MCP tools as HTTP API"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size

  filename         = data.archive_file.lambda_package.output_path
  source_code_hash = data.archive_file.lambda_package.output_base64sha256

  environment {
    variables = {
      CONFLUENCE_SECRET_NAME = aws_secretsmanager_secret.confluence_credentials.name
      ENVIRONMENT            = var.environment
      LOG_LEVEL              = var.log_level
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = {
    Name = "vsm-mcp-confluence-${var.environment}"
  }
}

# =============================================================================
# CloudWatch Log Group
# =============================================================================

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.mcp_confluence.function_name}"
  retention_in_days = var.log_retention_days
}

# =============================================================================
# API Gateway HTTP API
# =============================================================================

resource "aws_apigatewayv2_api" "main" {
  name          = "vsm-mcp-confluence-${var.environment}"
  description   = "API Gateway for VSM MCP Confluence Lambda"
  protocol_type = "HTTP"

  cors_configuration {
    allow_credentials = false
    allow_headers     = ["content-type", "authorization"]
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_origins     = ["*"]
    expose_headers    = []
    max_age           = 3600
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id           = aws_apigatewayv2_api.main.id
  integration_type = "AWS_PROXY"

  integration_uri        = aws_lambda_function.mcp_confluence.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "tool" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /tool"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "tools" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /tools"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.mcp_confluence.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

