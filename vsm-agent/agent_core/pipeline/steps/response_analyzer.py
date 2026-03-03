"""
STEP 6 — Response Analysis (LLM)

Takes the raw MCP output and turns it into a user-friendly natural
language response.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from agent_core.config.settings import AgentCoreSettings
from agent_core.models.agent_context import AgentContext


def run(
    ctx: AgentContext,
    *,
    settings: AgentCoreSettings,
    extra: Dict[str, Any],
) -> Tuple[AgentContext, Dict[str, Any]]:
    if ctx.final_status == "error":
        return ctx, {}

    if ctx.mcp_raw_result is None:
        # Nothing to summarize yet
        return ctx, {}

    # Very lightweight, rule-based "analysis" for now.
    if ctx.resolved_mcp_target == "jira":
        issues = ctx.mcp_raw_result.get("issues", [])
        count = len(issues)
        response = f"Encontré {count} issue(s) en Jira relacionados con tu consulta."
    elif ctx.resolved_mcp_target == "confluence":
        page = ctx.mcp_raw_result.get("page", {})
        title = page.get("title", "una página")
        response = f"Creé {title} en Confluence para registrar la información."
    else:
        response = "Procesé tu solicitud pero no hay más detalles que mostrar aún."

    new_ctx = ctx.with_updates(final_response_text=response)
    meta = {"model_used": settings.llm.analyzer_model, "tokens_used": 0}
    return new_ctx, meta




