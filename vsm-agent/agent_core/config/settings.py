"""
Agent Core settings.

Centralizes environment-based configuration for:
- AWS / DynamoDB
- LLM provider (Bedrock)
- Pipeline behavior (thresholds, feature flags)

All values have sensible defaults for local development and can be
overridden via environment variables in Lambda.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name)
    if value is None:
        if default is None:
            raise RuntimeError(f"Missing required environment variable: {name}")
        return default
    return value


@dataclass(frozen=True)
class DynamoSettings:
    region: str
    table_prefix: str

    @classmethod
    def load(cls) -> "DynamoSettings":
        return cls(
            region=_get_env("AWS_REGION", "us-east-1"),
            table_prefix=_get_env("DYNAMODB_TABLE_PREFIX", "agent-core"),
        )

    def table_name(self, logical_name: str) -> str:
        """
        Build physical DynamoDB table name from logical name.

        Example: prefix 'agent-core' + logical 'skill_permissions'
        → 'agent-core-skill_permissions'
        """
        return f"{self.table_prefix}-{logical_name}"


@dataclass(frozen=True)
class LLMSettings:
    interpreter_model: str
    analyzer_model: str
    bedrock_region: str

    @classmethod
    def load(cls) -> "LLMSettings":
        return cls(
            # Por defecto usamos un modelo Titan de texto, no Claude,
            # para evitar restricciones comerciales específicas.
            interpreter_model=_get_env(
                "INTERPRETER_MODEL", "amazon.titan-text-lite-v1"
            ),
            analyzer_model=_get_env(
                "ANALYZER_MODEL", "amazon.titan-text-lite-v1"
            ),
            bedrock_region=_get_env("BEDROCK_REGION", "us-east-1"),
        )


@dataclass(frozen=True)
class PipelineSettings:
    short_term_ttl_hours: int
    mid_term_ttl_hours: int
    trace_enabled: bool
    token_tracking_enabled: bool
    resilience_max_retries: int
    confidence_threshold: float

    @classmethod
    def load(cls) -> "PipelineSettings":
        return cls(
            short_term_ttl_hours=int(_get_env("MEMORY_SHORT_TERM_TTL_HOURS", "1")),
            mid_term_ttl_hours=int(_get_env("MEMORY_MID_TERM_TTL_HOURS", "48")),
            trace_enabled=_get_env("PIPELINE_TRACE_ENABLED", "true").lower() == "true",
            token_tracking_enabled=_get_env("TOKEN_TRACKING_ENABLED", "true").lower()
            == "true",
            resilience_max_retries=int(_get_env("RESILIENCE_MAX_RETRIES", "3")),
            confidence_threshold=float(_get_env("CONFIDENCE_THRESHOLD", "0.7")),
        )


@dataclass(frozen=True)
class MCPSettings:
    jira_url: str
    confluence_url: str
    jira_token_secret_arn: str
    confluence_token_secret_arn: str

    @classmethod
    def load(cls) -> "MCPSettings":
        return cls(
            jira_url=_get_env("MCP_JIRA_URL", "https://jira.example.com"),
            confluence_url=_get_env(
                "MCP_CONFLUENCE_URL", "https://confluence.example.com"
            ),
            jira_token_secret_arn=_get_env(
                "MCP_JIRA_TOKEN_SECRET", "arn:aws:secretsmanager:dummy-jira"
            ),
            confluence_token_secret_arn=_get_env(
                "MCP_CONFLUENCE_TOKEN_SECRET",
                "arn:aws:secretsmanager:dummy-confluence",
            ),
        )


@dataclass(frozen=True)
class AgentCoreSettings:
    dynamo: DynamoSettings
    llm: LLMSettings
    pipeline: PipelineSettings
    mcps: MCPSettings

    @classmethod
    def load(cls) -> "AgentCoreSettings":
        return cls(
            dynamo=DynamoSettings.load(),
            llm=LLMSettings.load(),
            pipeline=PipelineSettings.load(),
            mcps=MCPSettings.load(),
        )


def load_settings() -> AgentCoreSettings:
    """
    Convenience loader used by the pipeline/steps.
    """
    return AgentCoreSettings.load()



