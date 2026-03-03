"""
STEP 8 — Pipeline Traces

Full per-step traces are already recorded in `pipeline.orchestrator`
using `StepTrace`. This step is kept as a no-op to preserve the
conceptual 10-step structure and can be extended later for cross-system
correlation (e.g., X-Ray segments).
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
    # No-op for now.
    return ctx, {}



