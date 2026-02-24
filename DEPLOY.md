# Guía de Despliegue - VSM MCPs

Guía paso a paso para desplegar los MCPs de Jira y Confluence como Lambdas en AWS.

## Prerrequisitos

1. AWS CLI configurado con profile `asap_dev`
2. Terraform >= 1.0 instalado
3. Python 3.12 (para Jira MCP)
4. Node.js 20.x (para Confluence MCP)
5. Credenciales de Atlassian configuradas

## Configuración Inicial

### 1. Configurar Credenciales

Crea un archivo `.env` en la raíz del proyecto basándote en `ENV_TEMPLATE.md`:

```bash
cp ENV_TEMPLATE.md .env
# Edita .env con tus credenciales
```

### 2. Instalar Dependencias

**Jira MCP:**
```bash
cd vsm-mcp-jira
pip install -r requirements.txt
```

**Confluence MCP:**
```bash
cd vsm-mcp-confluence
npm install
```

## Despliegue

### Opción 1: Despliegue Individual

#### Jira MCP Lambda

```bash
cd vsm-mcp-jira/infra

# Configurar variables
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con tus valores

# Inicializar y desplegar
terraform init
terraform plan
terraform apply
```

#### Confluence MCP Lambda

```bash
cd vsm-mcp-confluence/infra

# Configurar variables
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con tus valores

# Inicializar y desplegar
terraform init
terraform plan
terraform apply
```

### Opción 2: Despliegue con Script

```bash
# Desde la raíz del proyecto
./scripts/deploy-mcps.sh dev
```

## Testing

### Tests Unitarios

**Jira MCP:**
```bash
cd vsm-mcp-jira
pytest tests/ -v --cov=src
```

**Confluence MCP:**
```bash
cd vsm-mcp-confluence
npm test
```

### Testing de APIs Desplegadas

Una vez desplegados, puedes probar las APIs:

**Jira MCP:**
```bash
# Obtener URL del API Gateway
cd vsm-mcp-jira/infra
API_URL=$(terraform output -raw api_gateway_stage_url)

# Listar herramientas
curl $API_URL/tools

# Ejecutar herramienta
curl -X POST $API_URL/tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "get_issue",
    "params": {
      "issue_key": "PROJ-123"
    }
  }'
```

**Confluence MCP:**
```bash
# Obtener URL del API Gateway
cd vsm-mcp-confluence/infra
API_URL=$(terraform output -raw api_gateway_stage_url)

# Listar herramientas
curl $API_URL/tools

# Ejecutar herramienta
curl -X POST $API_URL/tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "get_spaces",
    "params": {
      "limit": 10
    }
  }'
```

## Variables de Terraform

### Jira MCP

| Variable | Descripción | Default |
|----------|-------------|---------|
| `jira_base_url` | URL base de Jira | - |
| `jira_email` | Email del usuario | - |
| `jira_api_token` | API token | - |
| `lambda_timeout` | Timeout en segundos | 30 |
| `lambda_memory_size` | Memoria en MB | 256 |

### Confluence MCP

| Variable | Descripción | Default |
|----------|-------------|---------|
| `confluence_domain` | Dominio de Confluence | - |
| `confluence_email` | Email del usuario | - |
| `confluence_api_token` | API token | - |
| `lambda_timeout` | Timeout en segundos | 30 |
| `lambda_memory_size` | Memoria en MB | 256 |

## Troubleshooting

### Error: Credenciales inválidas

Verifica que las credenciales en `terraform.tfvars` sean correctas y que el token no haya expirado.

### Error: Lambda timeout

Aumenta el `lambda_timeout` en `terraform.tfvars` si las operaciones tardan más.

### Error: Module not found (Python)

Asegúrate de que todas las dependencias estén en `requirements.txt` y que el paquete Lambda incluya todas las librerías.

### Error: Module not found (Node.js)

Ejecuta `npm install` antes de crear el paquete Lambda. El Terraform debería incluir `node_modules` en el zip.

## Monitoreo

Los logs están disponibles en CloudWatch:

- **Jira MCP:** `/aws/lambda/vsm-mcp-jira-{environment}`
- **Confluence MCP:** `/aws/lambda/vsm-mcp-confluence-{environment}`

## Limpieza

Para destruir los recursos:

```bash
cd vsm-mcp-jira/infra
terraform destroy

cd ../vsm-mcp-confluence/infra
terraform destroy
```


