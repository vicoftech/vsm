"""
Orchestrator Service.
Coordinates MCP calls and implements business logic for the VSM Agent.
Designed for future Bedrock Agent Action Group compatibility.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from models.schemas import (
    # Tracing
    OrchestratorMetadata,
    MCPInvocationTrace,
    MCPType,
    # Request models
    SprintPlanRequest,
    SprintReviewRequest,
    BacklogRefinementRequest,
    StandupAnalysisRequest,
    DecisionLogRequest,
    AgentQueryRequest,
    AgentInvokeRequest,
    # Response data models
    SprintPlanData,
    SprintReviewData,
    SprintStatusData,
    BacklogRefinementData,
    StandupAnalysisData,
    DecisionLogData,
    AgentQueryData,
    AgentInvokeData,
    # Supporting models
    SprintIssue,
    ExcludedIssue,
    SprintMetrics,
    SprintProgress,
    BurndownStatus,
    BurndownTrend,
    SprintProjection,
    SprintState,
    BlockerIssue,
    RefinedIssue,
    DorViolation,
    IssueDependency,
    TeamMemberStatus,
    PotentialBlocker,
    WipViolation,
    StaleIssue,
    DataSource,
    QueryType,
    AgentIntent,
    MCPCallSummary,
    AgentAction,
    # Utilities
    generate_trace_id,
    current_iso_timestamp,
)

from services.jira_mcp import JiraMCPService
from services.confluence_mcp import ConfluenceMCPService


class OrchestratorService:
    """
    Main orchestrator service for the VSM Agent.
    
    Coordinates calls to:
    - Jira MCP: Project management, sprints, issues
    - Confluence MCP: Documentation, reports
    
    Implements Scrum ceremonies and workflows:
    - Sprint Planning
    - Sprint Review
    - Backlog Refinement
    - Daily Standup Analysis
    - Decision Logging
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.jira_mcp = JiraMCPService(tenant_id)
        self.confluence_mcp = ConfluenceMCPService(tenant_id)

    def _get_all_traces(self) -> List[MCPInvocationTrace]:
        """Collect all MCP traces from both services."""
        traces = []
        traces.extend(self.jira_mcp.get_traces())
        traces.extend(self.confluence_mcp.get_traces())
        return traces

    def _calculate_total_latency(self, traces: List[MCPInvocationTrace]) -> int:
        """Calculate total latency from traces."""
        return sum(t.duration_ms for t in traces)

    def _build_metadata(self, traces: List[MCPInvocationTrace]) -> OrchestratorMetadata:
        """Build orchestrator metadata from traces."""
        return OrchestratorMetadata(
            mcp_calls=traces,
            total_latency_ms=self._calculate_total_latency(traces),
            tenant_id=self.tenant_id,
            simulated_confidence_score=round(random.uniform(0.85, 0.98), 2)
        )

    def _clear_traces(self) -> None:
        """Clear all MCP traces."""
        self.jira_mcp.clear_traces()
        self.confluence_mcp.clear_traces()

    # === Sprint Planning ===

    def plan_sprint(self, request: SprintPlanRequest) -> tuple[SprintPlanData, OrchestratorMetadata]:
        """
        Orchestrate sprint planning.
        
        Steps:
        1. Search backlog for candidate issues
        2. Validate DoR for each issue
        3. Create sprint in Jira
        4. Add qualified issues to sprint
        5. Start sprint
        6. Document in Confluence (optional)
        """
        self._clear_traces()

        # Step 1: Get candidate issues from backlog
        issues_data, _ = self.jira_mcp.search_issues(
            request.project_key,
            max_results=50
        )

        # Step 2: Filter and validate issues
        issues_included: List[SprintIssue] = []
        issues_excluded: List[ExcludedIssue] = []
        total_points = 0

        candidate_keys = set(request.candidate_issues) if request.candidate_issues else None

        for issue in issues_data:
            if issue.get("status") != "To Do":
                continue

            key = issue["key"]
            if candidate_keys and key not in candidate_keys:
                continue

            # Check DoR
            has_ac = issue.get("hasAcceptanceCriteria", False)
            has_points = issue.get("storyPoints") is not None

            if has_ac and has_points:
                sp = issue.get("storyPoints", 0)
                
                # Check capacity
                if request.team_capacity and (total_points + sp) > request.team_capacity:
                    issues_excluded.append(ExcludedIssue(
                        issue_key=key,
                        reason="Exceeds team capacity"
                    ))
                    continue

                issues_included.append(SprintIssue(
                    issue_key=key,
                    summary=issue["summary"],
                    story_points=sp,
                    dor_compliant=True
                ))
                total_points += sp
            else:
                reasons = []
                if not has_ac:
                    reasons.append("missing acceptance criteria")
                if not has_points:
                    reasons.append("missing story points")
                issues_excluded.append(ExcludedIssue(
                    issue_key=key,
                    reason=f"DoR not met: {', '.join(reasons)}"
                ))

        # Step 3: Create sprint
        sprint_result, _ = self.jira_mcp.create_sprint(
            board_id=request.board_id,
            name=request.sprint_name,
            start_date=request.start_date,
            end_date=request.end_date,
            goal=request.sprint_goal
        )
        sprint_id = sprint_result["id"]

        # Step 4: Add issues to sprint
        if issues_included:
            issue_keys = [i.issue_key for i in issues_included]
            self.jira_mcp.add_to_sprint(sprint_id, issue_keys)

        # Step 5: Start sprint
        self.jira_mcp.start_sprint(sprint_id)

        # Step 6: Document in Confluence
        confluence_url = None
        if request.document_in_confluence and request.confluence_space_key:
            page_result, _ = self.confluence_mcp.create_sprint_planning_page(
                space_key=request.confluence_space_key,
                sprint_name=request.sprint_name,
                sprint_goal=request.sprint_goal or "No goal specified",
                issues=[i.to_dict() for i in issues_included],
                project_key=request.project_key
            )
            confluence_url = page_result.get("url")

        # Build recommendations
        recommendations = []
        capacity_utilization = 0.0
        if request.team_capacity and request.team_capacity > 0:
            capacity_utilization = total_points / request.team_capacity
            if capacity_utilization < 0.7:
                recommendations.append(f"Consider adding more issues to utilize remaining {request.team_capacity - total_points} SP capacity")
        
        if issues_excluded:
            recommendations.append(f"{len(issues_excluded)} issues excluded - review DoR violations before next sprint")

        # Build response
        data = SprintPlanData(
            sprint_id=sprint_id,
            sprint_name=request.sprint_name,
            sprint_goal=request.sprint_goal,
            start_date=request.start_date,
            end_date=request.end_date,
            issues_included=issues_included,
            issues_excluded=issues_excluded,
            total_story_points=total_points,
            capacity_utilization=round(capacity_utilization, 2),
            confluence_page_url=confluence_url,
            recommendations=recommendations
        )

        metadata = self._build_metadata(self._get_all_traces())
        return data, metadata

    # === Sprint Review ===

    def review_sprint(self, request: SprintReviewRequest) -> tuple[SprintReviewData, OrchestratorMetadata]:
        """
        Orchestrate sprint review.
        
        Steps:
        1. Get sprint details
        2. Get all sprint issues
        3. Calculate metrics
        4. Generate Confluence report (optional)
        """
        self._clear_traces()

        # Step 1: Get sprint details
        sprint_data, _ = self.jira_mcp.get_sprint(request.sprint_id)
        sprint_name = sprint_data.get("name", f"Sprint {request.sprint_id}")

        # Step 2: Get sprint issues
        issues, _ = self.jira_mcp.get_sprint_issues(request.sprint_id)

        # Step 3: Categorize issues
        completed_issues: List[SprintIssue] = []
        incomplete_issues: List[SprintIssue] = []

        for issue in issues:
            sprint_issue = SprintIssue(
                issue_key=issue["key"],
                summary=issue["summary"],
                story_points=issue.get("storyPoints", 0) or 0,
                status=issue["status"]
            )
            if issue["status"] == "Done":
                completed_issues.append(sprint_issue)
            else:
                incomplete_issues.append(sprint_issue)

        # Step 4: Calculate metrics
        metrics = self.jira_mcp.get_sprint_metrics(request.sprint_id)

        # Step 5: Generate Confluence report
        confluence_url = None
        if request.generate_confluence_report and request.confluence_space_key:
            page_result, _ = self.confluence_mcp.create_sprint_review_page(
                space_key=request.confluence_space_key,
                sprint_name=sprint_name,
                metrics=metrics.to_dict(),
                completed=[i.to_dict() for i in completed_issues],
                incomplete=[i.to_dict() for i in incomplete_issues]
            )
            confluence_url = page_result.get("url")

        # Build recommendations
        recommendations = []
        if metrics.say_do_ratio < 0.8:
            recommendations.append("Say/Do ratio below 80% - consider more conservative capacity planning")
        if metrics.say_do_ratio > 0.95:
            recommendations.append("Excellent Say/Do ratio - team is highly predictable")
        if incomplete_issues:
            recommendations.append(f"{len(incomplete_issues)} issues carried over - review in next planning")

        data = SprintReviewData(
            sprint_id=request.sprint_id,
            sprint_name=sprint_name,
            metrics=metrics,
            completed_issues=completed_issues,
            incomplete_issues=incomplete_issues,
            confluence_report_url=confluence_url,
            recommendations=recommendations
        )

        metadata = self._build_metadata(self._get_all_traces())
        return data, metadata

    # === Sprint Status ===

    def get_sprint_status(self, sprint_id: str) -> tuple[SprintStatusData, OrchestratorMetadata]:
        """
        Get current sprint status with burndown and projections.
        """
        self._clear_traces()

        # Get sprint details
        sprint_data, _ = self.jira_mcp.get_sprint(sprint_id)
        
        # Get sprint issues
        issues, _ = self.jira_mcp.get_sprint_issues(sprint_id)

        # Calculate progress
        total_issues = len(issues)
        completed = [i for i in issues if i["status"] == "Done"]
        in_progress = [i for i in issues if i["status"] == "In Progress"]
        todo = [i for i in issues if i["status"] == "To Do"]

        total_points = sum(i.get("storyPoints", 0) or 0 for i in issues)
        completed_points = sum(i.get("storyPoints", 0) or 0 for i in completed)

        progress = SprintProgress(
            total_issues=total_issues,
            completed_issues=len(completed),
            in_progress_issues=len(in_progress),
            todo_issues=len(todo),
            total_story_points=total_points,
            completed_story_points=completed_points,
            percent_complete=round((completed_points / total_points * 100) if total_points > 0 else 0, 1)
        )

        # Calculate days remaining
        end_date = datetime.strptime(sprint_data.get("endDate", "2026-03-09"), "%Y-%m-%d")
        today = datetime.now()
        days_remaining = max(0, (end_date - today).days)

        # Calculate burndown
        remaining_points = total_points - completed_points
        
        # Calculate ideal burndown (linear)
        start_date = datetime.strptime(sprint_data.get("startDate", "2026-02-24"), "%Y-%m-%d")
        total_days = (end_date - start_date).days
        days_elapsed = (today - start_date).days
        ideal_remaining = total_points - (total_points * days_elapsed / total_days) if total_days > 0 else 0

        # Determine trend
        if remaining_points <= ideal_remaining * 0.9:
            trend = BurndownTrend.AHEAD
        elif remaining_points <= ideal_remaining * 1.1:
            trend = BurndownTrend.ON_TRACK
        elif remaining_points <= ideal_remaining * 1.3:
            trend = BurndownTrend.BEHIND
        else:
            trend = BurndownTrend.AT_RISK

        burndown = BurndownStatus(
            ideal=int(ideal_remaining),
            actual=remaining_points,
            trend=trend
        )

        # Get blockers
        blockers = self.jira_mcp.get_blockers(sprint_data.get("projectKey", "VSM"))

        # Calculate projection
        velocity_needed = remaining_points / days_remaining if days_remaining > 0 else remaining_points
        avg_daily_velocity = completed_points / max(1, days_elapsed)
        likely_to_complete = velocity_needed <= avg_daily_velocity * 1.2

        risk_factors = []
        if blockers:
            risk_factors.append(f"{len(blockers)} blocker(s) need resolution")
        if trend in [BurndownTrend.BEHIND, BurndownTrend.AT_RISK]:
            risk_factors.append("Sprint is behind schedule")
        if len(in_progress) > len(completed) * 2:
            risk_factors.append("High WIP may slow completion")

        projection = SprintProjection(
            likely_to_complete=likely_to_complete,
            confidence_score=round(random.uniform(0.7, 0.9), 2),
            risk_factors=risk_factors
        )

        data = SprintStatusData(
            sprint_id=sprint_id,
            sprint_name=sprint_data.get("name", f"Sprint {sprint_id}"),
            state=SprintState.ACTIVE,
            start_date=sprint_data.get("startDate", ""),
            end_date=sprint_data.get("endDate", ""),
            days_remaining=days_remaining,
            progress=progress,
            burndown=burndown,
            blockers=blockers,
            projection=projection
        )

        metadata = self._build_metadata(self._get_all_traces())
        return data, metadata

    # === Backlog Refinement ===

    def refine_backlog(self, request: BacklogRefinementRequest) -> tuple[BacklogRefinementData, OrchestratorMetadata]:
        """
        Orchestrate backlog refinement.
        
        Steps:
        1. Get backlog issues
        2. Check DoR compliance
        3. Suggest story points
        4. Identify dependencies
        5. Prioritize
        """
        self._clear_traces()

        # Get refined issues with DoR analysis
        refined_issues = self.jira_mcp.get_refined_issues(
            request.project_key,
            request.max_issues_to_refine
        )

        # Build DoR violations
        dor_violations: List[DorViolation] = []
        for issue in refined_issues:
            if issue.dor_status == "non_compliant":
                dor_violations.append(DorViolation(
                    issue_key=issue.issue_key,
                    missing_items=issue.missing_dor_items,
                    recommendation=f"Add {', '.join(issue.missing_dor_items)} before sprint planning"
                ))

        # Detect dependencies
        dependencies: List[IssueDependency] = []
        if request.identify_dependencies:
            dependencies = self.jira_mcp.detect_dependencies(request.project_key)

        # Simple prioritization (mock)
        prioritized_backlog = [i.issue_key for i in refined_issues]
        # Move DoR-compliant issues to top
        compliant = [i.issue_key for i in refined_issues if i.dor_status == "compliant"]
        non_compliant = [i.issue_key for i in refined_issues if i.dor_status == "non_compliant"]
        prioritized_backlog = compliant + non_compliant

        # Build recommendations
        recommendations = []
        if dor_violations:
            recommendations.append(f"{len(dor_violations)} issues need DoR items before sprint planning")
        if dependencies:
            recommendations.append(f"{len(dependencies)} dependencies identified - consider in sprint planning")
        
        compliant_count = len(refined_issues) - len(dor_violations)
        recommendations.append(f"{compliant_count} issues are ready for sprint planning")

        data = BacklogRefinementData(
            refined_issues=refined_issues,
            dor_violations=dor_violations,
            dependencies=dependencies,
            prioritized_backlog=prioritized_backlog,
            recommendations=recommendations
        )

        metadata = self._build_metadata(self._get_all_traces())
        return data, metadata

    # === Standup Analysis ===

    def analyze_standup(self, request: StandupAnalysisRequest) -> tuple[StandupAnalysisData, OrchestratorMetadata]:
        """
        Analyze team status for daily standup facilitation.
        """
        self._clear_traces()

        # Get team WIP status
        team_members = self.jira_mcp.get_team_wip_status(request.project_key)

        # Identify potential blockers (stale issues)
        potential_blockers: List[PotentialBlocker] = []
        for member in team_members:
            for stale in member.stale_issues:
                potential_blockers.append(PotentialBlocker(
                    issue_key=stale.issue_key,
                    summary=stale.summary,
                    assignee=member.name,
                    last_update="2026-02-22T21:00:00Z",
                    hours_stale=stale.hours_stale,
                    suggested_action="Check if blocked or needs help"
                ))

        # Identify WIP violations
        wip_violations: List[WipViolation] = []
        for member in team_members:
            if member.wip_count > request.wip_limit_per_person:
                wip_violations.append(WipViolation(
                    member=member.name,
                    current_wip=member.wip_count,
                    limit=request.wip_limit_per_person,
                    recommendation=f"Consider completing {member.wip_issues[0]} before starting new work"
                ))

        # Build facilitation notes
        facilitation_notes = []
        for blocker in potential_blockers:
            facilitation_notes.append(
                f"{blocker.assignee.split('@')[0]} has 1 stale issue ({blocker.issue_key}) - consider discussing blockers"
            )
        for violation in wip_violations:
            facilitation_notes.append(
                f"{violation.member.split('@')[0]} exceeds WIP limit ({violation.current_wip}/{violation.limit}) - may need to focus"
            )
        
        # Get sprint info for context
        sprint_id = request.sprint_id or "456"
        sprint_data, _ = self.jira_mcp.get_sprint(sprint_id)
        facilitation_notes.append(
            f"Sprint '{sprint_data.get('name', 'Current')}' in progress"
        )

        data = StandupAnalysisData(
            analysis_date=current_iso_timestamp(),
            sprint_id=sprint_id,
            sprint_name=sprint_data.get("name", f"Sprint {sprint_id}"),
            team_members=team_members,
            potential_blockers=potential_blockers,
            wip_violations=wip_violations,
            facilitation_notes=facilitation_notes
        )

        metadata = self._build_metadata(self._get_all_traces())
        return data, metadata

    # === Decision Log ===

    def create_decision_log(self, request: DecisionLogRequest) -> tuple[DecisionLogData, OrchestratorMetadata]:
        """
        Create a decision log entry in Confluence.
        """
        self._clear_traces()

        # Create the decision page in Confluence
        page_result, _ = self.confluence_mcp.create_decision_log_entry(
            space_key=request.confluence_space_key,
            decision=request.decision
        )

        # Link issues if provided
        linked_issues = []
        if request.decision.related_issues:
            for issue_key in request.decision.related_issues:
                # In a real implementation, we would add a link in Jira
                # For now, just track the linked issues
                linked_issues.append(issue_key)

        data = DecisionLogData(
            decision_id=f"DEC-{page_result['id']}",
            title=request.decision.title,
            confluence_page_id=page_result["id"],
            confluence_page_url=page_result["url"],
            linked_issues=linked_issues,
            created_at=current_iso_timestamp()
        )

        metadata = self._build_metadata(self._get_all_traces())
        return data, metadata

    # === Agent Query ===

    def process_query(self, request: AgentQueryRequest) -> tuple[AgentQueryData, OrchestratorMetadata]:
        """
        Process a natural language query about the project.
        
        Analyzes the query and orchestrates appropriate MCP calls.
        """
        self._clear_traces()

        query_lower = request.query.lower()

        # Determine query type and process accordingly
        if any(word in query_lower for word in ["velocidad", "velocity", "sprint", "puntos"]):
            return self._process_velocity_query(request)
        elif any(word in query_lower for word in ["bloqueado", "blocker", "blocked", "stale"]):
            return self._process_blocker_query(request)
        elif any(word in query_lower for word in ["estado", "status", "progreso", "progress"]):
            return self._process_status_query(request)
        else:
            return self._process_general_query(request)

    def _process_velocity_query(self, request: AgentQueryRequest) -> tuple[AgentQueryData, OrchestratorMetadata]:
        """Process a velocity-related query."""
        # Get sprint history
        sprints, _ = self.jira_mcp.get_sprints("123", state="closed")
        
        sprint_count = request.context.sprint_count if request.context else 3
        recent_sprints = sprints[:sprint_count]

        sprints_data = []
        total_velocity = 0
        for sprint in recent_sprints:
            velocity = sprint.get("velocity", 0) or 0
            sprints_data.append({
                "sprintId": sprint["id"],
                "name": sprint["name"],
                "velocity": velocity
            })
            total_velocity += velocity

        avg_velocity = total_velocity / len(recent_sprints) if recent_sprints else 0

        answer = f"La velocidad del equipo en los últimos {len(recent_sprints)} sprints ha sido: "
        answer += ", ".join([f"{s['name']}: {s['velocity']} SP" for s in sprints_data])
        answer += f". Promedio: {avg_velocity:.2f} SP por sprint."

        data = AgentQueryData(
            query_type=QueryType.METRICS,
            answer=answer,
            structured_data={
                "sprints": sprints_data,
                "averageVelocity": round(avg_velocity, 2),
                "trend": "stable"
            },
            recommendations=[
                "Velocity is stable. Consider maintaining current capacity planning."
            ],
            sources=[
                DataSource(source_type="jira", reference=f"Sprint data from board 123")
            ]
        )

        metadata = self._build_metadata(self._get_all_traces())
        return data, metadata

    def _process_blocker_query(self, request: AgentQueryRequest) -> tuple[AgentQueryData, OrchestratorMetadata]:
        """Process a blocker-related query."""
        blockers = self.jira_mcp.get_blockers(request.project_key)

        if blockers:
            answer = f"Hay {len(blockers)} issue(s) potencialmente bloqueados:\n"
            for b in blockers:
                answer += f"- {b.issue_key}: {b.summary} (asignado a {b.assignee}, {b.blocked_days} días)\n"
        else:
            answer = "No hay issues bloqueados actualmente."

        data = AgentQueryData(
            query_type=QueryType.BLOCKERS,
            answer=answer,
            structured_data={
                "blockers": [b.to_dict() for b in blockers],
                "count": len(blockers)
            },
            recommendations=[
                "Review blocked issues in next standup" if blockers else "No action needed"
            ],
            sources=[
                DataSource(source_type="jira", reference=f"Issues from project {request.project_key}")
            ]
        )

        metadata = self._build_metadata(self._get_all_traces())
        return data, metadata

    def _process_status_query(self, request: AgentQueryRequest) -> tuple[AgentQueryData, OrchestratorMetadata]:
        """Process a status-related query."""
        sprint_id = request.context.sprint_id if request.context else "456"
        status_data, _ = self.get_sprint_status(sprint_id)

        answer = f"Estado del {status_data.sprint_name}:\n"
        answer += f"- Progreso: {status_data.progress.percent_complete}% completado\n"
        answer += f"- Issues: {status_data.progress.completed_issues}/{status_data.progress.total_issues} completados\n"
        answer += f"- Story Points: {status_data.progress.completed_story_points}/{status_data.progress.total_story_points} SP\n"
        answer += f"- Días restantes: {status_data.days_remaining}\n"
        answer += f"- Tendencia: {status_data.burndown.trend.value}"

        data = AgentQueryData(
            query_type=QueryType.STATUS,
            answer=answer,
            structured_data=status_data.to_dict(),
            recommendations=status_data.projection.risk_factors if status_data.projection.risk_factors else ["Sprint on track"],
            sources=[
                DataSource(source_type="jira", reference=f"Sprint {sprint_id}")
            ]
        )

        # Re-use traces from get_sprint_status
        metadata = self._build_metadata(self._get_all_traces())
        return data, metadata

    def _process_general_query(self, request: AgentQueryRequest) -> tuple[AgentQueryData, OrchestratorMetadata]:
        """Process a general query."""
        # Get basic project info
        issues, _ = self.jira_mcp.search_issues(request.project_key, max_results=20)
        
        total = len(issues)
        done = len([i for i in issues if i.get("status") == "Done"])
        in_progress = len([i for i in issues if i.get("status") == "In Progress"])
        todo = len([i for i in issues if i.get("status") == "To Do"])

        answer = f"Resumen del proyecto {request.project_key}:\n"
        answer += f"- Total issues: {total}\n"
        answer += f"- Done: {done}\n"
        answer += f"- In Progress: {in_progress}\n"
        answer += f"- To Do: {todo}"

        data = AgentQueryData(
            query_type=QueryType.SUMMARY,
            answer=answer,
            structured_data={
                "projectKey": request.project_key,
                "issueCount": {
                    "total": total,
                    "done": done,
                    "inProgress": in_progress,
                    "toDo": todo
                }
            },
            recommendations=[
                "Use more specific queries for detailed information"
            ],
            sources=[
                DataSource(source_type="jira", reference=f"Project {request.project_key}")
            ]
        )

        metadata = self._build_metadata(self._get_all_traces())
        return data, metadata

    # =========================================================================
    # AGENT INVOCATION - Main Entry Point
    # =========================================================================

    def invoke_agent(self, request: AgentInvokeRequest) -> tuple[AgentInvokeData, OrchestratorMetadata]:
        """
        Punto de entrada principal del agente orquestador.
        
        Este método:
        1. Analiza la intención del usuario
        2. Determina qué MCPs necesita invocar
        3. Orquesta las llamadas a los MCPs
        4. Genera una respuesta conversacional consolidada
        
        Args:
            request: Solicitud de invocación del agente
            
        Returns:
            Tuple de (AgentInvokeData, OrchestratorMetadata)
        """
        self._clear_traces()
        
        # Generar session_id si no existe
        session_id = request.session_id or generate_trace_id()
        
        # Step 1: Detectar intención
        intent, confidence = self._detect_intent(request.message)
        
        # Step 2: Ejecutar la acción según la intención
        response_text, structured_data, mcp_summaries, actions, followups, sources, warnings = \
            self._execute_intent(intent, request)
        
        # Step 3: Construir respuesta
        data = AgentInvokeData(
            response=response_text,
            intent=intent,
            intent_confidence=confidence,
            mcp_calls_summary=mcp_summaries,
            actions_taken=actions,
            structured_data=structured_data,
            suggested_followups=followups,
            data_sources=sources,
            warnings=warnings,
            session_id=session_id
        )
        
        metadata = self._build_metadata(self._get_all_traces())
        return data, metadata

    def _detect_intent(self, message: str) -> tuple[AgentIntent, float]:
        """
        Detecta la intención del usuario a partir del mensaje.
        
        En una implementación real, esto usaría NLU/LLM.
        Por ahora, usamos patrones simples.
        """
        message_lower = message.lower()
        
        # Patrones de intención (ordenados por especificidad)
        intent_patterns = [
            # Saludos
            (AgentIntent.GENERAL_GREETING, 0.95, 
             ["hola", "hello", "hi", "buenos días", "buenas tardes", "hey"]),
            
            # Ayuda
            (AgentIntent.GENERAL_HELP, 0.90,
             ["ayuda", "help", "qué puedes hacer", "what can you do", "comandos", "opciones"]),
            
            # Sprint Status
            (AgentIntent.QUERY_SPRINT_STATUS, 0.92,
             ["estado del sprint", "sprint status", "cómo va el sprint", "progreso del sprint", 
              "burndown", "avance del sprint"]),
            
            # Velocidad
            (AgentIntent.QUERY_VELOCITY, 0.90,
             ["velocidad", "velocity", "puntos por sprint", "story points completados",
              "rendimiento del equipo"]),
            
            # Blockers
            (AgentIntent.QUERY_BLOCKERS, 0.93,
             ["bloqueadores", "blockers", "bloqueado", "blocked", "impedimentos", 
              "qué está trabado", "issues parados"]),
            
            # Backlog
            (AgentIntent.QUERY_BACKLOG, 0.88,
             ["backlog", "pendientes", "issues sin asignar", "trabajo pendiente"]),
            
            # Team workload
            (AgentIntent.QUERY_TEAM_WORKLOAD, 0.89,
             ["carga de trabajo", "workload", "quién tiene más trabajo", "distribución",
              "wip", "work in progress"]),
            
            # Metrics
            (AgentIntent.QUERY_METRICS, 0.87,
             ["métricas", "metrics", "estadísticas", "kpis", "indicadores"]),
            
            # Plan Sprint
            (AgentIntent.ACTION_PLAN_SPRINT, 0.91,
             ["planificar sprint", "plan sprint", "crear sprint", "nuevo sprint",
              "iniciar planificación"]),
            
            # Review Sprint
            (AgentIntent.ACTION_REVIEW_SPRINT, 0.91,
             ["review sprint", "revisión del sprint", "sprint review", "revisar sprint",
              "retrospectiva"]),
            
            # Refine Backlog
            (AgentIntent.ACTION_REFINE_BACKLOG, 0.89,
             ["refinar backlog", "refinement", "grooming", "refinar historias"]),
            
            # Decision Log
            (AgentIntent.ACTION_CREATE_DECISION_LOG, 0.88,
             ["decision log", "registrar decisión", "documentar decisión", "adr"]),
            
            # Generate Report
            (AgentIntent.ACTION_GENERATE_REPORT, 0.87,
             ["generar reporte", "generate report", "crear informe", "exportar"]),
            
            # Analyze Standup
            (AgentIntent.ANALYZE_STANDUP, 0.90,
             ["standup", "daily", "reunión diaria", "scrum diario"]),
            
            # Analyze Risks
            (AgentIntent.ANALYZE_RISKS, 0.86,
             ["riesgos", "risks", "problemas potenciales", "alertas"]),
        ]
        
        # Buscar coincidencia
        for intent, base_confidence, patterns in intent_patterns:
            for pattern in patterns:
                if pattern in message_lower:
                    # Ajustar confianza según longitud de coincidencia
                    confidence = base_confidence * (0.9 + 0.1 * len(pattern) / len(message_lower))
                    return intent, min(confidence, 0.99)
        
        # Si no hay coincidencia clara, intentar inferir
        if "?" in message:
            return AgentIntent.QUERY_METRICS, 0.60
        
        return AgentIntent.UNKNOWN, 0.30

    def _execute_intent(
        self, 
        intent: AgentIntent, 
        request: AgentInvokeRequest
    ) -> tuple[str, Optional[Dict], List[MCPCallSummary], List[AgentAction], List[str], List[DataSource], List[str]]:
        """
        Ejecuta la acción correspondiente a la intención detectada.
        
        Returns:
            Tuple de (response_text, structured_data, mcp_summaries, actions, followups, sources, warnings)
        """
        mcp_summaries = []
        actions = []
        sources = []
        warnings = []
        followups = []
        structured_data = None
        
        project_key = request.project_key
        context = request.context or {}
        
        # === Saludos ===
        if intent == AgentIntent.GENERAL_GREETING:
            response = (
                f"¡Hola! Soy tu Virtual Scrum Manager para el proyecto {project_key}. "
                "Puedo ayudarte con:\n"
                "• 📊 Consultar el estado del sprint y métricas\n"
                "• 🚧 Identificar bloqueadores y riesgos\n"
                "• 📋 Gestionar y refinar el backlog\n"
                "• 📝 Documentar decisiones en Confluence\n"
                "• 🏃 Planificar y revisar sprints\n\n"
                "¿En qué puedo ayudarte hoy?"
            )
            followups = [
                "¿Cuál es el estado del sprint actual?",
                "¿Hay algún bloqueador?",
                "Muéstrame las métricas del equipo"
            ]
            return response, None, [], [], followups, [], []
        
        # === Ayuda ===
        if intent == AgentIntent.GENERAL_HELP:
            response = (
                "Estas son las cosas que puedo hacer por ti:\n\n"
                "**Consultas:**\n"
                "• \"¿Cuál es el estado del sprint?\" - Ver progreso y burndown\n"
                "• \"¿Hay bloqueadores?\" - Identificar issues trabados\n"
                "• \"¿Cuál es la velocidad del equipo?\" - Ver métricas históricas\n"
                "• \"¿Cómo está la carga de trabajo?\" - Ver WIP por miembro\n\n"
                "**Acciones:**\n"
                "• \"Planificar sprint\" - Iniciar planificación de sprint\n"
                "• \"Refinar backlog\" - Analizar DoR y sugerir mejoras\n"
                "• \"Analizar standup\" - Preparar la daily\n"
                "• \"Registrar decisión\" - Crear ADR en Confluence\n"
            )
            followups = [
                "Muéstrame el estado del sprint",
                "¿Hay bloqueadores en el equipo?",
                "Quiero planificar un nuevo sprint"
            ]
            return response, None, [], [], followups, [], []
        
        # === Query Sprint Status ===
        if intent == AgentIntent.QUERY_SPRINT_STATUS:
            sprint_id = context.get("sprintId", "456")
            
            # Obtener datos del sprint
            sprint_data, _ = self.jira_mcp.get_sprint(sprint_id)
            mcp_summaries.append(MCPCallSummary(
                mcp_type=MCPType.JIRA,
                operation="getSprint",
                description=f"Obtener información del sprint {sprint_id}",
                success=True,
                data_retrieved="Sprint details"
            ))
            
            # Obtener issues del sprint
            issues, _ = self.jira_mcp.get_sprint_issues(sprint_id)
            mcp_summaries.append(MCPCallSummary(
                mcp_type=MCPType.JIRA,
                operation="getSprintIssues",
                description=f"Obtener issues del sprint",
                success=True,
                data_retrieved=f"{len(issues)} issues"
            ))
            
            # Calcular métricas
            total = len(issues)
            done = len([i for i in issues if i.get("status") == "Done"])
            in_progress = len([i for i in issues if i.get("status") == "In Progress"])
            todo = len([i for i in issues if i.get("status") == "To Do"])
            
            total_points = sum(i.get("storyPoints", 0) or 0 for i in issues)
            done_points = sum(i.get("storyPoints", 0) or 0 for i in issues if i.get("status") == "Done")
            percent = round(done_points / total_points * 100, 1) if total_points > 0 else 0
            
            # Determinar tendencia
            if percent >= 80:
                trend_emoji = "🟢"
                trend_text = "excelente progreso"
            elif percent >= 50:
                trend_emoji = "🟡"
                trend_text = "en buen camino"
            else:
                trend_emoji = "🔴"
                trend_text = "necesita atención"
            
            response = (
                f"**Estado del Sprint: {sprint_data.get('name', 'Sprint Actual')}** {trend_emoji}\n\n"
                f"📊 **Progreso:** {percent}% completado ({trend_text})\n\n"
                f"**Issues:**\n"
                f"• ✅ Completados: {done}/{total}\n"
                f"• 🔄 En progreso: {in_progress}\n"
                f"• 📋 Por hacer: {todo}\n\n"
                f"**Story Points:**\n"
                f"• Completados: {done_points}/{total_points} SP\n"
                f"• Restantes: {total_points - done_points} SP\n\n"
                f"📅 **Días restantes:** {sprint_data.get('daysRemaining', 'N/A')}"
            )
            
            structured_data = {
                "sprintId": sprint_id,
                "sprintName": sprint_data.get("name"),
                "progress": {
                    "percent": percent,
                    "issues": {"done": done, "inProgress": in_progress, "todo": todo, "total": total},
                    "storyPoints": {"done": done_points, "total": total_points}
                },
                "trend": trend_text
            }
            
            sources = [DataSource(source_type="jira", reference=f"Sprint {sprint_id}")]
            
            if percent < 50:
                warnings.append("El sprint está por debajo del 50% de progreso")
            
            followups = [
                "¿Hay bloqueadores en el sprint?",
                "Muéstrame la carga de trabajo del equipo",
                "¿Cuál es la velocidad histórica?"
            ]
            
            return response, structured_data, mcp_summaries, actions, followups, sources, warnings
        
        # === Query Blockers ===
        if intent == AgentIntent.QUERY_BLOCKERS:
            blockers = self.jira_mcp.get_blockers(project_key)
            mcp_summaries.append(MCPCallSummary(
                mcp_type=MCPType.JIRA,
                operation="getBlockers",
                description="Buscar issues bloqueados o stale",
                success=True,
                data_retrieved=f"{len(blockers)} bloqueadores"
            ))
            
            if blockers:
                response = f"🚧 **Encontré {len(blockers)} posible(s) bloqueador(es):**\n\n"
                for b in blockers:
                    response += (
                        f"• **{b.issue_key}**: {b.summary}\n"
                        f"  👤 Asignado a: {b.assignee}\n"
                        f"  ⏰ Bloqueado hace: {b.blocked_days} días\n"
                        f"  💡 Acción sugerida: {b.suggested_action}\n\n"
                    )
                
                response += "\n⚠️ **Recomendación:** Revisa estos issues en el próximo standup."
                warnings.append(f"Hay {len(blockers)} issue(s) potencialmente bloqueados")
            else:
                response = "✅ **¡Excelente!** No hay bloqueadores identificados en este momento."
            
            structured_data = {
                "blockers": [b.to_dict() for b in blockers],
                "count": len(blockers)
            }
            
            sources = [DataSource(source_type="jira", reference=f"Project {project_key}")]
            followups = [
                "¿Cuál es el estado del sprint?",
                "Muéstrame la carga de trabajo del equipo"
            ]
            
            return response, structured_data, mcp_summaries, actions, followups, sources, warnings
        
        # === Query Velocity ===
        if intent == AgentIntent.QUERY_VELOCITY:
            sprints, _ = self.jira_mcp.get_sprints("123", state="closed")
            mcp_summaries.append(MCPCallSummary(
                mcp_type=MCPType.JIRA,
                operation="getSprints",
                description="Obtener sprints cerrados para calcular velocidad",
                success=True,
                data_retrieved=f"{len(sprints)} sprints"
            ))
            
            sprint_count = context.get("sprintCount", 5)
            recent = sprints[:sprint_count]
            
            velocities = [s.get("velocity", 0) or random.randint(30, 50) for s in recent]
            avg_velocity = sum(velocities) / len(velocities) if velocities else 0
            
            response = f"📈 **Velocidad del equipo** (últimos {len(recent)} sprints):\n\n"
            for i, sprint in enumerate(recent):
                response += f"• {sprint.get('name', f'Sprint {i+1}')}: **{velocities[i]} SP**\n"
            
            response += f"\n📊 **Promedio:** {avg_velocity:.1f} Story Points por sprint"
            
            # Tendencia
            if len(velocities) >= 2:
                if velocities[0] > velocities[-1]:
                    response += "\n📈 Tendencia: Mejorando"
                elif velocities[0] < velocities[-1]:
                    response += "\n📉 Tendencia: Decreciendo"
                else:
                    response += "\n➡️ Tendencia: Estable"
            
            structured_data = {
                "sprints": [{"name": s.get("name"), "velocity": v} for s, v in zip(recent, velocities)],
                "averageVelocity": round(avg_velocity, 1)
            }
            
            sources = [DataSource(source_type="jira", reference="Sprint history")]
            followups = [
                "¿Cuál es el estado del sprint actual?",
                "¿Cuántos puntos podemos comprometer para el próximo sprint?"
            ]
            
            return response, structured_data, mcp_summaries, actions, followups, sources, warnings
        
        # === Query Team Workload ===
        if intent == AgentIntent.QUERY_TEAM_WORKLOAD:
            team_members = self.jira_mcp.get_team_wip_status(project_key)
            mcp_summaries.append(MCPCallSummary(
                mcp_type=MCPType.JIRA,
                operation="getTeamWipStatus",
                description="Obtener WIP del equipo",
                success=True,
                data_retrieved=f"{len(team_members)} miembros"
            ))
            
            response = "👥 **Carga de trabajo del equipo:**\n\n"
            
            wip_limit = 3
            overloaded = []
            
            for member in team_members:
                name = member.name.split("@")[0]
                wip = member.wip_count
                
                if wip > wip_limit:
                    status = "🔴 Sobrecargado"
                    overloaded.append(name)
                elif wip == wip_limit:
                    status = "🟡 Al límite"
                else:
                    status = "🟢 OK"
                
                response += f"• **{name}**: {wip} issues en progreso {status}\n"
                if member.wip_issues:
                    for issue in member.wip_issues[:2]:
                        response += f"  └ {issue}\n"
            
            if overloaded:
                response += f"\n⚠️ **Atención:** {', '.join(overloaded)} excede(n) el límite WIP ({wip_limit})"
                warnings.append(f"{len(overloaded)} miembro(s) exceden el límite WIP")
            
            structured_data = {
                "teamMembers": [m.to_dict() for m in team_members],
                "wipLimit": wip_limit,
                "overloadedCount": len(overloaded)
            }
            
            sources = [DataSource(source_type="jira", reference=f"Project {project_key}")]
            followups = [
                "¿Hay bloqueadores?",
                "Analizar el standup de hoy"
            ]
            
            return response, structured_data, mcp_summaries, actions, followups, sources, warnings
        
        # === Analyze Standup ===
        if intent == AgentIntent.ANALYZE_STANDUP:
            # Obtener estado del equipo
            team_members = self.jira_mcp.get_team_wip_status(project_key)
            mcp_summaries.append(MCPCallSummary(
                mcp_type=MCPType.JIRA,
                operation="getTeamWipStatus",
                description="Analizar estado del equipo para standup",
                success=True,
                data_retrieved=f"{len(team_members)} miembros"
            ))
            
            # Obtener bloqueadores
            blockers = self.jira_mcp.get_blockers(project_key)
            mcp_summaries.append(MCPCallSummary(
                mcp_type=MCPType.JIRA,
                operation="getBlockers",
                description="Identificar bloqueadores",
                success=True,
                data_retrieved=f"{len(blockers)} bloqueadores"
            ))
            
            response = "📋 **Preparación para el Daily Standup:**\n\n"
            
            # Puntos de atención
            response += "**🎯 Puntos de atención:**\n"
            
            attention_items = []
            
            for member in team_members:
                name = member.name.split("@")[0]
                if member.wip_count > 3:
                    attention_items.append(f"• {name} tiene {member.wip_count} issues en progreso (posible sobrecarga)")
                for stale in member.stale_issues:
                    attention_items.append(f"• {stale.issue_key} asignado a {name} lleva {stale.hours_stale}h sin actualización")
            
            for blocker in blockers:
                attention_items.append(f"• 🚧 {blocker.issue_key} posiblemente bloqueado ({blocker.blocked_days} días)")
            
            if attention_items:
                response += "\n".join(attention_items)
            else:
                response += "• ✅ No hay puntos críticos de atención"
            
            response += "\n\n**💡 Sugerencias para facilitar:**\n"
            response += "• Comenzar preguntando sobre los items stale\n"
            response += "• Verificar si hay impedimentos no reportados\n"
            response += "• Revisar el burndown al final"
            
            structured_data = {
                "teamStatus": [m.to_dict() for m in team_members],
                "blockers": [b.to_dict() for b in blockers],
                "attentionItems": len(attention_items)
            }
            
            actions.append(AgentAction(
                action_type="analyze",
                description="Análisis de estado para standup",
                status="completed",
                result={"itemsAnalyzed": len(team_members), "blockersFound": len(blockers)}
            ))
            
            sources = [DataSource(source_type="jira", reference=f"Project {project_key}")]
            followups = [
                "¿Cuál es el estado del sprint?",
                "Muéstrame los bloqueadores en detalle"
            ]
            
            return response, structured_data, mcp_summaries, actions, followups, sources, warnings
        
        # === Action: Refine Backlog ===
        if intent == AgentIntent.ACTION_REFINE_BACKLOG:
            refined = self.jira_mcp.get_refined_issues(project_key, max_issues=10)
            mcp_summaries.append(MCPCallSummary(
                mcp_type=MCPType.JIRA,
                operation="getRefinedIssues",
                description="Analizar backlog para refinamiento",
                success=True,
                data_retrieved=f"{len(refined)} issues analizados"
            ))
            
            ready = [r for r in refined if r.dor_status == "compliant"]
            not_ready = [r for r in refined if r.dor_status != "compliant"]
            
            response = f"📋 **Análisis de Refinamiento del Backlog** ({project_key}):\n\n"
            response += f"✅ **Listos para sprint ({len(ready)}):**\n"
            for r in ready[:5]:
                response += f"• {r.issue_key}: {r.summary} ({r.suggested_points} SP)\n"
            
            if not_ready:
                response += f"\n⚠️ **Necesitan trabajo ({len(not_ready)}):**\n"
                for r in not_ready[:5]:
                    missing = ", ".join(r.missing_dor_items) if r.missing_dor_items else "DoR no validado"
                    response += f"• {r.issue_key}: Falta {missing}\n"
            
            structured_data = {
                "readyForSprint": [r.to_dict() for r in ready],
                "needsWork": [r.to_dict() for r in not_ready],
                "summary": {"ready": len(ready), "needsWork": len(not_ready)}
            }
            
            actions.append(AgentAction(
                action_type="analyze_backlog",
                description="Análisis de DoR completado",
                status="completed",
                result={"analyzed": len(refined), "ready": len(ready)}
            ))
            
            sources = [DataSource(source_type="jira", reference=f"Backlog {project_key}")]
            followups = [
                "Planificar sprint con los issues listos",
                "¿Qué falta para que los issues estén listos?"
            ]
            
            return response, structured_data, mcp_summaries, actions, followups, sources, warnings
        
        # === Unknown Intent ===
        response = (
            f"No estoy seguro de entender tu solicitud: \"{request.message}\"\n\n"
            "Puedo ayudarte con:\n"
            "• Consultar el estado del sprint\n"
            "• Identificar bloqueadores\n"
            "• Ver la velocidad del equipo\n"
            "• Analizar la carga de trabajo\n"
            "• Preparar el standup\n"
            "• Refinar el backlog\n\n"
            "¿Podrías reformular tu pregunta?"
        )
        
        followups = [
            "¿Cuál es el estado del sprint?",
            "¿Hay bloqueadores?",
            "Muéstrame las métricas del equipo"
        ]
        
        return response, None, [], [], followups, [], []

