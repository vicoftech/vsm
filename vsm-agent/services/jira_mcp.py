"""
Jira MCP Service.
Can operate in two modes:
1. Mock mode: Simulates Jira MCP operations (default)
2. Real mode: Invokes the vsm-mcp-jira Lambda function

Designed for future Bedrock Agent Action Group compatibility.
"""

import json
import logging
import os
import random
import time
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger()

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

# Try to import boto3 for Lambda invocation
try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class JiraMCPService:
    """
    Jira MCP Service.
    
    Supports two modes:
    1. Mock mode (MOCK_MODE=true): Simulates Jira operations
    2. Real mode (MOCK_MODE=false): Invokes vsm-mcp-jira Lambda
    
    Operations:
    - search_issues: Search for issues using JQL
    - get_issue: Get issue details
    - get_projects: Get all projects
    - create_sprint: Create a new sprint
    - add_to_sprint: Add issues to sprint
    - start_sprint: Start a sprint
    - complete_sprint: Complete a sprint
    - get_sprint: Get sprint details
    - get_sprints: Get all sprints for a board
    - transition_issue: Transition issue status
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._traces: List[MCPInvocationTrace] = []
        self._mock_mode = is_mock_mode_enabled()
        self._mock_store = MockStoreService(tenant_id) if self._mock_mode else None
        self._lambda_client = None
        self._jira_lambda_name = os.environ.get("JIRA_MCP_LAMBDA_NAME", "vsm-mcp-jira-dev")

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

    @property
    def lambda_client(self):
        """Lazy initialization of Lambda client."""
        if self._lambda_client is None and BOTO3_AVAILABLE:
            self._lambda_client = boto3.client("lambda")
        return self._lambda_client

    def _invoke_lambda_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke a tool on the vsm-mcp-jira Lambda.
        
        Args:
            tool_name: Name of the tool to invoke
            params: Parameters for the tool
            
        Returns:
            Result from the tool execution
        """
        if not self.lambda_client:
            raise RuntimeError("boto3 not available - cannot invoke Lambda")
        
        start_time = time.time()
        
        try:
            # Prepare the payload for the Lambda
            payload = {
                "requestContext": {
                    "http": {
                        "method": "POST",
                        "path": "/tool"
                    }
                },
                "body": json.dumps({
                    "tool": tool_name,
                    "params": params
                })
            }
            
            # Invoke the Lambda
            response = self.lambda_client.invoke(
                FunctionName=self._jira_lambda_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload)
            )
            
            # Parse response
            response_payload = json.loads(response["Payload"].read())
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Check for errors
            if response.get("FunctionError"):
                error_message = response_payload.get("errorMessage", "Unknown error")
                self._record_trace(
                    tool_name,
                    latency_ms,
                    success=False,
                    error_code="LAMBDA_ERROR",
                    error_message=error_message
                )
                raise RuntimeError(f"Lambda error: {error_message}")
            
            # Parse the response body
            status_code = response_payload.get("statusCode", 200)
            body_str = response_payload.get("body", "{}")
            
            if isinstance(body_str, str):
                body = json.loads(body_str)
            else:
                body = body_str
            
            if status_code != 200:
                error_msg = body.get("error", {}).get("message", "Unknown error")
                self._record_trace(
                    tool_name,
                    latency_ms,
                    success=False,
                    error_code=f"HTTP_{status_code}",
                    error_message=error_msg
                )
                raise RuntimeError(f"Tool execution failed: {error_msg}")
            
            # Extract result
            if body.get("success"):
                result = body.get("result", {})
                # Ensure result is a dict, not a string
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except json.JSONDecodeError:
                        # If it's not JSON, wrap it in a dict
                        result = {"data": result}
                elif not isinstance(result, dict):
                    # If it's not a dict or string, wrap it
                    result = {"data": result}
                self._record_trace(tool_name, latency_ms, success=True)
                return result
            else:
                error_msg = body.get("error", "Unknown error")
                self._record_trace(
                    tool_name,
                    latency_ms,
                    success=False,
                    error_code="TOOL_ERROR",
                    error_message=str(error_msg)
                )
                raise RuntimeError(f"Tool returned error: {error_msg}")
                
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            self._record_trace(
                tool_name,
                latency_ms,
                success=False,
                error_code="INVOCATION_ERROR",
                error_message=str(e)
            )
            raise

    def search_issues(self, project_key: str, jql: Optional[str] = None,
                      max_results: int = 50) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search for issues using JQL.
        
        In mock mode: Returns simulated issues
        In real mode: Invokes vsm-mcp-jira Lambda search_issues tool
        """
        # Build JQL query
        if jql:
            query = jql
        else:
            query = f"project = {project_key}"
        
        params = {"projectKey": project_key, "jql": jql, "maxResults": max_results}
        
        # Real mode: Invoke Lambda
        if not self._mock_mode:
            try:
                result = self._invoke_lambda_tool("search_issues", {
                    "jql": query,
                    "max_results": max_results
                })
                
                # Extract issues from result
                issues = result.get("issues", [])
                total = result.get("total", len(issues))
                
                # Get latency from trace
                traces = self.get_traces()
                latency = traces[-1].duration_ms if traces else 0
                
                return issues, latency
            except Exception as e:
                # Fallback to mock on error
                logger.warning(f"Lambda invocation failed, falling back to mock: {e}")
                # Continue to mock mode below
        
        # Mock mode: Check for custom mock first
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
        """
        Get all sprints for a board.
        
        In mock mode: Returns simulated sprints
        In real mode: Invokes vsm-mcp-jira Lambda get_sprints tool
        """
        # Convert board_id to int if it's a string
        try:
            board_id_int = int(board_id) if isinstance(board_id, str) else board_id
        except ValueError:
            board_id_int = board_id
        
        params = {"boardId": board_id, "state": state}
        
        # Real mode: Invoke Lambda
        if not self._mock_mode:
            try:
                lambda_params = {
                    "board_id": board_id_int,
                    "max_results": 50
                }
                if state:
                    lambda_params["state"] = state
                
                result = self._invoke_lambda_tool("get_sprints", lambda_params)
                
                # Extract sprints from result
                sprints = result.get("values", []) if isinstance(result, dict) else result
                
                # Get latency from trace
                traces = self.get_traces()
                latency = traces[-1].duration_ms if traces else 0
                
                return sprints, latency
            except Exception as e:
                # Fallback to mock on error
                logger.warning(f"Lambda invocation failed, falling back to mock: {e}")
                # Continue to mock mode below
        
        # Mock mode: Check for custom mock first
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

    def get_projects(self) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get all active projects.
        
        In mock mode: Returns simulated projects
        In real mode: Invokes vsm-mcp-jira Lambda get_projects tool
        
        Returns:
            Tuple of (list of projects, latency_ms)
        """
        params = {}
        
        # Real mode: Invoke Lambda
        if not self._mock_mode:
            try:
                result = self._invoke_lambda_tool("get_projects", {})
                
                # Get latency from trace
                traces = self.get_traces()
                latency = traces[-1].duration_ms if traces else 0
                
                # Result is already a list of projects
                projects = result if isinstance(result, list) else result.get("values", [])
                
                return projects, latency
            except Exception as e:
                # Fallback to mock on error
                logger.warning(f"Lambda invocation failed, falling back to mock: {e}")
                # Continue to mock mode below
        
        # Mock mode: Check for custom mock first
        mock_response = self._check_mock("get_projects", params)
        if mock_response is not None:
            latency = self._simulate_latency()
            self._record_trace("getProjects", latency, from_mock=True)
            return mock_response, latency
        
        # Default mock projects
        latency = self._simulate_latency()
        
        projects = [
            {
                "key": "VSM",
                "name": "Virtual Scrum Manager",
                "projectTypeKey": "software",
                "lead": "scrum-master@example.com",
                "active": True
            },
            {
                "key": "PROJ",
                "name": "Sample Project",
                "projectTypeKey": "software",
                "lead": "pm@example.com",
                "active": True
            },
            {
                "key": "DEV",
                "name": "Development Project",
                "projectTypeKey": "software",
                "lead": "tech-lead@example.com",
                "active": True
            },
            {
                "key": "QA",
                "name": "Quality Assurance",
                "projectTypeKey": "software",
                "lead": "qa-lead@example.com",
                "active": True
            }
        ]
        
        self._record_trace("getProjects", latency, success=True)
        return projects, latency

    def create_project(
        self,
        project_key: str,
        project_name: str,
        lead_account_id: str,
        project_type: str = "software",
        description: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        Create a new project in Jira.
        
        In mock mode: Returns simulated project
        In real mode: Invokes vsm-mcp-jira Lambda create_project tool
        
        Args:
            project_key: Project key (uppercase, alphanumeric, max 10 chars)
            project_name: Project name
            lead_account_id: Lead account ID (Jira account ID, not email)
            project_type: Project type (default: "software")
            description: Optional description
            
        Returns:
            Tuple of (project_data, latency_ms)
        """
        params = {
            "key": project_key,
            "name": project_name,
            "lead": lead_account_id,
            "project_type": project_type
        }
        if description:
            params["description"] = description
        
        # Real mode: Invoke Lambda
        if not self._mock_mode:
            try:
                result = self._invoke_lambda_tool("create_project", {
                    "key": project_key,
                    "name": project_name,
                    "lead": lead_account_id,
                    "project_type": project_type,
                    "description": description
                })
                
                # Get latency from trace
                traces = self.get_traces()
                latency = traces[-1].duration_ms if traces else 0
                
                return result, latency
            except Exception as e:
                # Fallback to mock on error
                logger.warning(f"Lambda invocation failed, falling back to mock: {e}")
                # Continue to mock mode below
        
        # Mock mode: Check for custom mock first
        mock_response = self._check_mock("create_project", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("create_project", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("create_project", latency)
        
        # Mock project data
        return {
            "key": project_key,
            "id": str(random.randint(10000, 99999)),
            "name": project_name,
            "projectTypeKey": project_type,
            "lead": {
                "accountId": lead_account_id,
                "displayName": "Project Lead"
            }
        }, latency

    def create_story(
        self,
        project_key: str,
        summary: str,
        description: Optional[str] = None,
        assignee_account_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        Create a new story in Jira.
        
        In mock mode: Returns simulated story
        In real mode: Invokes vsm-mcp-jira Lambda create_story tool
        
        Args:
            project_key: Project key (e.g., "PROJ2")
            summary: Story title/summary
            description: Optional description
            assignee_account_id: Optional assignee account ID
            
        Returns:
            Tuple of (story_data, latency_ms)
        """
        params = {
            "project_key": project_key,
            "summary": summary
        }
        if description:
            params["description"] = description
        if assignee_account_id:
            params["assignee_account_id"] = assignee_account_id
        
        # Real mode: Invoke Lambda
        if not self._mock_mode:
            try:
                result = self._invoke_lambda_tool("create_story", {
                    "project_key": project_key,
                    "summary": summary,
                    "description": description,
                    "assignee_account_id": assignee_account_id
                })
                
                # Get latency from trace
                traces = self.get_traces()
                latency = traces[-1].duration_ms if traces else 0
                
                # Ensure result is a dict
                if not isinstance(result, dict):
                    if isinstance(result, str):
                        try:
                            result = json.loads(result)
                        except json.JSONDecodeError:
                            result = {"key": result, "id": result}
                    else:
                        result = {"key": str(result), "id": str(result)}
                
                return result, latency
            except Exception as e:
                # Fallback to mock on error
                logger.warning(f"Lambda invocation failed, falling back to mock: {e}")
                # Continue to mock mode below
        
        # Mock mode: Check for custom mock first
        mock_response = self._check_mock("create_story", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("create_story", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("create_story", latency)
        
        # Mock story data
        story_key = f"{project_key}-{random.randint(100, 999)}"
        return {
            "id": str(random.randint(10000, 99999)),
            "key": story_key,
            "self": f"https://example.atlassian.net/rest/api/3/issue/{story_key}",
            "fields": {
                "summary": summary,
                "description": description or "",
                "project": {"key": project_key}
            }
        }, latency

    def add_comment(self, issue_key: str, comment: str) -> Tuple[Dict[str, Any], int]:
        """
        Add a comment to a Jira issue.
        
        In mock mode: Returns simulated comment
        In real mode: Invokes vsm-mcp-jira Lambda add_comment tool
        
        Args:
            issue_key: Issue key (e.g., "PROJ2-3")
            comment: Comment text
            
        Returns:
            Tuple of (comment_data, latency_ms)
        """
        params = {
            "issue_key": issue_key,
            "comment": comment
        }
        
        # Real mode: Invoke Lambda
        if not self._mock_mode:
            try:
                result = self._invoke_lambda_tool("add_comment", {
                    "issue_key": issue_key,
                    "comment": comment
                })
                
                # Get latency from trace
                traces = self.get_traces()
                latency = traces[-1].duration_ms if traces else 0
                
                return result, latency
            except Exception as e:
                # Fallback to mock on error
                logger.warning(f"Lambda invocation failed, falling back to mock: {e}")
                # Continue to mock mode below
        
        # Mock mode: Check for custom mock first
        mock_response = self._check_mock("add_comment", params)
        if mock_response is not None:
            latency = self._simulate_latency()
            self._record_trace("add_comment", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("add_comment", latency)
        
        # Mock comment data
        return {
            "id": str(random.randint(10000, 99999)),
            "body": comment,
            "self": f"https://example.atlassian.net/rest/api/3/issue/{issue_key}/comment/{random.randint(10000, 99999)}"
        }, latency

    def set_story_points(self, issue_key: str, story_points: int) -> Tuple[Dict[str, Any], int]:
        """
        Set story points for a Jira issue.
        
        In mock mode: Returns simulated success
        In real mode: Invokes vsm-mcp-jira Lambda set_story_points tool
        
        Args:
            issue_key: Issue key (e.g., "PROJ2-3")
            story_points: Story points value (integer)
            
        Returns:
            Tuple of (result_data, latency_ms)
        """
        params = {
            "issue_key": issue_key,
            "story_points": story_points
        }
        
        # Real mode: Invoke Lambda
        if not self._mock_mode:
            try:
                result = self._invoke_lambda_tool("set_story_points", {
                    "issue_key": issue_key,
                    "story_points": story_points
                })
                
                # Get latency from trace
                traces = self.get_traces()
                latency = traces[-1].duration_ms if traces else 0
                
                return result, latency
            except Exception as e:
                # Fallback to mock on error
                logger.warning(f"Lambda invocation failed, falling back to mock: {e}")
                # Continue to mock mode below
        
        # Mock mode: Check for custom mock first
        mock_response = self._check_mock("set_story_points", params)
        if mock_response is not None:
            latency = self._simulate_latency()
            self._record_trace("set_story_points", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("set_story_points", latency)
        
        # Mock success response
        return {}, latency

    def get_transitions(self, issue_key: str) -> Tuple[Dict[str, Any], int]:
        """
        Get available transitions for a Jira issue.
        
        In mock mode: Returns simulated transitions
        In real mode: Invokes vsm-mcp-jira Lambda get_transitions tool
        
        Args:
            issue_key: Issue key (e.g., "PROJ2-3")
            
        Returns:
            Tuple of (transitions_data, latency_ms)
        """
        params = {"issue_key": issue_key}
        
        # Real mode: Invoke Lambda
        if not self._mock_mode:
            try:
                result = self._invoke_lambda_tool("get_transitions", {
                    "issue_key": issue_key
                })
                
                # Get latency from trace
                traces = self.get_traces()
                latency = traces[-1].duration_ms if traces else 0
                
                return result, latency
            except Exception as e:
                # Fallback to mock on error
                logger.warning(f"Lambda invocation failed, falling back to mock: {e}")
                # Continue to mock mode below
        
        # Mock mode: Check for custom mock first
        mock_response = self._check_mock("get_transitions", params)
        if mock_response is not None:
            latency = self._simulate_latency()
            self._record_trace("get_transitions", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("get_transitions", latency)
        
        # Mock transitions
        return {
            "transitions": [
                {"id": "11", "name": "To Do", "to": {"name": "To Do"}},
                {"id": "21", "name": "In Progress", "to": {"name": "In Progress"}},
                {"id": "31", "name": "Done", "to": {"name": "Done"}},
                {"id": "41", "name": "Finalizada", "to": {"name": "Finalizada"}},
            ]
        }, latency

    def transition_issue(self, issue_key: str, transition_id: str, comment: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
        """
        Transition a Jira issue to a new status.
        
        In mock mode: Returns simulated success
        In real mode: Invokes vsm-mcp-jira Lambda transition_issue tool
        
        Args:
            issue_key: Issue key (e.g., "PROJ2-3")
            transition_id: Transition ID (e.g., "31" for Done)
            comment: Optional comment for the transition
            
        Returns:
            Tuple of (result_data, latency_ms)
        """
        params = {
            "issue_key": issue_key,
            "transition_id": transition_id
        }
        if comment:
            params["comment"] = comment
        
        # Real mode: Invoke Lambda
        if not self._mock_mode:
            try:
                result = self._invoke_lambda_tool("transition_issue", {
                    "issue_key": issue_key,
                    "transition_id": transition_id,
                    "comment": comment
                })
                
                # Get latency from trace
                traces = self.get_traces()
                latency = traces[-1].duration_ms if traces else 0
                
                return result, latency
            except Exception as e:
                # Fallback to mock on error
                logger.warning(f"Lambda invocation failed, falling back to mock: {e}")
                # Continue to mock mode below
        
        # Mock mode: Check for custom mock first
        mock_response = self._check_mock("transition_issue", params)
        if mock_response is not None:
            latency = self._simulate_latency()
            self._record_trace("transition_issue", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("transition_issue", latency)
        
        # Mock success response
        return {}, latency

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
