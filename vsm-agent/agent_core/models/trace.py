"""
Tracing models for the Agent Core pipeline.

These traces are persisted to DynamoDB (pipeline_traces table) and can be
also sent to X-Ray or other observability backends.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict


@dataclass
class StepTrace:
    trace_id: str
    step_number: int
    step_name: str
    status: str  # success | skipped | error
    input_summary: str
    output_summary: str
    duration_ms: int
    model_used: str | None = None
    tokens_used: int | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )

    def to_item(self) -> Dict[str, Any]:
        """
        Convert to a DynamoDB item for the low-level client.
        """
        # Truncate summaries to keep items small and safe
        input_summary = self.input_summary[:500]
        output_summary = self.output_summary[:500]

        item: Dict[str, Any] = {
            "PK": {"S": f"TRACE#{self.trace_id}"},
            "SK": {"S": f"STEP#{self.step_number}"},
            "step_name": {"S": self.step_name},
            "status": {"S": self.status},
            "input_summary": {"S": input_summary},
            "output_summary": {"S": output_summary},
            "duration_ms": {"N": str(self.duration_ms)},
            "timestamp": {"S": self.timestamp},
        }

        if self.model_used is not None:
            item["model_used"] = {"S": self.model_used}
        if self.tokens_used is not None:
            item["tokens_used"] = {"N": str(self.tokens_used)}

        return item



