"""
STEP 10 — Resilience & Fallback Handler

Guarantees that the agent always returns a user-friendly response, even
when previous steps failed or permissions are missing.
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
    if ctx.final_response_text:
        # We already have a response; nothing to do.
        return ctx, {}

    # Map simple categories to friendly fallbacks.
    if ctx.final_status == "error":
        message = (
            "Ocurrió un error al procesar tu solicitud. "
            f"Por favor intentá nuevamente. trace_id={ctx.trace_id}"
        )
    elif ctx.fallback_message:
        message = ctx.fallback_message
    elif ctx.intent == "unknown":
        message = (
            "No estoy seguro de entender lo que necesitás. "
            "Podés preguntarme sobre el estado del sprint, bloqueadores o métricas del equipo."
        )
    else:
        message = "No pude completar la acción, pero el sistema registró la solicitud para análisis."

    new_ctx = ctx.with_updates(
        final_response_text=message,
        final_status=ctx.final_status or "fallback",
    )
    return new_ctx, {}



