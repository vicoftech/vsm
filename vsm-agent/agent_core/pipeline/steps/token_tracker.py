"""
STEP 9 — Token Consumption Tracking

In this initial implementation we don't have real token counts yet, but
we keep the shape and a DynamoDB sink ready so it can be wired to
Bedrock usage later.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Tuple

from agent_core.config.settings import AgentCoreSettings
from agent_core.models.agent_context import AgentContext
from agent_core.repositories.dynamo_base import put_item


def run(
    ctx: AgentContext,
    *,
    settings: AgentCoreSettings,
    extra: Dict[str, Any],
) -> Tuple[AgentContext, Dict[str, Any]]:
    if not settings.pipeline.token_tracking_enabled:
        return ctx, {}

    now = datetime.utcnow()
    month_str = now.strftime("%Y-%m")
    date_str = now.strftime("%Y-%m-%d")

    item = {
        "PK": {"S": f"TENANT#{ctx.tenant_id}|MONTH#{month_str}"},
        "SK": {"S": f"USER#{ctx.user_id or 'anonymous'}|DATE#{date_str}"},
        "tokens_input": {"N": str(ctx.tokens_input)},
        "tokens_output": {"N": str(ctx.tokens_output)},
        "total_tokens": {"N": str(ctx.tokens_input + ctx.tokens_output)},
        "invocations": {"N": "1"},
    }

    table_name = settings.dynamo.table_name("token_consumption")
    put_item(table_name, item)

    return ctx, {}



