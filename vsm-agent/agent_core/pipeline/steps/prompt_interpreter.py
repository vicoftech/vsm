"""
STEP 3 — Prompt Interpretation (LLM light)

To keep the Lambda free of heavy external dependencies for now, this
step reuses a very simple intent detection heuristic similar to the
existing `OrchestratorService._detect_intent`, but returns a generic
JSON structure compatible with `feature_1.md`.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from agent_core.config.settings import AgentCoreSettings
from agent_core.models.agent_context import AgentContext


def _simple_intent_detection(message: str) -> Dict[str, Any]:
    msg = message.lower()

    # Crear / abrir tickets en Jira (español e inglés)
    if any(
        w in msg
        for w in [
            "creame un ticket",
            "créame un ticket",
            "crear un ticket",
            "crear ticket",
            "crea un ticket",
            "create ticket",
            "nuevo ticket",
            "nuevo issue",
            "create issue",
        ]
    ):
        return {
            "intent": "create_ticket",
            "skill_id": "jira_create_issue",
            "mcp_target": "jira",
        }
    if any(w in msg for w in ["buscar", "search confluence", "documentación"]):
        return {
            "intent": "search_confluence",
            "skill_id": "confluence_search",
            "mcp_target": "confluence",
        }

    return {
        "intent": "unknown",
        "skill_id": None,
        "mcp_target": None,
    }


def run(
    ctx: AgentContext,
    *,
    settings: AgentCoreSettings,
    extra: Dict[str, Any],
) -> Tuple[AgentContext, Dict[str, Any]]:
    parsed = _simple_intent_detection(ctx.prompt)
    confidence = 0.92 if parsed["intent"] != "unknown" else 0.4

    fallback_message = (
        "No pude determinar la acción. ¿Podés especificar más?"
        if confidence < settings.pipeline.confidence_threshold
        else None
    )

    new_ctx = ctx.with_updates(
        intent=parsed["intent"],
        resolved_skill_id=parsed["skill_id"],
        resolved_mcp_target=parsed["mcp_target"],
        resolved_parameters={},
        confidence=confidence,
        fallback_message=fallback_message,
    )

    # In a future version this step will call Bedrock using settings.llm.interpreter_model
    meta = {"model_used": settings.llm.interpreter_model, "tokens_used": 0}
    return new_ctx, meta



