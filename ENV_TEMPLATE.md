# Template de Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```bash
# =============================================================================
# VSM MCPs - Environment Variables
# =============================================================================

# =============================================================================
# Jira MCP Configuration
# =============================================================================
JIRA_BASE_URL=https://agentvsm.atlassian.net
JIRA_EMAIL=vicoftech@gmail.com
JIRA_API_TOKEN=ATATT3xFfGF02VQWriq_ZaSSmYq1S-iHIfO_FvLo09ZjkHsUMUtHRxHmjJivBFusItLm5fwCXdD09RaHUcRcOFVxXVddz1m60tIQehgdZQ-PlIbcfPXxKovYABNZYCTITpuqVVyTjhAtPqNRx2L42Q-BGOuN9qZM43bbZSW2XOfobH_giBy_W2U=41C151D1

# =============================================================================
# Confluence MCP Configuration
# =============================================================================
CONFLUENCE_DOMAIN=agentvsm.atlassian.net
CONFLUENCE_EMAIL=vicoftech@gmail.com
CONFLUENCE_API_TOKEN=ATATT3xFfGF02VQWriq_ZaSSmYq1S-iHIfO_FvLo09ZjkHsUMUtHRxHmjJivBFusItLm5fwCXdD09RaHUcRcOFVxXVddz1m60tIQehgdZQ-PlIbcfPXxKovYABNZYCTITpuqVVyTjhAtPqNRx2L42Q-BGOuN9qZM43bbZSW2XOfobH_giBy_W2U=41C151D1

# =============================================================================
# AWS Configuration (for Lambda deployment)
# =============================================================================
AWS_REGION=us-east-1
AWS_PROFILE=asap_dev

# =============================================================================
# Environment
# =============================================================================
ENVIRONMENT=dev
LOG_LEVEL=INFO
```

**⚠️ IMPORTANTE:** 
- El archivo `.env` está en `.gitignore` y NO debe versionarse
- Usa este template para crear tu archivo `.env` local
- Para producción, usa AWS Secrets Manager o Parameter Store


