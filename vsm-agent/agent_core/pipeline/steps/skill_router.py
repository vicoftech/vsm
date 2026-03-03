"""
STEP 4 — Skill & Rule Routing

Validates that:
- The skill resolved in STEP 3 exists and is enabled (future `skills_catalog`).
- The user has permission to execute the skill (via `skill_permissions`).

In this first version we only check permissions if a skill was found.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from agent_core.config.settings import AgentCoreSettings
from agent_core.models.agent_context import AgentContext
from agent_core.repositories.permissions_repo import PermissionsRepository
from agent_core.repositories.skills_repo import SkillsRepository


def _apply_rules(ctx: AgentContext, rules: list[str]) -> AgentContext:
    """
    Apply simple in-code rules based on rule IDs from DynamoDB.

    This keeps the behaviour declarative desde la tabla `skills_catalog`
    sin necesidad de una tabla extra de reglas en esta primera versión.
    """
    # Example: require a project parameter for Jira ticket creation
    if "require_project_param" in rules:
        project = ctx.resolved_parameters.get("project")
        if not project:
            return ctx.with_updates(
                final_status="fallback",
                fallback_message=(
                    "Necesito saber en qué proyecto de Jira crear el ticket. "
                    "Por favor indicá el código del proyecto (por ejemplo: VSM)."
                ),
            )

    # Placeholder for other rules like rate limiting, parameter transforms, etc.
    return ctx


def run(
    ctx: AgentContext,
    *,
    settings: AgentCoreSettings,
    extra: Dict[str, Any],
) -> Tuple[AgentContext, Dict[str, Any]]:
    # If no skill was resolved, we leave the context as fallback candidate
    if not ctx.resolved_skill_id:
        return ctx, {}

    perm_repo = PermissionsRepository(settings=settings)
    perm = perm_repo.get_permission(
        ctx.tenant_id, ctx.user_id or "anonymous", ctx.resolved_skill_id
    )

    if not perm or not perm.allowed:
        # Permission denied — mark context as fallback/error but let
        # resilience handler build the final user-facing message.
        new_ctx = ctx.with_updates(
            final_status="fallback",
            fallback_message="No tenés permisos para ejecutar esta acción.",
        )
        return new_ctx, {}

    # Load skill definition from catalog (best-effort)
    skills_repo = SkillsRepository(settings=settings)
    skill = skills_repo.get_skill(ctx.resolved_skill_id, version="v1")

    if not skill or not skill.enabled:
        new_ctx = ctx.with_updates(
            final_status="fallback",
            fallback_message=(
                "La acción que pediste (skill del agente) no está disponible en este entorno."
            ),
        )
        return new_ctx, {}

    new_ctx = ctx.with_updates(
        resolved_mcp_target=skill.mcp_target or perm.mcp_target,
        allowed_skills=[ctx.resolved_skill_id],
    )

    # Apply simple rule set from skills_catalog
    if skill.rules:
        new_ctx = _apply_rules(new_ctx, skill.rules)

    return new_ctx, {}



