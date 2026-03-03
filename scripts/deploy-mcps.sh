#!/bin/bash
# Deploy script for VSM MCPs

set -e

ENVIRONMENT=${1:-dev}
AWS_PROFILE=${AWS_PROFILE:-asap_dev}

echo "🚀 Deploying VSM MCPs to environment: $ENVIRONMENT"
echo "Using AWS profile: $AWS_PROFILE"

# Deploy Jira MCP
echo ""
echo "📋 Deploying Jira MCP Lambda..."
cd vsm-mcp-jira/infra

if [ ! -f "terraform.tfvars" ]; then
    echo "⚠️  terraform.tfvars not found. Copying from example..."
    cp terraform.tfvars.example terraform.tfvvars
    echo "⚠️  Please edit terraform.tfvars with your credentials before continuing"
    exit 1
fi

terraform init
terraform plan -var="environment=$ENVIRONMENT" -out=jira.tfplan
terraform apply jira.tfplan

JIRA_API_URL=$(terraform output -raw api_gateway_stage_url)
echo "✅ Jira MCP deployed: $JIRA_API_URL"

# Deploy Confluence MCP
echo ""
echo "📄 Deploying Confluence MCP Lambda..."
cd ../../vsm-mcp-confluence

# Install dependencies
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

cd infra

if [ ! -f "terraform.tfvars" ]; then
    echo "⚠️  terraform.tfvars not found. Copying from example..."
    cp terraform.tfvars.example terraform.tfvars
    echo "⚠️  Please edit terraform.tfvars with your credentials before continuing"
    exit 1
fi

terraform init
terraform plan -var="environment=$ENVIRONMENT" -out=confluence.tfplan
terraform apply confluence.tfplan

CONFLUENCE_API_URL=$(terraform output -raw api_gateway_stage_url)
echo "✅ Confluence MCP deployed: $CONFLUENCE_API_URL"

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "Jira MCP API:    $JIRA_API_URL"
echo "Confluence MCP API: $CONFLUENCE_API_URL"
echo ""
echo "Test the APIs:"
echo "  curl $JIRA_API_URL/tools"
echo "  curl $CONFLUENCE_API_URL/tools"





