"""
STEP 1 — Auth & Permission Resolution

In this first implementation we keep it simple:
- Tenant is passed explicitly from the Lambda handler.
- User information is derived from headers when available.
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
    headers: Dict[str, str] = {
        k.lower(): str(v) for k, v in (extra.get("headers") or {}).items()
    }

    user_id = headers.get("x-user-id") or headers.get("cognito:username") or "anonymous"
    email = headers.get("x-user-email") or headers.get("email")
    roles_header = headers.get("x-roles") or ""
    roles = [r.strip() for r in roles_header.split(",") if r.strip()]

    new_ctx = ctx.with_updates(user_id=user_id, email=email, roles=roles)

    # For now we don't hit DynamoDB here; that will be done in the skill
    # routing step once we know which skill we want to execute.

    return new_ctx, {}




