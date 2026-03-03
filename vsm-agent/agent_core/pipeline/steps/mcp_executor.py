"""
STEP 5 — MCP Execution

This step bridges the new Agent Core pipeline with the existing MCP
services (`services.jira_mcp` and `services.confluence_mcp`).
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from agent_core.config.settings import AgentCoreSettings
from agent_core.models.agent_context import AgentContext

# Reuse existing MCP mock services for now
from services.jira_mcp import JiraMCPService
from services.confluence_mcp import ConfluenceMCPService


def run(
    ctx: AgentContext,
    *,
    settings: AgentCoreSettings,
    extra: Dict[str, Any],
) -> Tuple[AgentContext, Dict[str, Any]]:
    if ctx.final_status == "error":
        return ctx, {}

    if not ctx.resolved_mcp_target:
        # Nothing to execute (e.g., greeting/help intents in future)
        return ctx, {}

    if ctx.resolved_mcp_target == "jira":
        jira = JiraMCPService(ctx.tenant_id)
        # For now we call a very simple operation: search_issues
        issues, _latency = jira.search_issues(
            project_key=ctx.resolved_parameters.get("project", "VSM")
        )
        result = {"issues": issues}
    elif ctx.resolved_mcp_target == "confluence":
        conf = ConfluenceMCPService(ctx.tenant_id)
        # Minimal stub: create a simple page instead of a full decision log
        page, _latency = conf.create_page(
            space_key=ctx.resolved_parameters.get("spaceKey", "VSM"),
            title="Agent Core Test Page",
            content="<p>Agent Core test content</p>",
        )
        result = {"page": page}
    else:
        result = {}

    new_ctx = ctx.with_updates(
        mcp_raw_result=result,
        mcp_status_code=200,
    )

    return new_ctx, {}



