"""
Domain models and schemas for the VSM Agent Orchestrator.
Pure Python dataclasses - no external dependencies.
Designed for future Bedrock Agent Action Group compatibility.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime, date
import uuid


# === Enums ===

class MCPType(Enum):
    JIRA = "jira"
    CONFLUENCE = "confluence"


class SprintState(Enum):
    FUTURE = "future"
    ACTIVE = "active"
    CLOSED = "closed"


class BurndownTrend(Enum):
    AHEAD = "ahead"
    ON_TRACK = "on_track"
    BEHIND = "behind"
    AT_RISK = "at_risk"


class DependencyType(Enum):
    BLOCKS = "blocks"
    IS_BLOCKED_BY = "is_blocked_by"
    RELATES_TO = "relates_to"


class QueryType(Enum):
    METRICS = "metrics"
    STATUS = "status"
    BLOCKERS = "blockers"
    SUMMARY = "summary"
    COMPARISON = "comparison"
    FORECAST = "forecast"


class AgentIntent(Enum):
    """Intenciones detectadas por el agente."""
    # Consultas de información
    QUERY_SPRINT_STATUS = "query_sprint_status"
    QUERY_VELOCITY = "query_velocity"
    QUERY_BLOCKERS = "query_blockers"
    QUERY_BACKLOG = "query_backlog"
    QUERY_TEAM_WORKLOAD = "query_team_workload"
    QUERY_METRICS = "query_metrics"
    QUERY_PROJECTS = "query_projects"
    QUERY_COMPLETED_ISSUES = "query_completed_issues"
    
    # Acciones de Sprint
    ACTION_PLAN_SPRINT = "action_plan_sprint"
    ACTION_REVIEW_SPRINT = "action_review_sprint"
    ACTION_START_SPRINT = "action_start_sprint"
    ACTION_CLOSE_SPRINT = "action_close_sprint"
    
    # Acciones de Backlog
    ACTION_REFINE_BACKLOG = "action_refine_backlog"
    ACTION_PRIORITIZE_BACKLOG = "action_prioritize_backlog"
    
    # Acciones de Documentación
    ACTION_CREATE_DECISION_LOG = "action_create_decision_log"
    ACTION_GENERATE_REPORT = "action_generate_report"
    
    # Acciones de Proyectos
    ACTION_CREATE_PROJECT = "action_create_project"
    
    # Acciones de Issues
    ACTION_CREATE_STORY = "action_create_story"
    ACTION_CREATE_TASK = "action_create_task"
    ACTION_CREATE_BUG = "action_create_bug"
    ACTION_ADD_COMMENT = "action_add_comment"
    ACTION_SET_STORY_POINTS = "action_set_story_points"
    ACTION_TRANSITION_ISSUE = "action_transition_issue"
    
    # Análisis
    ANALYZE_STANDUP = "analyze_standup"
    ANALYZE_RISKS = "analyze_risks"
    
    # General
    GENERAL_HELP = "general_help"
    GENERAL_GREETING = "general_greeting"
    UNKNOWN = "unknown"


class ConversationRole(Enum):
    """Roles en la conversación."""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class ErrorCode(Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    SCRUM_VALIDATION_ERROR = "SCRUM_VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    TENANT_NOT_FOUND = "TENANT_NOT_FOUND"
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    SPRINT_NOT_FOUND = "SPRINT_NOT_FOUND"
    MCP_JIRA_ERROR = "MCP_JIRA_ERROR"
    MCP_CONFLUENCE_ERROR = "MCP_CONFLUENCE_ERROR"
    ORCHESTRATION_ERROR = "ORCHESTRATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# === MCP Tracing ===

@dataclass
class MCPInvocationTrace:
    """Trace of a single MCP invocation."""
    mcp_type: MCPType
    operation: str
    duration_ms: int
    success: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "mcpType": self.mcp_type.value,
            "operation": self.operation,
            "durationMs": self.duration_ms,
            "success": self.success
        }
        if self.error_code:
            result["errorCode"] = self.error_code
        if self.error_message:
            result["errorMessage"] = self.error_message
        return result


@dataclass
class OrchestratorMetadata:
    """Metadata about the orchestration execution."""
    mcp_calls: List[MCPInvocationTrace]
    total_latency_ms: int
    tenant_id: str
    simulated_confidence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mcpCalls": [call.to_dict() for call in self.mcp_calls],
            "totalLatencyMs": self.total_latency_ms,
            "simulatedConfidenceScore": self.simulated_confidence_score,
            "tenantId": self.tenant_id
        }


# === Sprint Planning ===

@dataclass
class SprintPlanRequest:
    """Request to plan a sprint."""
    project_key: str
    board_id: str
    sprint_name: str
    start_date: str
    end_date: str
    sprint_goal: Optional[str] = None
    team_capacity: Optional[int] = None
    candidate_issues: List[str] = field(default_factory=list)
    document_in_confluence: bool = True
    confluence_space_key: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SprintPlanRequest":
        return cls(
            project_key=data.get("projectKey", ""),
            board_id=data.get("boardId", ""),
            sprint_name=data.get("sprintName", ""),
            start_date=data.get("startDate", ""),
            end_date=data.get("endDate", ""),
            sprint_goal=data.get("sprintGoal"),
            team_capacity=data.get("teamCapacity"),
            candidate_issues=data.get("candidateIssues", []),
            document_in_confluence=data.get("documentInConfluence", True),
            confluence_space_key=data.get("confluenceSpaceKey")
        )

    def validate(self) -> List[str]:
        errors = []
        if not self.project_key:
            errors.append("projectKey is required")
        if not self.board_id:
            errors.append("boardId is required")
        if not self.sprint_name:
            errors.append("sprintName is required")
        if not self.start_date:
            errors.append("startDate is required")
        if not self.end_date:
            errors.append("endDate is required")
        return errors


@dataclass
class SprintIssue:
    """Issue included in a sprint."""
    issue_key: str
    summary: str
    story_points: int = 0
    dor_compliant: bool = True
    status: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "issueKey": self.issue_key,
            "summary": self.summary,
            "storyPoints": self.story_points,
            "dorCompliant": self.dor_compliant
        }
        if self.status:
            result["status"] = self.status
        return result


@dataclass
class ExcludedIssue:
    """Issue excluded from sprint with reason."""
    issue_key: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issueKey": self.issue_key,
            "reason": self.reason
        }


@dataclass
class SprintPlanData:
    """Data returned from sprint planning."""
    sprint_id: str
    sprint_name: str
    sprint_goal: Optional[str]
    start_date: str
    end_date: str
    issues_included: List[SprintIssue]
    issues_excluded: List[ExcludedIssue]
    total_story_points: int
    capacity_utilization: float
    confluence_page_url: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sprintId": self.sprint_id,
            "sprintName": self.sprint_name,
            "sprintGoal": self.sprint_goal,
            "startDate": self.start_date,
            "endDate": self.end_date,
            "issuesIncluded": [i.to_dict() for i in self.issues_included],
            "issuesExcluded": [i.to_dict() for i in self.issues_excluded],
            "totalStoryPoints": self.total_story_points,
            "capacityUtilization": self.capacity_utilization,
            "confluencePageUrl": self.confluence_page_url,
            "recommendations": self.recommendations
        }


# === Sprint Review ===

@dataclass
class SprintReviewRequest:
    """Request to review a completed sprint."""
    project_key: str
    sprint_id: str
    generate_confluence_report: bool = True
    confluence_space_key: Optional[str] = None
    include_metrics: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SprintReviewRequest":
        return cls(
            project_key=data.get("projectKey", ""),
            sprint_id=data.get("sprintId", ""),
            generate_confluence_report=data.get("generateConfluenceReport", True),
            confluence_space_key=data.get("confluenceSpaceKey"),
            include_metrics=data.get("includeMetrics", [])
        )

    def validate(self) -> List[str]:
        errors = []
        if not self.project_key:
            errors.append("projectKey is required")
        if not self.sprint_id:
            errors.append("sprintId is required")
        return errors


@dataclass
class SprintMetrics:
    """Sprint metrics."""
    velocity: int = 0
    planned_points: int = 0
    say_do_ratio: float = 0.0
    average_cycle_time: float = 0.0
    throughput: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "velocity": self.velocity,
            "plannedPoints": self.planned_points,
            "sayDoRatio": self.say_do_ratio,
            "averageCycleTime": self.average_cycle_time,
            "throughput": self.throughput
        }


@dataclass
class SprintReviewData:
    """Data returned from sprint review."""
    sprint_id: str
    sprint_name: str
    metrics: SprintMetrics
    completed_issues: List[SprintIssue]
    incomplete_issues: List[SprintIssue]
    confluence_report_url: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sprintId": self.sprint_id,
            "sprintName": self.sprint_name,
            "metrics": self.metrics.to_dict(),
            "completedIssues": [i.to_dict() for i in self.completed_issues],
            "incompleteIssues": [i.to_dict() for i in self.incomplete_issues],
            "confluenceReportUrl": self.confluence_report_url,
            "recommendations": self.recommendations
        }


# === Sprint Status ===

@dataclass
class SprintProgress:
    """Sprint progress tracking."""
    total_issues: int = 0
    completed_issues: int = 0
    in_progress_issues: int = 0
    todo_issues: int = 0
    total_story_points: int = 0
    completed_story_points: int = 0
    percent_complete: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "totalIssues": self.total_issues,
            "completedIssues": self.completed_issues,
            "inProgressIssues": self.in_progress_issues,
            "todoIssues": self.todo_issues,
            "totalStoryPoints": self.total_story_points,
            "completedStoryPoints": self.completed_story_points,
            "percentComplete": self.percent_complete
        }


@dataclass
class BurndownStatus:
    """Burndown chart status."""
    ideal: int
    actual: int
    trend: BurndownTrend

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ideal": self.ideal,
            "actual": self.actual,
            "trend": self.trend.value
        }


@dataclass
class BlockerIssue:
    """Issue that is blocking."""
    issue_key: str
    summary: str
    blocked_days: int
    assignee: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issueKey": self.issue_key,
            "summary": self.summary,
            "blockedDays": self.blocked_days,
            "assignee": self.assignee
        }


@dataclass
class SprintProjection:
    """Sprint completion projection."""
    likely_to_complete: bool
    confidence_score: float
    risk_factors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "likelyToComplete": self.likely_to_complete,
            "confidenceScore": self.confidence_score,
            "riskFactors": self.risk_factors
        }


@dataclass
class SprintStatusData:
    """Sprint status data."""
    sprint_id: str
    sprint_name: str
    state: SprintState
    start_date: str
    end_date: str
    days_remaining: int
    progress: SprintProgress
    burndown: BurndownStatus
    blockers: List[BlockerIssue]
    projection: SprintProjection

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sprintId": self.sprint_id,
            "sprintName": self.sprint_name,
            "state": self.state.value,
            "startDate": self.start_date,
            "endDate": self.end_date,
            "daysRemaining": self.days_remaining,
            "progress": self.progress.to_dict(),
            "burndown": self.burndown.to_dict(),
            "blockers": [b.to_dict() for b in self.blockers],
            "projection": self.projection.to_dict()
        }


# === Backlog Refinement ===

@dataclass
class BacklogRefinementRequest:
    """Request to refine backlog."""
    project_key: str
    max_issues_to_refine: int = 10
    check_dor: bool = True
    suggest_story_points: bool = True
    identify_dependencies: bool = True
    prioritization_criteria: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BacklogRefinementRequest":
        return cls(
            project_key=data.get("projectKey", ""),
            max_issues_to_refine=data.get("maxIssuesToRefine", 10),
            check_dor=data.get("checkDor", True),
            suggest_story_points=data.get("suggestStoryPoints", True),
            identify_dependencies=data.get("identifyDependencies", True),
            prioritization_criteria=data.get("prioritizationCriteria", [])
        )

    def validate(self) -> List[str]:
        errors = []
        if not self.project_key:
            errors.append("projectKey is required")
        return errors


@dataclass
class RefinedIssue:
    """Issue after refinement."""
    issue_key: str
    summary: str
    current_story_points: Optional[int] = None
    suggested_story_points: Optional[int] = None
    dor_status: str = "compliant"
    missing_dor_items: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issueKey": self.issue_key,
            "summary": self.summary,
            "currentStoryPoints": self.current_story_points,
            "suggestedStoryPoints": self.suggested_story_points,
            "dorStatus": self.dor_status,
            "missingDorItems": self.missing_dor_items
        }


@dataclass
class DorViolation:
    """DoR violation."""
    issue_key: str
    missing_items: List[str]
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issueKey": self.issue_key,
            "missingItems": self.missing_items,
            "recommendation": self.recommendation
        }


@dataclass
class IssueDependency:
    """Dependency between issues."""
    from_issue: str
    to_issue: str
    dependency_type: DependencyType

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fromIssue": self.from_issue,
            "toIssue": self.to_issue,
            "dependencyType": self.dependency_type.value
        }


@dataclass
class BacklogRefinementData:
    """Backlog refinement result data."""
    refined_issues: List[RefinedIssue]
    dor_violations: List[DorViolation]
    dependencies: List[IssueDependency]
    prioritized_backlog: List[str]
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "refinedIssues": [i.to_dict() for i in self.refined_issues],
            "dorViolations": [v.to_dict() for v in self.dor_violations],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "prioritizedBacklog": self.prioritized_backlog,
            "recommendations": self.recommendations
        }


# === Standup Analysis ===

@dataclass
class StandupAnalysisRequest:
    """Request to analyze standup."""
    project_key: str
    sprint_id: Optional[str] = None
    stale_threshold_hours: int = 24
    wip_limit_per_person: int = 2

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StandupAnalysisRequest":
        return cls(
            project_key=data.get("projectKey", ""),
            sprint_id=data.get("sprintId"),
            stale_threshold_hours=data.get("staleThresholdHours", 24),
            wip_limit_per_person=data.get("wipLimitPerPerson", 2)
        )

    def validate(self) -> List[str]:
        errors = []
        if not self.project_key:
            errors.append("projectKey is required")
        return errors


@dataclass
class StaleIssue:
    """Issue that hasn't been updated."""
    issue_key: str
    summary: str
    hours_stale: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issueKey": self.issue_key,
            "summary": self.summary,
            "hoursStale": self.hours_stale
        }


@dataclass
class TeamMemberStatus:
    """Team member status."""
    name: str
    wip_count: int
    wip_issues: List[str]
    stale_issues: List[StaleIssue]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "wipCount": self.wip_count,
            "wipIssues": self.wip_issues,
            "staleIssues": [s.to_dict() for s in self.stale_issues]
        }


@dataclass
class PotentialBlocker:
    """Potential blocker issue."""
    issue_key: str
    summary: str
    assignee: str
    last_update: str
    hours_stale: int
    suggested_action: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issueKey": self.issue_key,
            "summary": self.summary,
            "assignee": self.assignee,
            "lastUpdate": self.last_update,
            "hoursStale": self.hours_stale,
            "suggestedAction": self.suggested_action
        }


@dataclass
class WipViolation:
    """WIP limit violation."""
    member: str
    current_wip: int
    limit: int
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "member": self.member,
            "currentWip": self.current_wip,
            "limit": self.limit,
            "recommendation": self.recommendation
        }


@dataclass
class StandupAnalysisData:
    """Standup analysis result data."""
    analysis_date: str
    sprint_id: str
    sprint_name: str
    team_members: List[TeamMemberStatus]
    potential_blockers: List[PotentialBlocker]
    wip_violations: List[WipViolation]
    facilitation_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysisDate": self.analysis_date,
            "sprintId": self.sprint_id,
            "sprintName": self.sprint_name,
            "teamMembers": [m.to_dict() for m in self.team_members],
            "potentialBlockers": [b.to_dict() for b in self.potential_blockers],
            "wipViolations": [v.to_dict() for v in self.wip_violations],
            "facilitationNotes": self.facilitation_notes
        }


# === Decision Log ===

@dataclass
class Alternative:
    """Decision alternative."""
    name: str
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Alternative":
        return cls(
            name=data.get("name", ""),
            pros=data.get("pros", []),
            cons=data.get("cons", [])
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "pros": self.pros,
            "cons": self.cons
        }


@dataclass
class Decision:
    """Decision details."""
    title: str
    context: str
    chosen_alternative: str
    rationale: str
    alternatives: List[Alternative] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)
    related_issues: List[str] = field(default_factory=list)
    participants: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Decision":
        return cls(
            title=data.get("title", ""),
            context=data.get("context", ""),
            chosen_alternative=data.get("chosenAlternative", ""),
            rationale=data.get("rationale", ""),
            alternatives=[Alternative.from_dict(a) for a in data.get("alternatives", [])],
            consequences=data.get("consequences", []),
            related_issues=data.get("relatedIssues", []),
            participants=data.get("participants", [])
        )


@dataclass
class DecisionLogRequest:
    """Request to create decision log entry."""
    project_key: str
    confluence_space_key: str
    decision: Decision

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionLogRequest":
        return cls(
            project_key=data.get("projectKey", ""),
            confluence_space_key=data.get("confluenceSpaceKey", ""),
            decision=Decision.from_dict(data.get("decision", {}))
        )

    def validate(self) -> List[str]:
        errors = []
        if not self.project_key:
            errors.append("projectKey is required")
        if not self.confluence_space_key:
            errors.append("confluenceSpaceKey is required")
        if not self.decision.title:
            errors.append("decision.title is required")
        if not self.decision.context:
            errors.append("decision.context is required")
        if not self.decision.chosen_alternative:
            errors.append("decision.chosenAlternative is required")
        if not self.decision.rationale:
            errors.append("decision.rationale is required")
        return errors


@dataclass
class DecisionLogData:
    """Decision log creation result."""
    decision_id: str
    title: str
    confluence_page_id: str
    confluence_page_url: str
    linked_issues: List[str]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decisionId": self.decision_id,
            "title": self.title,
            "confluencePageId": self.confluence_page_id,
            "confluencePageUrl": self.confluence_page_url,
            "linkedIssues": self.linked_issues,
            "createdAt": self.created_at
        }


# === Agent Query ===

@dataclass
class QueryContext:
    """Context for agent query."""
    sprint_id: Optional[str] = None
    include_history: bool = False
    sprint_count: int = 1

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryContext":
        if not data:
            return cls()
        return cls(
            sprint_id=data.get("sprintId"),
            include_history=data.get("includeHistory", False),
            sprint_count=data.get("sprintCount", 1)
        )


@dataclass
class AgentQueryRequest:
    """Request for agent query."""
    query: str
    project_key: str
    context: Optional[QueryContext] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentQueryRequest":
        # Support both "query" and "message" as field names
        query_value = data.get("query") or data.get("message", "")
        # Use "VSM" as default project key if not provided
        project_key_value = data.get("projectKey") or data.get("project_key", "VSM")
        
        return cls(
            query=query_value,
            project_key=project_key_value,
            context=QueryContext.from_dict(data.get("context", {}))
        )

    def validate(self) -> List[str]:
        errors = []
        if not self.query:
            errors.append("query (or message) is required")
        # projectKey is now optional with default "VSM"
        return errors


@dataclass
class DataSource:
    """Data source reference."""
    source_type: str
    reference: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.source_type,
            "reference": self.reference
        }


@dataclass
class AgentQueryData:
    """Agent query result data."""
    query_type: QueryType
    answer: str
    structured_data: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    sources: List[DataSource] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "queryType": self.query_type.value,
            "answer": self.answer,
            "structuredData": self.structured_data,
            "recommendations": self.recommendations,
            "sources": [s.to_dict() for s in self.sources]
        }


# === Error Response ===

@dataclass
class ErrorDetails:
    """Error details."""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentError:
    """Agent error."""
    code: ErrorCode
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details
        }


# === Response Wrappers ===

@dataclass
class AgentResponse:
    """Generic agent response wrapper."""
    trace_id: str
    correlation_id: str
    orchestrator_metadata: OrchestratorMetadata
    data: Any

    def to_dict(self) -> Dict[str, Any]:
        data_dict = self.data
        if hasattr(self.data, 'to_dict'):
            data_dict = self.data.to_dict()
        
        return {
            "traceId": self.trace_id,
            "correlationId": self.correlation_id,
            "orchestratorMetadata": self.orchestrator_metadata.to_dict(),
            "data": data_dict
        }


@dataclass
class ErrorResponse:
    """Error response wrapper."""
    error: AgentError
    trace_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.error.to_dict(),
            "traceId": self.trace_id
        }


# === Agent Invocation (Main Entry Point) ===

@dataclass
class ConversationMessage:
    """Mensaje en el historial de conversación."""
    role: ConversationRole
    content: str
    timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp or current_iso_timestamp()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMessage":
        return cls(
            role=ConversationRole(data.get("role", "user")),
            content=data.get("content", ""),
            timestamp=data.get("timestamp")
        )


@dataclass
class AgentInvokeRequest:
    """
    Request principal para invocar al agente.
    Este es el punto de entrada principal del agente orquestador.
    """
    # Mensaje del usuario
    message: str
    
    # Contexto del proyecto
    project_key: str
    
    # ID de sesión para mantener contexto de conversación
    session_id: Optional[str] = None
    
    # Historial de conversación (opcional, para contexto)
    conversation_history: List[ConversationMessage] = field(default_factory=list)
    
    # Contexto adicional
    context: Optional[Dict[str, Any]] = None
    
    # Opciones de ejecución
    options: Optional[Dict[str, Any]] = None
    
    def validate(self) -> List[str]:
        errors = []
        if not self.message:
            errors.append("message is required")
        if not self.project_key:
            errors.append("projectKey is required")
        if len(self.message) > 5000:
            errors.append("message exceeds maximum length of 5000 characters")
        return errors
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentInvokeRequest":
        history = []
        for msg in data.get("conversationHistory", []):
            history.append(ConversationMessage.from_dict(msg))
        
        return cls(
            message=data.get("message", ""),
            project_key=data.get("projectKey", ""),
            session_id=data.get("sessionId"),
            conversation_history=history,
            context=data.get("context"),
            options=data.get("options")
        )


@dataclass
class ChatRequest:
    """Simple chat request - solo requiere el mensaje."""
    message: str
    project_key: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatRequest":
        return cls(
            message=data.get("message", ""),
            project_key=data.get("projectKey") or data.get("project_key", "VSM")
        )
    
    def validate(self) -> List[str]:
        errors = []
        if not self.message:
            errors.append("message is required")
        if len(self.message) > 5000:
            errors.append("message exceeds maximum length of 5000 characters")
        return errors


@dataclass
class MCPCallSummary:
    """Resumen de una llamada a un MCP."""
    mcp_type: MCPType
    operation: str
    description: str
    success: bool
    data_retrieved: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "mcpType": self.mcp_type.value,
            "operation": self.operation,
            "description": self.description,
            "success": self.success
        }
        if self.data_retrieved:
            result["dataRetrieved"] = self.data_retrieved
        return result


@dataclass
class AgentAction:
    """Acción ejecutada por el agente."""
    action_type: str
    description: str
    status: str  # "completed", "pending", "failed"
    result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "actionType": self.action_type,
            "description": self.description,
            "status": self.status
        }
        if self.result:
            result["result"] = self.result
        return result


@dataclass
class AgentInvokeData:
    """
    Respuesta del agente a una invocación.
    Contiene la respuesta conversacional y los datos estructurados.
    """
    # Respuesta en lenguaje natural
    response: str
    
    # Intención detectada
    intent: AgentIntent
    
    # Confianza en la detección de intención
    intent_confidence: float
    
    # Resumen de llamadas a MCPs realizadas
    mcp_calls_summary: List[MCPCallSummary] = field(default_factory=list)
    
    # Acciones ejecutadas
    actions_taken: List[AgentAction] = field(default_factory=list)
    
    # Datos estructurados (resultado de las consultas)
    structured_data: Optional[Dict[str, Any]] = None
    
    # Sugerencias de follow-up
    suggested_followups: List[str] = field(default_factory=list)
    
    # Referencias a datos consultados
    data_sources: List[DataSource] = field(default_factory=list)
    
    # Advertencias o notas
    warnings: List[str] = field(default_factory=list)
    
    # ID de sesión para continuidad
    session_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "response": self.response,
            "intent": self.intent.value,
            "intentConfidence": self.intent_confidence,
            "mcpCallsSummary": [c.to_dict() for c in self.mcp_calls_summary],
            "actionsTaken": [a.to_dict() for a in self.actions_taken],
            "structuredData": self.structured_data,
            "suggestedFollowups": self.suggested_followups,
            "dataSources": [s.to_dict() for s in self.data_sources],
            "warnings": self.warnings,
            "sessionId": self.session_id
        }


# === Utility Functions ===

def generate_trace_id() -> str:
    """Generate a new trace ID."""
    return str(uuid.uuid4())


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def current_iso_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().isoformat() + "Z"

