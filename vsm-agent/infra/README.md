# VSM Agent Lambda - Terraform Deployment

This directory contains Terraform configuration to deploy the VSM Agent Lambda function with API Gateway, Cognito authorization, and CORS support.

## Prerequisites

- Terraform >= 1.0
- AWS CLI configured with appropriate credentials
- Python 3.12 (for Lambda runtime)

## Configuration

1. Copy the example variables file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` with your configuration:
   - AWS region and environment
   - Lambda settings (timeout, memory)
   - Cognito configuration (use existing or create new)
   - CORS allowed origins

## Cognito Setup

### Option 1: Use Existing Cognito User Pool

If you already have a Cognito User Pool:

```hcl
cognito_user_pool_id       = "us-east-1_XXXXXXXXX"
cognito_user_pool_client_id = "xxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### Option 2: Create New Cognito User Pool

Leave the Cognito variables empty to create a new user pool:

```hcl
cognito_user_pool_id       = ""
cognito_user_pool_client_id = ""
```

The Terraform will automatically create a new user pool and client.

## CORS Configuration

CORS is configured at two levels:

1. **API Gateway Level**: Configured in `main.tf` via `cors_configuration` block
   - Handles preflight OPTIONS requests
   - Sets allowed origins, methods, and headers

2. **Lambda Level**: CORS headers are added to all responses in the handler code
   - Ensures CORS headers are present even if API Gateway doesn't handle them
   - Headers are added to all responses including errors

## Deployment

1. Initialize Terraform:
   ```bash
   terraform init
   ```

2. Review the deployment plan:
   ```bash
   terraform plan
   ```

3. Apply the configuration:
   ```bash
   terraform apply
   ```

4. After deployment, note the outputs:
   - `api_gateway_url`: Your API endpoint
   - `cognito_user_pool_id`: User pool ID for authentication
   - `cognito_user_pool_client_id`: Client ID for authentication

## API Endpoints

All endpoints are prefixed with `/v1/agent` and require Cognito authentication:

### Agent Endpoints
- `POST /v1/agent/invoke` - Main agent invocation
- `POST /v1/agent/sprint/plan` - Sprint planning
- `POST /v1/agent/sprint/review` - Sprint review
- `GET /v1/agent/sprint/{sprintId}/status` - Sprint status
- `POST /v1/agent/backlog/refine` - Backlog refinement
- `POST /v1/agent/standup/analyze` - Standup analysis
- `POST /v1/agent/decision-log/create` - Create decision log
- `POST /v1/agent/query` - Agent query

### Mock Management Endpoints
- `GET /v1/agent/mocks/config` - Get mock configuration
- `GET /v1/agent/mocks` - List mocks
- `POST /v1/agent/mocks` - Create mock
- `GET /v1/agent/mocks/{mockId}` - Get mock
- `PUT /v1/agent/mocks/{mockId}` - Update mock
- `DELETE /v1/agent/mocks/{mockId}` - Delete mock
- `DELETE /v1/agent/mocks` - Clear all mocks
- `GET /v1/agent/mocks/export` - Export mocks
- `POST /v1/agent/mocks/import` - Import mocks
- `POST /v1/agent/mocks/test` - Test mock matching
- `POST /v1/agent/mocks/reset-hits` - Reset hit counts
- `POST /v1/agent/mocks/load-defaults` - Load default mocks

## Authentication

All endpoints (except OPTIONS for CORS) require a valid Cognito JWT token in the `Authorization` header:

```
Authorization: Bearer <cognito-jwt-token>
```

The Lambda handler extracts user information from the JWT token:
- User ID (`sub` claim)
- Username (`cognito:username` claim)
- Email (`email` claim)

This information is available in the request context and logged for traceability.

## CORS Support

CORS is fully configured:

- **Preflight requests**: Handled by API Gateway and Lambda (OPTIONS method)
- **Response headers**: All responses include CORS headers:
  - `Access-Control-Allow-Origin: *`
  - `Access-Control-Allow-Methods: GET,POST,PUT,DELETE,OPTIONS,PATCH`
  - `Access-Control-Allow-Headers: *`
  - `Access-Control-Allow-Credentials: true`

## Required Headers

All requests must include:
- `Authorization: Bearer <cognito-jwt-token>` (required for all endpoints except OPTIONS)
- `x-tenant-id: tenant-<id>` (required by Lambda handler)
- `Content-Type: application/json` (for POST/PUT requests)

## Outputs

After deployment, Terraform outputs:
- `api_gateway_url`: Base API Gateway URL
- `api_gateway_stage_url`: Full stage URL
- `lambda_function_name`: Lambda function name
- `lambda_function_arn`: Lambda function ARN
- `cognito_user_pool_id`: Cognito User Pool ID
- `cognito_user_pool_client_id`: Cognito User Pool Client ID

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

## Notes

- The Lambda function is packaged from the parent directory
- All Python dependencies must be included in the deployment package
- CloudWatch logs are retained for the specified number of days
- X-Ray tracing can be enabled via the `enable_xray` variable

