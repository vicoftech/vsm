"""
Mock Jira MCP Service.
Simulates invocations to the Jira MCP for orchestrator testing.
Designed for future Bedrock Agent Action Group compatibility.

Now supports dynamic mocks from DynamoDB when MOCK_MODE is enabled.
"""

import random
import time
from typing import Dict, Any, List, Optional, Tuple

from models.schemas import (
    MCPInvocationTrace,
    MCPType,
    SprintIssue,
    SprintMetrics,
    SprintState,
    BlockerIssue,
    StaleIssue,
    TeamMemberStatus,
    RefinedIssue,
    IssueDependency,
    DependencyType,
)

from services.mock_store import MockStoreService, is_mock_mode_enabled


class JiraMCPService:
    """
    Mock Jira MCP Service.
    
    Simulates the following Jira MCP operations:
    - search_issues: Search for issues using JQL
    - get_issue: Get issue details
    - create_sprint: Create a new sprint
    - add_to_sprint: Add issues to sprint
    - start_sprint: Start a sprint
    - complete_sprint: Complete a sprint
    - get_sprint: Get sprint details
    - get_sprints: Get all sprints for a board
    - transition_issue: Transition issue status
    
    When MOCK_MODE is enabled, checks DynamoDB for custom mock responses first.
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._traces: List[MCPInvocationTrace] = []
        self._mock_store = MockStoreService(tenant_id) if is_mock_mode_enabled() else None

    def get_traces(self) -> List[MCPInvocationTrace]:
        """Get all MCP invocation traces."""
        return self._traces

    def clear_traces(self) -> None:
        """Clear invocation traces."""
        self._traces = []

    def _simulate_latency(self) -> int:
        """Simulate network latency (50-300ms)."""
        latency = random.randint(50, 300)
        time.sleep(latency / 1000)
        return latency

    def _record_trace(self, operation: str, duration_ms: int, success: bool = True,
                      error_code: Optional[str] = None, error_message: Optional[str] = None,
                      from_mock: bool = False) -> None:
        """Record an MCP invocation trace."""
        trace = MCPInvocationTrace(
            mcp_type=MCPType.JIRA,
            operation=operation + (" [MOCK]" if from_mock else ""),
            duration_ms=duration_ms,
            success=success,
            error_code=error_code,
            error_message=error_message
        )
        self._traces.append(trace)

    def _check_mock(self, operation: str, params: Dict[str, Any]) -> Optional[Any]:
        """Check if there's a matching mock in the store."""
        if self._mock_store:
            mock = self._mock_store.find_matching_mock("jira", operation, params)
            if mock:
                return mock.response
        return None

    def search_issues(self, project_key: str, jql: Optional[str] = None,
                      max_results: int = 50) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search for issues using JQL.
        
        Returns mock issues for the project.
        """
        params = {"projectKey": project_key, "jql": jql, "maxResults": max_results}
        
        # Check for custom mock first
        mock_response = self._check_mock("search_issues", params)
        if mock_response is not None:
            latency = random.randint(10, 50)  # Faster for mocks
            self._record_trace("search_issues", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("search_issues", latency)

        # Mock issues data
        mock_issues = [
            {
                "key": f"{project_key}-101",
                "summary": "Implementar dashboard de métricas",
                "status": "To Do",
                "storyPoints": 8,
                "assignee": "john.doe@example.com",
                "type": "Story",
                "hasAcceptanceCriteria": True,
                "updated": "2026-02-23T15:30:00Z"
            },
            {
                "key": f"{project_key}-102",
                "summary": "API de exportación de reportes",
                "status": "To Do",
                "storyPoints": 5,
                "assignee": "jane.smith@example.com",
                "type": "Story",
                "hasAcceptanceCriteria": True,
                "updated": "2026-02-23T14:00:00Z"
            },
            {
                "key": f"{project_key}-103",
                "summary": "Integración con Slack",
                "status": "To Do",
                "storyPoints": 3,
                "assignee": "john.doe@example.com",
                "type": "Story",
                "hasAcceptanceCriteria": True,
                "updated": "2026-02-23T12:00:00Z"
            },
            {
                "key": f"{project_key}-104",
                "summary": "Refactorizar módulo de autenticación",
                "status": "To Do",
                "storyPoints": None,
                "assignee": None,
                "type": "Story",
                "hasAcceptanceCriteria": False,
                "updated": "2026-02-20T10:00:00Z"
            },
            {
                "key": f"{project_key}-105",
                "summary": "Corregir bug en formulario de login",
                "status": "In Progress",
                "storyPoints": 2,
                "assignee": "john.doe@example.com",
                "type": "Bug",
                "hasAcceptanceCriteria": True,
                "updated": "2026-02-24T08:00:00Z"
            },
            {
                "key": f"{project_key}-106",
                "summary": "Optimizar queries de base de datos",
                "status": "In Progress",
                "storyPoints": 5,
                "assignee": "jane.smith@example.com",
                "type": "Task",
                "hasAcceptanceCriteria": True,
                "updated": "2026-02-24T07:30:00Z"
            },
            {
                "key": f"{project_key}-107",
                "summary": "Refactor authentication module",
                "status": "In Progress",
                "storyPoints": 8,
                "assignee": "jane.smith@example.com",
                "type": "Story",
                "hasAcceptanceCriteria": True,
                "updated": "2026-02-22T21:00:00Z"
            },
            {
                "key": f"{project_key}-108",
                "summary": "Waiting for API credentials",
                "status": "In Progress",
                "storyPoints": 3,
                "assignee": "john.doe@example.com",
                "type": "Story",
                "hasAcceptanceCriteria": True,
                "updated": "2026-02-22T10:00:00Z",
                "blocked": True
            },
            {
                "key": f"{project_key}-109",
                "summary": "Setup CI/CD pipeline",
                "status": "In Progress",
                "storyPoints": 5,
                "assignee": "jane.smith@example.com",
                "type": "Task",
                "hasAcceptanceCriteria": True,
                "updated": "2026-02-24T06:00:00Z"
            },
            {
                "key": f"{project_key}-110",
                "summary": "Documentar API REST",
                "status": "Done",
                "storyPoints": 3,
                "assignee": "john.doe@example.com",
                "type": "Task",
                "hasAcceptanceCriteria": True,
                "updated": "2026-02-23T18:00:00Z"
            },
            {
                "key": f"{project_key}-111",
                "summary": "Implementar tests unitarios",
                "status": "Done",
                "storyPoints": 5,
                "assignee": "jane.smith@example.com",
                "type": "Story",
                "hasAcceptanceCriteria": True,
                "updated": "2026-02-23T16:00:00Z"
            }
        ]

        return mock_issues[:max_results], latency

    def get_issue(self, issue_key: str) -> Tuple[Dict[str, Any], int]:
        """Get issue details by key."""
        params = {"issueKey": issue_key}
        
        mock_response = self._check_mock("get_issue", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("get_issue", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("get_issue", latency)

        # Extract project key from issue key
        parts = issue_key.split("-")
        project_key = parts[0] if parts else "VSM"

        return {
            "key": issue_key,
            "summary": f"Issue {issue_key}",
            "description": "Detailed description of the issue...",
            "status": "To Do",
            "storyPoints": 5,
            "assignee": "john.doe@example.com",
            "reporter": "pm@example.com",
            "type": "Story",
            "priority": "Medium",
            "labels": ["backend", "api"],
            "components": ["Core"],
            "created": "2026-02-20T10:00:00Z",
            "updated": "2026-02-23T15:30:00Z",
            "hasAcceptanceCriteria": True,
            "acceptanceCriteria": [
                "AC1: User can view the dashboard",
                "AC2: Dashboard shows real-time data",
                "AC3: Dashboard is responsive"
            ]
        }, latency

    def create_sprint(self, board_id: str, name: str, start_date: str,
                      end_date: str, goal: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
        """Create a new sprint."""
        params = {"boardId": board_id, "name": name, "startDate": start_date, 
                  "endDate": end_date, "goal": goal}
        
        mock_response = self._check_mock("create_sprint", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("create_sprint", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("create_sprint", latency)

        sprint_id = str(random.randint(400, 500))

        return {
            "id": sprint_id,
            "name": name,
            "state": "future",
            "startDate": start_date,
            "endDate": end_date,
            "goal": goal,
            "boardId": board_id
        }, latency

    def add_to_sprint(self, sprint_id: str, issue_keys: List[str]) -> Tuple[Dict[str, Any], int]:
        """Add issues to a sprint."""
        params = {"sprintId": sprint_id, "issueKeys": issue_keys}
        
        mock_response = self._check_mock("add_to_sprint", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("add_to_sprint", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("add_to_sprint", latency)

        return {
            "sprintId": sprint_id,
            "addedIssues": issue_keys,
            "count": len(issue_keys)
        }, latency

    def start_sprint(self, sprint_id: str) -> Tuple[Dict[str, Any], int]:
        """Start a sprint."""
        params = {"sprintId": sprint_id}
        
        mock_response = self._check_mock("start_sprint", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("start_sprint", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("start_sprint", latency)

        return {
            "sprintId": sprint_id,
            "state": "active",
            "started": True
        }, latency

    def complete_sprint(self, sprint_id: str) -> Tuple[Dict[str, Any], int]:
        """Complete a sprint."""
        params = {"sprintId": sprint_id}
        
        mock_response = self._check_mock("complete_sprint", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("complete_sprint", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("complete_sprint", latency)

        return {
            "sprintId": sprint_id,
            "state": "closed",
            "completed": True
        }, latency

    def get_sprint(self, sprint_id: str) -> Tuple[Dict[str, Any], int]:
        """Get sprint details."""
        params = {"sprintId": sprint_id}
        
        mock_response = self._check_mock("get_sprint", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("get_sprint", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("get_sprint", latency)

        return {
            "id": sprint_id,
            "name": f"Sprint {sprint_id[-2:]}",
            "state": "active",
            "startDate": "2026-02-24",
            "endDate": "2026-03-09",
            "goal": "Complete MVP of reporting module",
            "boardId": "123"
        }, latency

    def get_sprints(self, board_id: str, state: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int]:
        """Get all sprints for a board."""
        params = {"boardId": board_id, "state": state}
        
        mock_response = self._check_mock("get_sprints", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("get_sprints", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("get_sprints", latency)

        sprints = [
            {
                "id": "456",
                "name": "Sprint 15",
                "state": "active",
                "startDate": "2026-02-24",
                "endDate": "2026-03-09",
                "goal": "Complete MVP of reporting module",
                "velocity": None
            },
            {
                "id": "455",
                "name": "Sprint 14",
                "state": "closed",
                "startDate": "2026-02-10",
                "endDate": "2026-02-23",
                "goal": "Authentication and authorization",
                "velocity": 32
            },
            {
                "id": "454",
                "name": "Sprint 13",
                "state": "closed",
                "startDate": "2026-01-27",
                "endDate": "2026-02-09",
                "goal": "Core API implementation",
                "velocity": 28
            },
            {
                "id": "453",
                "name": "Sprint 12",
                "state": "closed",
                "startDate": "2026-01-13",
                "endDate": "2026-01-26",
                "goal": "Database and models",
                "velocity": 35
            }
        ]

        if state:
            sprints = [s for s in sprints if s["state"] == state]

        return sprints, latency

    def get_sprint_issues(self, sprint_id: str) -> Tuple[List[Dict[str, Any]], int]:
        """Get all issues in a sprint."""
        params = {"sprintId": sprint_id}
        
        mock_response = self._check_mock("get_sprint_issues", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("search_issues", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("search_issues", latency)

        # Return mock sprint issues
        return [
            {
                "key": "VSM-101",
                "summary": "Implementar dashboard de métricas",
                "status": "To Do",
                "storyPoints": 8,
                "assignee": "john.doe@example.com"
            },
            {
                "key": "VSM-102",
                "summary": "API de exportación de reportes",
                "status": "In Progress",
                "storyPoints": 5,
                "assignee": "jane.smith@example.com"
            },
            {
                "key": "VSM-103",
                "summary": "Integración con Slack",
                "status": "Done",
                "storyPoints": 3,
                "assignee": "john.doe@example.com"
            },
            {
                "key": "VSM-105",
                "summary": "Corregir bug en login",
                "status": "Done",
                "storyPoints": 2,
                "assignee": "john.doe@example.com"
            },
            {
                "key": "VSM-106",
                "summary": "Optimizar queries",
                "status": "In Progress",
                "storyPoints": 5,
                "assignee": "jane.smith@example.com"
            },
            {
                "key": "VSM-107",
                "summary": "Refactor auth module",
                "status": "In Progress",
                "storyPoints": 8,
                "assignee": "jane.smith@example.com"
            },
            {
                "key": "VSM-108",
                "summary": "API credentials setup",
                "status": "In Progress",
                "storyPoints": 3,
                "assignee": "john.doe@example.com"
            }
        ], latency

    def link_issues(self, from_key: str, to_key: str, link_type: str) -> Tuple[Dict[str, Any], int]:
        """Link two issues."""
        params = {"fromKey": from_key, "toKey": to_key, "linkType": link_type}
        
        mock_response = self._check_mock("link_issues", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("link_issues", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("link_issues", latency)

        return {
            "fromIssue": from_key,
            "toIssue": to_key,
            "linkType": link_type,
            "created": True
        }, latency

    # === Helper Methods for Orchestrator ===

    def get_backlog_issues(self, project_key: str, limit: int = 10) -> List[SprintIssue]:
        """Get backlog issues ready for refinement."""
        issues_data, _ = self.search_issues(project_key, max_results=limit)
        
        result = []
        for issue in issues_data:
            if issue.get("status") == "To Do":
                result.append(SprintIssue(
                    issue_key=issue["key"],
                    summary=issue["summary"],
                    story_points=issue.get("storyPoints") or 0,
                    dor_compliant=issue.get("hasAcceptanceCriteria", False) and issue.get("storyPoints") is not None,
                    status=issue["status"]
                ))
        
        return result[:limit]

    def get_sprint_metrics(self, sprint_id: str) -> SprintMetrics:
        """Calculate sprint metrics."""
        issues, _ = self.get_sprint_issues(sprint_id)
        
        completed = [i for i in issues if i["status"] == "Done"]
        velocity = sum(i.get("storyPoints", 0) or 0 for i in completed)
        planned = sum(i.get("storyPoints", 0) or 0 for i in issues)
        
        return SprintMetrics(
            velocity=velocity,
            planned_points=planned,
            say_do_ratio=round(velocity / planned, 2) if planned > 0 else 0.0,
            average_cycle_time=18.5,  # Mock value
            throughput=len(completed)
        )

    def get_blockers(self, project_key: str) -> List[BlockerIssue]:
        """Get blocked issues."""
        issues, _ = self.search_issues(project_key)
        
        blockers = []
        for issue in issues:
            if issue.get("blocked") or (issue.get("status") == "In Progress" and "2026-02-22" in issue.get("updated", "")):
                blockers.append(BlockerIssue(
                    issue_key=issue["key"],
                    summary=issue["summary"],
                    blocked_days=2,
                    assignee=issue.get("assignee", "unassigned")
                ))
        
        return blockers

    def get_team_wip_status(self, project_key: str) -> List[TeamMemberStatus]:
        """Get WIP status by team member."""
        issues, _ = self.search_issues(project_key)
        
        # Group by assignee
        by_assignee: Dict[str, List[Dict]] = {}
        for issue in issues:
            assignee = issue.get("assignee")
            if assignee and issue.get("status") == "In Progress":
                if assignee not in by_assignee:
                    by_assignee[assignee] = []
                by_assignee[assignee].append(issue)
        
        result = []
        for assignee, assignee_issues in by_assignee.items():
            wip_issues = [i["key"] for i in assignee_issues]
            stale_issues = []
            
            for issue in assignee_issues:
                updated = issue.get("updated", "")
                if "2026-02-22" in updated or "2026-02-21" in updated:
                    stale_issues.append(StaleIssue(
                        issue_key=issue["key"],
                        summary=issue["summary"],
                        hours_stale=36
                    ))
            
            result.append(TeamMemberStatus(
                name=assignee,
                wip_count=len(wip_issues),
                wip_issues=wip_issues,
                stale_issues=stale_issues
            ))
        
        return result

    def get_refined_issues(self, project_key: str, limit: int = 10) -> List[RefinedIssue]:
        """Get issues with refinement analysis."""
        issues, _ = self.search_issues(project_key, max_results=limit)
        
        result = []
        for issue in issues:
            if issue.get("status") == "To Do":
                missing_items = []
                if not issue.get("hasAcceptanceCriteria"):
                    missing_items.append("acceptance_criteria")
                if issue.get("storyPoints") is None:
                    missing_items.append("story_points")
                
                result.append(RefinedIssue(
                    issue_key=issue["key"],
                    summary=issue["summary"],
                    current_story_points=issue.get("storyPoints"),
                    suggested_story_points=issue.get("storyPoints") or 5,
                    dor_status="compliant" if not missing_items else "non_compliant",
                    missing_dor_items=missing_items
                ))
        
        return result[:limit]

    def detect_dependencies(self, project_key: str) -> List[IssueDependency]:
        """Detect dependencies between issues."""
        # Mock dependencies
        return [
            IssueDependency(
                from_issue=f"{project_key}-102",
                to_issue=f"{project_key}-101",
                dependency_type=DependencyType.BLOCKS
            ),
            IssueDependency(
                from_issue=f"{project_key}-103",
                to_issue=f"{project_key}-102",
                dependency_type=DependencyType.RELATES_TO
            )
        ]
