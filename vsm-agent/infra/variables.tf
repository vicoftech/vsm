# =============================================================================
# VSM Agent Lambda - Variables
# =============================================================================

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS profile to use for CLI commands"
  type        = string
  default     = "asap_dev"
}

variable "environment" {
  description = "Environment name (dev, qa, prod)"
  type        = string
  default     = "dev"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 30
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 256
}

variable "log_level" {
  description = "Logging level"
  type        = string
  default     = "INFO"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "enable_xray" {
  description = "Enable X-Ray tracing"
  type        = bool
  default     = false
}

variable "mock_mode" {
  description = "Enable mock mode (true) or use real MCP Lambdas (false)"
  type        = bool
  default     = false
}

variable "jira_mcp_lambda_name" {
  description = "Name of the vsm-mcp-jira Lambda function"
  type        = string
  default     = "vsm-mcp-jira-dev"
}

# Cognito Configuration
variable "cognito_user_pool_id" {
  description = "Existing Cognito User Pool ID (leave empty to create new)"
  type        = string
  default     = ""
}

variable "cognito_user_pool_client_id" {
  description = "Existing Cognito User Pool Client ID (required if cognito_user_pool_id is provided)"
  type        = string
  default     = ""
}

variable "cognito_callback_urls" {
  description = "Cognito callback URLs for OAuth"
  type        = list(string)
  default     = ["http://localhost:3000/callback", "https://localhost:3000/callback"]
}

variable "cognito_logout_urls" {
  description = "Cognito logout URLs for OAuth"
  type        = list(string)
  default     = ["http://localhost:3000/logout", "https://localhost:3000/logout"]
}

# CORS Configuration
variable "cors_allowed_origins" {
  description = "Allowed CORS origins"
  type        = list(string)
  default     = ["*"]
}

