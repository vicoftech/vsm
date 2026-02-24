# VSM - Virtual Scrum Manager

Monorepo para el Virtual Scrum Manager con MCPs (Model Context Protocol) desplegados como Lambdas en AWS.

## Estructura del Repositorio

```
vsm/
├── vsm-agent/              # Agente Orquestador (Lambda)
├── vsm-mcp-jira/          # MCP Jira Lambda (Python)
├── vsm-mcp-confluence/    # MCP Confluence Lambda (Node.js)
├── vsm-product/           # Skills y reglas (submódulo)
└── .env.example           # Template de credenciales
```

## Componentes

### 1. VSM Agent (`vsm-agent/`)
Agente orquestador principal que coordina las llamadas a los MCPs y expone una API HTTP para invocación del agente.

**Endpoint principal:** `POST /v1/agent/invoke`

### 2. MCP Jira Lambda (`vsm-mcp-jira/`)
Lambda function en Python 3.12 que expone todas las herramientas del MCP Jira Extended como API HTTP.

**Herramientas:** Issues, Filters, Boards, Dashboards, Projects, Sprints

### 3. MCP Confluence Lambda (`vsm-mcp-confluence/`)
Lambda function en Node.js 20.x que expone todas las herramientas del MCP Confluence como API HTTP.

**Herramientas:** Pages, Spaces, Search (CQL), Labels

## Configuración

### Credenciales

1. Copiar `.env.example` a `.env` en la raíz del proyecto
2. Configurar las credenciales de Atlassian:

```bash
# Jira
JIRA_BASE_URL=https://agentvsm.atlassian.net
JIRA_EMAIL=mcp-jira-scrum-agent
JIRA_API_TOKEN=TU_TOKEN_AQUI

# Confluence
CONFLUENCE_DOMAIN=agentvsm.atlassian.net
CONFLUENCE_EMAIL=mcp-jira-scrum-agent
CONFLUENCE_API_TOKEN=TU_TOKEN_AQUI
```

**⚠️ IMPORTANTE:** El archivo `.env` NO debe versionarse (está en `.gitignore`)

## Despliegue

### MCP Jira Lambda

```bash
cd vsm-mcp-jira/infra
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply
```

### MCP Confluence Lambda

```bash
cd vsm-mcp-confluence
npm install
cd infra
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply
```

## Testing

### Tests Unitarios - Jira MCP

```bash
cd vsm-mcp-jira
pip install -r requirements.txt
pytest tests/ -v
```

### Tests Unitarios - Confluence MCP

```bash
cd vsm-mcp-confluence
npm install
npm test
```

## Uso de las APIs

### Jira MCP Lambda

```bash
# Listar herramientas disponibles
curl https://API_GATEWAY_URL/tools

# Ejecutar herramienta
curl -X POST https://API_GATEWAY_URL/tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "get_issue",
    "params": {
      "issue_key": "PROJ-123"
    }
  }'
```

### Confluence MCP Lambda

```bash
# Listar herramientas disponibles
curl https://API_GATEWAY_URL/tools

# Ejecutar herramienta
curl -X POST https://API_GATEWAY_URL/tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "create_page",
    "params": {
      "spaceKey": "TEST",
      "title": "Test Page",
      "body": "Page content"
    }
  }'
```

## Arquitectura

```
┌─────────────────┐
│  API Gateway    │
│  (HTTP API)     │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────┐
│ Jira  │ │Confluence│
│ MCP   │ │  MCP    │
│Lambda │ │ Lambda  │
└───────┘ └─────────┘
    │         │
    └────┬────┘
         │
    ┌────▼────┐
    │ Atlassian│
    │   Cloud  │
    └─────────┘
```

## Desarrollo Local

Para pruebas locales, puedes usar las credenciales del archivo `.env`:

```bash
# Jira MCP
cd vsm-mcp-jira
python -m pytest tests/ -v

# Confluence MCP
cd vsm-mcp-confluence
npm test
```

## Contribuir

1. Crear un branch desde `dev`
2. Hacer cambios
3. Ejecutar tests
4. Crear Pull Request


