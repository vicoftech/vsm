"""
Strands-style pipeline orchestrator for the Agent Core.

This module wires the 10 conceptual steps described in `feature_1.md`
into a simple, sequential Python pipeline.

Each step is implemented in `agent_core.pipeline.steps.*` and receives /
returns an `AgentContext` instance.
"""

from __future__ import annotations

from time import perf_counter
import logging
from typing import Any, Dict, Optional

from agent_core.config.settings import load_settings
from agent_core.models.agent_context import AgentContext, new_agent_context
from agent_core.models.trace import StepTrace
from agent_core.repositories.dynamo_base import put_item

from agent_core.pipeline.steps import (
    auth_resolver,
    memory_loader,
    prompt_interpreter,
    skill_router,
    mcp_executor,
    response_analyzer,
    auditor,
    tracer,
    token_tracker,
    resilience_handler,
)


logger = logging.getLogger(__name__)

def _run_step(
    step_number: int,
    step_name: str,
    ctx: AgentContext,
    func,
    settings,
    extra: Optional[Dict[str, Any]] = None,
) -> AgentContext:
    """
    Execute a single pipeline step and record a basic trace.
    """
    start = perf_counter()
    status = "success"
    model_used: Optional[str] = None
    tokens_used = 0

    try:
        new_ctx, meta = func(ctx, settings=settings, extra=extra or {})
        model_used = meta.get("model_used")
        tokens_used = meta.get("tokens_used", 0)
    except Exception as exc:  # pragma: no cover - defensive
        status = "error"
        # Log completo del error para debugging (incluye traceback).
        logger.error(
            "Agent pipeline step %s (#{}) failed for tenant %s: %s".format(
                step_number
            ),
            step_name,
            ctx.tenant_id,
            exc,
            exc_info=True,
        )
        new_ctx = ctx.with_updates(
            final_status="error",
            final_response_text="Ocurrió un error inesperado al procesar tu solicitud.",
            metadata={**ctx.metadata, f"{step_name}_error": str(exc)},
        )

    duration_ms = int((perf_counter() - start) * 1000)

    if settings.pipeline.trace_enabled:
        trace = StepTrace(
            trace_id=new_ctx.trace_id,
            step_number=step_number,
            step_name=step_name,
            status=status,
            input_summary=f"tenant={ctx.tenant_id}",
            output_summary=f"status={new_ctx.final_status}",
            duration_ms=duration_ms,
            model_used=model_used,
            tokens_used=tokens_used or None,
        )
        table_name = settings.dynamo.table_name("pipeline_traces")
        put_item(table_name, trace.to_item())

    return new_ctx


def run_agent_pipeline(
    tenant_id: str,
    prompt: str,
    *,
    session_id: Optional[str] = None,
    raw_headers: Optional[Dict[str, str]] = None,
) -> AgentContext:
    """
    High-level entry point for the Agent Core pipeline.

    It creates an initial `AgentContext`, runs all 10 steps, and returns
    the enriched context with the final response.
    """
    settings = load_settings()
    ctx = new_agent_context(tenant_id=tenant_id, prompt=prompt, session_id=session_id)

    # STEP 1 — Auth & Permission Resolution
    ctx = _run_step(
        1,
        "auth_resolver",
        ctx,
        auth_resolver.run,
        settings,
        extra={"headers": raw_headers or {}},
    )

    # STEP 2 — Memory Load
    ctx = _run_step(2, "memory_loader", ctx, memory_loader.run, settings)

    # STEP 3 — Prompt Interpretation (LLM light)
    ctx = _run_step(3, "prompt_interpreter", ctx, prompt_interpreter.run, settings)

    # STEP 4 — Skill & Rule Routing
    ctx = _run_step(4, "skill_router", ctx, skill_router.run, settings)

    # STEP 5 — MCP Execution
    ctx = _run_step(5, "mcp_executor", ctx, mcp_executor.run, settings)

    # STEP 6 — Response Analysis (LLM)
    ctx = _run_step(6, "response_analyzer", ctx, response_analyzer.run, settings)

    # STEP 7 — Audit Log
    ctx = _run_step(7, "auditor", ctx, auditor.run, settings)

    # STEP 8 — Pipeline Traces (already handled inline, but step kept for parity)
    ctx = _run_step(8, "tracer", ctx, tracer.run, settings)

    # STEP 9 — Token Consumption Tracking
    ctx = _run_step(9, "token_tracker", ctx, token_tracker.run, settings)

    # STEP 10 — Resilience & Fallback Handler
    ctx = _run_step(10, "resilience_handler", ctx, resilience_handler.run, settings)

    return ctx




