"""
Mock Confluence MCP Service.
Simulates invocations to the Confluence MCP for orchestrator testing.
Designed for future Bedrock Agent Action Group compatibility.

Now supports dynamic mocks from DynamoDB when MOCK_MODE is enabled.
"""

import random
import time
from typing import Dict, Any, List, Optional, Tuple

from models.schemas import (
    MCPInvocationTrace,
    MCPType,
    Decision,
    Alternative,
)

from services.mock_store import MockStoreService, is_mock_mode_enabled


class ConfluenceMCPService:
    """
    Mock Confluence MCP Service.
    
    Simulates the following Confluence MCP operations:
    - create_page: Create a new page
    - update_page: Update an existing page
    - get_page: Get page content
    - search_pages: Search for pages
    - get_space: Get space information
    
    When MOCK_MODE is enabled, checks DynamoDB for custom mock responses first.
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._traces: List[MCPInvocationTrace] = []
        self._page_counter = 1000
        self._mock_store = MockStoreService(tenant_id) if is_mock_mode_enabled() else None

    def get_traces(self) -> List[MCPInvocationTrace]:
        """Get all MCP invocation traces."""
        return self._traces

    def clear_traces(self) -> None:
        """Clear invocation traces."""
        self._traces = []

    def _simulate_latency(self) -> int:
        """Simulate network latency (100-400ms)."""
        latency = random.randint(100, 400)
        time.sleep(latency / 1000)
        return latency

    def _record_trace(self, operation: str, duration_ms: int, success: bool = True,
                      error_code: Optional[str] = None, error_message: Optional[str] = None,
                      from_mock: bool = False) -> None:
        """Record an MCP invocation trace."""
        trace = MCPInvocationTrace(
            mcp_type=MCPType.CONFLUENCE,
            operation=operation + (" [MOCK]" if from_mock else ""),
            duration_ms=duration_ms,
            success=success,
            error_code=error_code,
            error_message=error_message
        )
        self._traces.append(trace)

    def _generate_page_id(self) -> str:
        """Generate a unique page ID."""
        self._page_counter += 1
        return str(self._page_counter)

    def _check_mock(self, operation: str, params: Dict[str, Any]) -> Optional[Any]:
        """Check if there's a matching mock in the store."""
        if self._mock_store:
            mock = self._mock_store.find_matching_mock("confluence", operation, params)
            if mock:
                return mock.response
        return None

    def create_page(self, space_key: str, title: str, content: str,
                    parent_id: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
        """
        Create a new Confluence page.
        
        Returns mock page creation result.
        """
        params = {"spaceKey": space_key, "title": title, "parentId": parent_id}
        
        mock_response = self._check_mock("create_page", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("create_page", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("create_page", latency)

        page_id = self._generate_page_id()
        
        # Generate URL based on space and title
        safe_title = title.replace(" ", "+")
        base_url = f"https://confluence.example.com/display/{space_key}/{safe_title}"

        return {
            "id": page_id,
            "title": title,
            "spaceKey": space_key,
            "version": 1,
            "url": base_url,
            "webUrl": base_url,
            "createdAt": "2026-02-24T10:00:00Z",
            "createdBy": "vsm-agent@example.com"
        }, latency

    def update_page(self, page_id: str, title: str, content: str,
                    version: int) -> Tuple[Dict[str, Any], int]:
        """
        Update an existing Confluence page.
        """
        params = {"pageId": page_id, "title": title, "version": version}
        
        mock_response = self._check_mock("update_page", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("update_page", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("update_page", latency)

        return {
            "id": page_id,
            "title": title,
            "version": version + 1,
            "updatedAt": "2026-02-24T10:30:00Z",
            "updatedBy": "vsm-agent@example.com"
        }, latency

    def get_page(self, page_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Get page content by ID.
        """
        params = {"pageId": page_id}
        
        mock_response = self._check_mock("get_page", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("get_page", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("get_page", latency)

        return {
            "id": page_id,
            "title": f"Page {page_id}",
            "spaceKey": "VSMPROJ",
            "version": 3,
            "content": "<p>Page content here...</p>",
            "url": f"https://confluence.example.com/pages/viewpage.action?pageId={page_id}",
            "createdAt": "2026-02-20T10:00:00Z",
            "updatedAt": "2026-02-24T10:30:00Z"
        }, latency

    def search_pages(self, space_key: str, query: str,
                     limit: int = 25) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search for pages in a space.
        """
        params = {"spaceKey": space_key, "query": query, "limit": limit}
        
        mock_response = self._check_mock("search_pages", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("search_pages", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("search_pages", latency)

        # Mock search results
        return [
            {
                "id": "1001",
                "title": "Project Charter",
                "spaceKey": space_key,
                "url": f"https://confluence.example.com/display/{space_key}/Project+Charter"
            },
            {
                "id": "1002",
                "title": "Decision Log",
                "spaceKey": space_key,
                "url": f"https://confluence.example.com/display/{space_key}/Decision+Log"
            },
            {
                "id": "1003",
                "title": "Sprint 14 Review",
                "spaceKey": space_key,
                "url": f"https://confluence.example.com/display/{space_key}/Sprint+14+Review"
            }
        ][:limit], latency

    def get_space(self, space_key: str) -> Tuple[Dict[str, Any], int]:
        """
        Get space information.
        """
        params = {"spaceKey": space_key}
        
        mock_response = self._check_mock("get_space", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("get_space", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("get_space", latency)

        return {
            "key": space_key,
            "name": f"{space_key} Project Space",
            "type": "global",
            "homePageId": "1000",
            "url": f"https://confluence.example.com/display/{space_key}"
        }, latency

    def add_comment(self, page_id: str, comment: str) -> Tuple[Dict[str, Any], int]:
        """
        Add a comment to a page.
        """
        params = {"pageId": page_id}
        
        mock_response = self._check_mock("add_comment", params)
        if mock_response is not None:
            latency = random.randint(10, 50)
            self._record_trace("add_comment", latency, from_mock=True)
            return mock_response, latency
        
        latency = self._simulate_latency()
        self._record_trace("add_comment", latency)

        return {
            "id": str(random.randint(5000, 6000)),
            "pageId": page_id,
            "content": comment,
            "createdAt": "2026-02-24T10:45:00Z",
            "createdBy": "vsm-agent@example.com"
        }, latency

    # === High-Level Document Creation Methods ===

    def create_sprint_planning_page(self, space_key: str, sprint_name: str,
                                    sprint_goal: str, issues: List[Dict],
                                    project_key: str) -> Tuple[Dict[str, Any], int]:
        """
        Create a Sprint Planning documentation page.
        """
        title = f"{sprint_name} Planning"
        
        # Build content
        content = f"""
        <h1>{sprint_name} Planning</h1>
        <h2>Sprint Goal</h2>
        <p>{sprint_goal}</p>
        
        <h2>Sprint Backlog</h2>
        <table>
            <thead>
                <tr>
                    <th>Issue</th>
                    <th>Summary</th>
                    <th>Story Points</th>
                    <th>Assignee</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for issue in issues:
            jira_link = f"https://jira.example.com/browse/{issue.get('issueKey', issue.get('key', ''))}"
            content += f"""
                <tr>
                    <td><a href="{jira_link}">{issue.get('issueKey', issue.get('key', ''))}</a></td>
                    <td>{issue.get('summary', '')}</td>
                    <td>{issue.get('storyPoints', 0)}</td>
                    <td>{issue.get('assignee', 'Unassigned')}</td>
                </tr>
            """
        
        content += """
            </tbody>
        </table>
        
        <h2>Links</h2>
        <ul>
            <li><a href="https://jira.example.com/secure/RapidBoard.jspa">Jira Board</a></li>
        </ul>
        """
        
        return self.create_page(space_key, title, content)

    def create_sprint_review_page(self, space_key: str, sprint_name: str,
                                  metrics: Dict, completed: List[Dict],
                                  incomplete: List[Dict]) -> Tuple[Dict[str, Any], int]:
        """
        Create a Sprint Review documentation page.
        """
        title = f"{sprint_name} Review"
        
        content = f"""
        <h1>{sprint_name} Review</h1>
        
        <h2>Sprint Metrics</h2>
        <table>
            <tr><td><strong>Velocity</strong></td><td>{metrics.get('velocity', 0)} SP</td></tr>
            <tr><td><strong>Planned Points</strong></td><td>{metrics.get('plannedPoints', 0)} SP</td></tr>
            <tr><td><strong>Say/Do Ratio</strong></td><td>{metrics.get('sayDoRatio', 0):.0%}</td></tr>
            <tr><td><strong>Throughput</strong></td><td>{metrics.get('throughput', 0)} issues</td></tr>
            <tr><td><strong>Avg Cycle Time</strong></td><td>{metrics.get('averageCycleTime', 0)} hours</td></tr>
        </table>
        
        <h2>Completed Issues ({len(completed)})</h2>
        <table>
            <thead>
                <tr><th>Issue</th><th>Summary</th><th>Story Points</th></tr>
            </thead>
            <tbody>
        """
        
        for issue in completed:
            key = issue.get('issueKey', issue.get('key', ''))
            content += f"""
                <tr>
                    <td><a href="https://jira.example.com/browse/{key}">{key}</a></td>
                    <td>{issue.get('summary', '')}</td>
                    <td>{issue.get('storyPoints', 0)}</td>
                </tr>
            """
        
        content += """
            </tbody>
        </table>
        """
        
        if incomplete:
            content += f"""
            <h2>Incomplete Issues ({len(incomplete)})</h2>
            <table>
                <thead>
                    <tr><th>Issue</th><th>Summary</th><th>Status</th></tr>
                </thead>
                <tbody>
            """
            
            for issue in incomplete:
                key = issue.get('issueKey', issue.get('key', ''))
                content += f"""
                    <tr>
                        <td><a href="https://jira.example.com/browse/{key}">{key}</a></td>
                        <td>{issue.get('summary', '')}</td>
                        <td>{issue.get('status', 'Unknown')}</td>
                    </tr>
                """
            
            content += """
                </tbody>
            </table>
            """
        
        return self.create_page(space_key, title, content)

    def create_decision_log_entry(self, space_key: str,
                                  decision: Decision) -> Tuple[Dict[str, Any], int]:
        """
        Create a Decision Log entry page.
        """
        title = f"Decision: {decision.title}"
        
        content = f"""
        <h1>{decision.title}</h1>
        
        <ac:structured-macro ac:name="info">
            <ac:rich-text-body>
                <p><strong>Status:</strong> Decided</p>
                <p><strong>Date:</strong> 2026-02-24</p>
            </ac:rich-text-body>
        </ac:structured-macro>
        
        <h2>Context</h2>
        <p>{decision.context}</p>
        
        <h2>Alternatives Considered</h2>
        """
        
        for alt in decision.alternatives:
            content += f"""
            <h3>{alt.name}</h3>
            <p><strong>Pros:</strong></p>
            <ul>
            """
            for pro in alt.pros:
                content += f"<li>{pro}</li>"
            content += """
            </ul>
            <p><strong>Cons:</strong></p>
            <ul>
            """
            for con in alt.cons:
                content += f"<li>{con}</li>"
            content += "</ul>"
        
        content += f"""
        <h2>Decision</h2>
        <p><strong>Chosen:</strong> {decision.chosen_alternative}</p>
        
        <h2>Rationale</h2>
        <p>{decision.rationale}</p>
        
        <h2>Consequences</h2>
        <ul>
        """
        
        for consequence in decision.consequences:
            content += f"<li>{consequence}</li>"
        
        content += """
        </ul>
        """
        
        if decision.related_issues:
            content += """
            <h2>Related Jira Issues</h2>
            <ul>
            """
            for issue in decision.related_issues:
                content += f'<li><a href="https://jira.example.com/browse/{issue}">{issue}</a></li>'
            content += "</ul>"
        
        if decision.participants:
            content += """
            <h2>Participants</h2>
            <ul>
            """
            for participant in decision.participants:
                content += f"<li>{participant}</li>"
            content += "</ul>"
        
        return self.create_page(space_key, title, content)

    def create_metrics_report_page(self, space_key: str, project_key: str,
                                   sprints_data: List[Dict]) -> Tuple[Dict[str, Any], int]:
        """
        Create a Metrics Report page.
        """
        title = f"{project_key} - Metrics Report"
        
        content = f"""
        <h1>{project_key} - Sprint Metrics Report</h1>
        <p>Generated: 2026-02-24T10:00:00Z</p>
        
        <h2>Velocity Trend</h2>
        <table>
            <thead>
                <tr><th>Sprint</th><th>Velocity (SP)</th><th>Planned (SP)</th><th>Say/Do Ratio</th></tr>
            </thead>
            <tbody>
        """
        
        for sprint in sprints_data:
            say_do = sprint.get('velocity', 0) / sprint.get('planned', 1) if sprint.get('planned') else 0
            content += f"""
                <tr>
                    <td>{sprint.get('name', '')}</td>
                    <td>{sprint.get('velocity', 0)}</td>
                    <td>{sprint.get('planned', 0)}</td>
                    <td>{say_do:.0%}</td>
                </tr>
            """
        
        total_velocity = sum(s.get('velocity', 0) for s in sprints_data)
        avg_velocity = total_velocity / len(sprints_data) if sprints_data else 0
        
        content += f"""
            </tbody>
        </table>
        
        <h2>Summary</h2>
        <ul>
            <li><strong>Average Velocity:</strong> {avg_velocity:.1f} SP</li>
            <li><strong>Total Sprints:</strong> {len(sprints_data)}</li>
        </ul>
        
        <h2>Recommendations</h2>
        <ul>
            <li>Maintain current capacity planning based on stable velocity</li>
            <li>Continue monitoring Say/Do ratio for predictability</li>
        </ul>
        """
        
        return self.create_page(space_key, title, content)
