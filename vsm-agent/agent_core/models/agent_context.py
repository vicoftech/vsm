"""
Agent execution context model.

This object is passed (immutably) through all pipeline steps, each step
returning a new enriched instance.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass(frozen=True)
class MemoryLayer:
    """Represents loaded memory for a given scope."""

    items: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class AgentContext:
    """
    Central execution context for the Agent Core pipeline.

    It purposely avoids tight coupling to HTTP/Lambda so it can be reused
    from different entry points (API Gateway, Bedrock Agents, etc.).
    """

    # Correlation / tracing
    trace_id: str
    session_id: str

    # Tenant / user
    tenant_id: str
    user_id: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    email: Optional[str] = None

    # Raw user prompt
    prompt: str = ""

    # Memory layers
    short_term_memory: MemoryLayer = field(default_factory=MemoryLayer)
    mid_term_memory: MemoryLayer = field(default_factory=MemoryLayer)
    long_term_memory: MemoryLayer = field(default_factory=MemoryLayer)

    # Permissions / skills
    allowed_skills: List[str] = field(default_factory=list)

    # Skill routing outcome
    resolved_skill_id: Optional[str] = None
    resolved_mcp_target: Optional[str] = None
    resolved_parameters: Dict[str, Any] = field(default_factory=dict)
    intent: Optional[str] = None
    confidence: float = 0.0
    fallback_message: Optional[str] = None

    # MCP execution
    mcp_raw_result: Optional[Dict[str, Any]] = None
    mcp_status_code: Optional[int] = None

    # Final response
    final_response_text: Optional[str] = None
    final_status: str = "success"  # success | fallback | error

    # Token usage
    tokens_input: int = 0
    tokens_output: int = 0

    # Arbitrary per-step metadata (for traces, debugging, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **kwargs: Any) -> "AgentContext":
        """
        Return a new AgentContext with updated fields.

        This is the preferred way to evolve context in each pipeline step.
        """
        return replace(self, **kwargs)


def new_agent_context(
    tenant_id: str,
    prompt: str,
    session_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> AgentContext:
    """
    Helper to construct a fresh AgentContext with generated IDs.
    """
    return AgentContext(
        trace_id=trace_id or str(uuid4()),
        session_id=session_id or str(uuid4()),
        tenant_id=tenant_id,
        prompt=prompt,
    )



