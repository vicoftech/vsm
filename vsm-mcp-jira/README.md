# VSM MCP Jira Lambda

Lambda function que expone las herramientas del MCP Jira Extended como API HTTP.

## Estructura

```
vsm-mcp-jira/
├── src/
│   ├── handler.py          # Lambda handler principal
│   ├── mcp_server.py       # Servidor MCP adaptado para Lambda
│   ├── tools/
│   │   ├── issues.py       # Herramientas de issues
│   │   ├── filters.py      # Herramientas de filtros
│   │   ├── boards.py       # Herramientas de tableros
│   │   ├── dashboards.py   # Herramientas de dashboards
│   │   ├── projects.py     # Herramientas de proyectos
│   │   └── sprints.py      # Herramientas de sprints
│   └── jira_client.py      # Cliente Jira API
├── tests/
│   ├── test_issues.py
│   ├── test_filters.py
│   ├── test_boards.py
│   ├── test_dashboards.py
│   ├── test_projects.py
│   └── test_sprints.py
├── infra/
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── requirements.txt
└── .env.example
```

## Herramientas Expuestas

### Issues
- `get_issue` - Obtener issue por key
- `search_issues` - Búsqueda JQL
- `create_epic`, `create_story`, `create_task`, `create_bug`, `create_subtask`
- `update_issue` - Actualizar issue
- `transition_issue` - Mover issue
- `assign_issue` - Asignar issue
- `add_comment` - Agregar comentario
- `add_worklog` - Agregar worklog
- `set_story_points` - Establecer story points
- Operaciones bulk

### Filtros
- `create_filter` - Crear filtro JQL
- `get_filter` - Obtener filtro
- `search_filters` - Buscar filtros
- `update_filter` - Actualizar filtro
- `delete_filter` - Eliminar filtro

### Tableros
- `get_boards` - Listar boards
- `create_board` - Crear board (Scrum/Kanban)

### Dashboards
- `create_dashboard` - Crear dashboard
- `get_dashboard` - Obtener dashboard
- `get_dashboards` - Listar dashboards
- `update_dashboard` - Actualizar dashboard
- `delete_dashboard` - Eliminar dashboard

### Proyectos
- `get_projects` - Listar proyectos
- `get_project` - Obtener proyecto
- `create_project` - Crear proyecto con template
- `update_project` - Actualizar proyecto
- `add_user_to_project` - Agregar usuario al proyecto

### Sprints
- `get_sprints` - Obtener sprints del board
- `create_sprint` - Crear sprint
- `add_to_sprint` - Agregar issues al sprint
- `start_sprint` - Iniciar sprint
- `complete_sprint` - Cerrar sprint

## Configuración

1. Copiar `.env.example` a `.env` y configurar credenciales
2. Instalar dependencias: `pip install -r requirements.txt`
3. Ejecutar tests: `pytest tests/`
4. Deploy con Terraform: `cd infra && terraform apply`

## Variables de Entorno

- `JIRA_BASE_URL` - URL base de Jira (ej: https://agentvsm.atlassian.net)
- `JIRA_EMAIL` - Email del usuario de Jira
- `JIRA_API_TOKEN` - API token de Jira


