"""
Memory models for Agent Core.

We keep this intentionally simple and focused on what the pipeline needs:
- role (user/assistant/system)
- content (text)
- timestamp (ISO string)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class MemoryMessage:
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: str

    @classmethod
    def from_dynamo(cls, item: Dict[str, Any]) -> "MemoryMessage":
        """
        Build from low-level DynamoDB attribute map.
        """
        def _s(name: str, default: str = "") -> str:
            return item.get(name, {}).get("S", default)

        return cls(
            role=_s("role"),
            content=_s("content"),
            timestamp=_s("timestamp"),
        )



