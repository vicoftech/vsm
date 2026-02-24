# VSM MCPs - Postman Collection

Esta carpeta contiene la colección de Postman y el environment para probar los MCPs de Jira y Confluence desplegados en AWS.

## Archivos

- `VSM-MCPs.postman_collection.json` - Colección de Postman con todos los endpoints
- `VSM-MCPs.postman_environment.json` - Environment con las URLs y variables de configuración

## Instalación

1. Abre Postman
2. Importa la colección:
   - Click en "Import" en la esquina superior izquierda
   - Selecciona `VSM-MCPs.postman_collection.json`
3. Importa el environment:
   - Click en "Import" nuevamente
   - Selecciona `VSM-MCPs.postman_environment.json`
4. Selecciona el environment "VSM MCPs - Dev Environment" en el dropdown de environments (esquina superior derecha)

## Estructura de la Colección

### Jira MCP
- **Health Check** - Verifica que el servicio esté funcionando
- **List Tools** - Lista todas las herramientas disponibles
- **Issues** - Operaciones con issues (get, search, create, assign, etc.)
- **Projects** - Operaciones con proyectos
- **Sprints** - Operaciones con sprints
- **Boards** - Operaciones con boards

### Confluence MCP
- **Health Check** - Verifica que el servicio esté funcionando
- **List Tools** - Lista todas las herramientas disponibles
- **Pages** - Operaciones con páginas (get, create, update, delete, etc.)
- **Spaces** - Operaciones con espacios
- **Search** - Búsquedas en Confluence
- **Labels** - Operaciones con etiquetas

## Variables del Environment

- `jira_api_url` - URL base del API Gateway de Jira MCP
- `confluence_api_url` - URL base del API Gateway de Confluence MCP
- `jira_project_key` - Clave del proyecto de Jira para pruebas (por defecto: PROJ)
- `confluence_space_key` - Clave del espacio de Confluence para pruebas (por defecto: TEST)
- `test_issue_key` - Clave de issue de ejemplo (por defecto: PROJ-123)
- `test_page_id` - ID de página de ejemplo (por defecto: 12345)

## Uso

1. **Health Check**: Ejecuta primero los health checks para verificar que ambos servicios estén funcionando
2. **List Tools**: Revisa las herramientas disponibles en cada MCP
3. **Ejecutar Herramientas**: Usa los requests de ejemplo como base y modifica los parámetros según necesites

## Ejemplo de Request

Todos los requests de ejecución de herramientas siguen este formato:

```json
{
  "tool": "nombre_de_la_herramienta",
  "params": {
    "param1": "valor1",
    "param2": "valor2"
  }
}
```

## Notas

- Los valores de ejemplo (como `PROJ-123`, `12345`) deben ser reemplazados con valores reales de tu instancia de Jira/Confluence
- Las credenciales están configuradas en las variables de entorno de las Lambdas, no se requieren en los requests
- Todos los endpoints soportan CORS, por lo que pueden ser llamados desde cualquier origen

## URLs Actuales (Dev)

- **Jira MCP**: `https://r0j5helj8l.execute-api.us-east-1.amazonaws.com`
- **Confluence MCP**: `https://34wumz64x3.execute-api.us-east-1.amazonaws.com`

