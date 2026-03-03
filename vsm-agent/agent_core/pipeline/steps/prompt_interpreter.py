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
from agent_core.llm.interpreter import interpret_prompt, LLMInterpreterError


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
    # Listar historias / backlog / épicas del proyecto
    if any(
        w in msg
        for w in [
            "historias epicas",
            "historias épicas",
            "épicas",
            "epicas",
            "epics",
            "historias",
            "backlog",
            "lista las historias",
            "listame las historias",
            "listame todas las historias",
        ]
    ):
        return {
            "intent": "list_backlog",
            "skill_id": "jira_list_backlog",
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
    """
    STEP 3: intentar usar Bedrock (Haiku/Titan) para interpretar el prompt.

    NOTA: fallback heurístico deshabilitado temporalmente para forzar
    visibilidad de errores del LLM en CloudWatch y trazas.
    """
    # Intento con LLM (sin fallback heurístico).
    #
    # Cualquier fallo de `interpret_prompt` (incluyendo problemas de permisos,
    # modelo inexistente o JSON inválido) se propagará como LLMInterpreterError
    # hacia el orquestador, que marcará el pipeline en estado de error.
    llm_result = interpret_prompt(ctx, settings=settings)

    # Usar SIEMPRE el resultado del LLM, incluso si la confianza es baja
    # o el intent es "unknown", para poder inspeccionar el comportamiento
    # real del modelo Titan/Claude.
    confidence = llm_result.confidence
    fallback_message = llm_result.fallback_message

    new_ctx = ctx.with_updates(
        intent=llm_result.intent,
        resolved_skill_id=llm_result.skill_id,
        resolved_mcp_target=llm_result.mcp_target,
        resolved_parameters=llm_result.parameters or {},
        confidence=confidence,
        fallback_message=fallback_message,
    )

    meta = {
        "model_used": settings.llm.interpreter_model,
        "tokens_used": 0,
    }
    return new_ctx, meta



