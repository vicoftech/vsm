# VSM - Postman Collections

Esta carpeta contiene las colecciones de Postman y los environments para probar los MCPs de Jira y Confluence, así como el VSM Agent Orchestrator desplegados en AWS.

## Archivos

### MCPs Collections
- `VSM-MCPs.postman_collection.json` - Colección de Postman con todos los endpoints de Jira y Confluence MCPs
- `VSM-MCPs.postman_environment.json` - Environment con las URLs y variables de configuración para MCPs

### Agent Collection
- `VSM-Agent.postman_collection.json` - Colección de Postman con todos los endpoints del VSM Agent Orchestrator
- `VSM-Agent.postman_environment.json` - Environment con las URLs, Cognito credentials y variables de configuración para el Agent

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

## VSM Agent Collection

### Instalación

1. Importa la colección `VSM-Agent.postman_collection.json`
2. Importa el environment `VSM-Agent.postman_environment.json`
3. Configura las variables en el environment:
   - `agent_api_url` - URL base del API Gateway del Agent (obtener de Terraform output)
   - `cognito_client_id` - ID del Cognito User Pool Client (obtener de Terraform output)
   - `cognito_user_pool_id` - ID del Cognito User Pool (obtener de Terraform output)
   - `aws_region` - Región de AWS (por defecto: us-east-1)
   - `tenant_id` - ID del tenant (por defecto: dev)

### Autenticación

1. **Get Cognito Token**: Ejecuta primero el request "Get Cognito Token" en la carpeta "Authentication"
   - Esto autenticará con el usuario `develop@agentvsm.ia` / `Develop1!`
   - Los tokens se guardarán automáticamente en las variables del environment
   - Todos los demás requests usarán automáticamente el token en el header `Authorization`

2. **Refresh Token**: Si el token expira, usa el request "Refresh Token" para obtener un nuevo token

### Estructura de la Colección

#### Authentication
- **Get Cognito Token** - Autentica con username/password y obtiene tokens
- **Refresh Token** - Refresca el access token usando el refresh token

#### Agent Endpoints
- **Invoke Agent** - Endpoint principal de invocación del agente
- **Sprint Plan** - Planificar un sprint
- **Sprint Review** - Revisar un sprint completado
- **Get Sprint Status** - Obtener estado de un sprint
- **Backlog Refinement** - Refinar items del backlog
- **Standup Analysis** - Analizar notas de standup
- **Create Decision Log** - Crear entrada en el log de decisiones
- **Agent Query** - Ejecutar una consulta al agente

#### Mock Management
- **Get Mock Config** - Obtener configuración de mocks
- **List Mocks** - Listar todos los mocks
- **Create Mock** - Crear un nuevo mock
- **Get Mock** - Obtener un mock específico
- **Update Mock** - Actualizar un mock
- **Delete Mock** - Eliminar un mock
- **Export Mocks** - Exportar todos los mocks
- **Import Mocks** - Importar mocks
- **Test Mock** - Probar matching de mocks
- **Load Default Mocks** - Cargar mocks por defecto
- **Reset Hit Counts** - Resetear contadores de hits
- **Clear All Mocks** - Limpiar todos los mocks

### Credenciales por Defecto

El environment incluye las siguientes credenciales preconfiguradas:
- **Username**: `develop@agentvsm.ia`
- **Password**: `Develop1!`

Estas credenciales se usan automáticamente en el request "Get Cognito Token".

## URLs Actuales (Dev)

- **Jira MCP**: `https://r0j5helj8l.execute-api.us-east-1.amazonaws.com`
- **Confluence MCP**: `https://34wumz64x3.execute-api.us-east-1.amazonaws.com`
- **VSM Agent**: Configurar después del despliegue con Terraform (ver output `api_gateway_stage_url`)

