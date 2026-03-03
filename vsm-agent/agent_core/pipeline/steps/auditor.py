"""
STEP 7 — Audit Log

Persists a high-level audit entry of the invocation:
- prompt_input
- prompt_output
- skill executed / mcp target
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Tuple

from agent_core.config.settings import AgentCoreSettings
from agent_core.models.agent_context import AgentContext
from agent_core.repositories.dynamo_base import put_item


@dataclass
class AuditRecord:
    tenant_id: str
    user_id: str
    session_id: str
    trace_id: str
    prompt_input: str
    prompt_output: str
    skill_executed: str | None
    mcp_target: str | None
    status: str
    duration_ms: int
    tokens_input: int
    tokens_output: int

    def to_item(self) -> Dict[str, Any]:
        data = asdict(self)
        now = datetime.utcnow()
        date_str = now.strftime("%Y-%m-%d")
        ts = now.isoformat() + "Z"
        return {
            "PK": {"S": f"TENANT#{self.tenant_id}|DATE#{date_str}"},
            "SK": {"S": f"AUDIT#{ts}|{self.trace_id}"},
            **{
                "user_id": {"S": self.user_id},
                "session_id": {"S": self.session_id},
                "prompt_input": {"S": self.prompt_input[:2000]},
                "prompt_output": {"S": self.prompt_output[:2000]},
                "skill_executed": {"S": self.skill_executed or ""},
                "mcp_target": {"S": (self.mcp_target or "")},
                "status": {"S": self.status},
                "duration_ms": {"N": str(self.duration_ms)},
                "tokens_input": {"N": str(self.tokens_input)},
                "tokens_output": {"N": str(self.tokens_output)},
            },
        }


def run(
    ctx: AgentContext,
    *,
    settings: AgentCoreSettings,
    extra: Dict[str, Any],
) -> Tuple[AgentContext, Dict[str, Any]]:
    # We don't have precise duration here; keep 0 for now, can be
    # enriched once pipeline is instrumented end-to-end.
    record = AuditRecord(
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id or "anonymous",
        session_id=ctx.session_id,
        trace_id=ctx.trace_id,
        prompt_input=ctx.prompt,
        prompt_output=ctx.final_response_text or "",
        skill_executed=ctx.resolved_skill_id,
        mcp_target=ctx.resolved_mcp_target,
        status=ctx.final_status,
        duration_ms=0,
        tokens_input=ctx.tokens_input,
        tokens_output=ctx.tokens_output,
    )

    table_name = settings.dynamo.table_name("audit_log")
    put_item(table_name, record.to_item())

    return ctx, {}



