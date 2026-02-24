# VSM MCP Confluence Lambda

Lambda function que expone las herramientas del MCP Confluence como API HTTP.

## Estructura

```
vsm-mcp-confluence/
├── src/
│   ├── handler.py              # Lambda handler principal
│   ├── confluence_client.py  # Cliente Confluence API
│   └── tools/
│       ├── pages.py            # Herramientas de páginas
│       ├── spaces.py           # Herramientas de espacios
│       ├── search.py           # Búsqueda CQL
│       └── labels.py           # Herramientas de labels
├── tests/
│   └── test_pages.py           # Tests unitarios
├── infra/
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── requirements.txt
├── pytest.ini
└── .env.example
```

## Herramientas Expuestas

### Páginas
- `create_page` - Crear página
- `update_page` - Actualizar página
- `get_page` - Obtener página
- `delete_page` - Eliminar página
- `get_page_content` - Obtener contenido de página
- `get_pages` - Listar páginas en un espacio

### Espacios
- `get_spaces` - Listar espacios
- `get_space` - Obtener espacio
- `create_space` - Crear espacio

### Búsqueda
- `search_cql` - Búsqueda CQL en Confluence
- `search_by_title` - Buscar por título
- `search_by_label` - Buscar por label

### Labels
- `add_labels` - Agregar labels a página
- `get_labels` - Obtener labels de página
- `remove_label` - Remover label de página

## Configuración

1. Crear archivo `.env` con las credenciales:
   ```
   CONFLUENCE_DOMAIN=agentvsm.atlassian.net
   CONFLUENCE_EMAIL=your-email@example.com
   CONFLUENCE_API_TOKEN=your-api-token
   ```

2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Ejecutar tests:
   ```bash
   pytest tests/ -v
   ```

4. Deploy con Terraform:
   ```bash
   cd infra
   terraform init
   terraform plan
   terraform apply
   ```

## Variables de Entorno

- `CONFLUENCE_DOMAIN` - Dominio de Confluence (ej: agentvsm.atlassian.net)
- `CONFLUENCE_EMAIL` - Email del usuario de Confluence
- `CONFLUENCE_API_TOKEN` - API token de Confluence

## API Endpoints

- `POST /tool` - Ejecutar una herramienta
- `GET /tools` - Listar herramientas disponibles
- `GET /health` - Health check

### Ejemplo de uso

```bash
curl -X POST https://your-api-gateway-url/tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "get_page",
    "params": {
      "page_id": "12345"
    }
  }'
```
