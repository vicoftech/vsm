"""
Jira Issues Tools for MCP.
Implements all issue-related operations.
"""

from typing import Dict, Any, List, Optional
import sys
import os
# Add parent directory to path for Lambda packaging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jira_client import JiraClient


class IssuesTools:
    """Tools for managing Jira issues."""

    def __init__(self, client: JiraClient):
        """Initialize with Jira client."""
        self.client = client

    async def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """
        Get issue by key.
        
        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            
        Returns:
            Issue data
        """
        return await self.client.get(f"issue/{issue_key}")

    async def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        fields: Optional[List[str]] = None,
        start_at: int = 0
    ) -> Dict[str, Any]:
        """
        Search issues using JQL.
        
        Args:
            jql: JQL query string
            max_results: Maximum number of results
            fields: List of fields to return
            start_at: Starting index for pagination
            
        Returns:
            Search results with issues list
        """
        params = {
            "jql": jql,
            "maxResults": max_results,
            "startAt": start_at
        }
        
        if fields:
            params["fields"] = ",".join(fields)
        
        return await self.client.get("search", params=params)

    async def get_transitions(self, issue_key: str) -> Dict[str, Any]:
        """
        Get available transitions for an issue.
        
        Args:
            issue_key: Issue key
            
        Returns:
            Available transitions
        """
        return await self.client.get(f"issue/{issue_key}/transitions")

    async def transition_issue(
        self,
        issue_key: str,
        transition_id: str,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transition issue to a new status.
        
        Args:
            issue_key: Issue key
            transition_id: Transition ID
            comment: Optional comment
            
        Returns:
            Empty dict on success
        """
        data = {"transition": {"id": transition_id}}
        
        if comment:
            data["update"] = {
                "comment": [{"add": {"body": comment}}]
            }
        
        return await self.client.post(f"issue/{issue_key}/transitions", json_data=data)

    async def create_epic(
        self,
        project: str,
        summary: str,
        description: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create an epic."""
        return await self._create_issue("Epic", project, summary, description, **kwargs)

    async def create_story(
        self,
        project: str,
        summary: str,
        description: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a story."""
        return await self._create_issue("Story", project, summary, description, **kwargs)

    async def create_task(
        self,
        project: str,
        summary: str,
        description: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a task."""
        return await self._create_issue("Task", project, summary, description, **kwargs)

    async def create_bug(
        self,
        project: str,
        summary: str,
        description: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a bug."""
        return await self._create_issue("Bug", project, summary, description, **kwargs)

    async def create_subtask(
        self,
        project: str,
        parent_key: str,
        summary: str,
        description: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a subtask."""
        issue_type = kwargs.pop("issue_type", "Sub-task")
        fields = {
            "project": {"key": project},
            "summary": summary,
            "issuetype": {"name": issue_type},
            "parent": {"key": parent_key}
        }
        
        if description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]
            }
        
        # Add custom fields
        fields.update(kwargs)
        
        data = {"fields": fields}
        return await self.client.post("issue", json_data=data)

    async def _create_issue(
        self,
        issue_type: str,
        project: str,
        summary: str,
        description: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Internal method to create issues."""
        fields = {
            "project": {"key": project},
            "summary": summary,
            "issuetype": {"name": issue_type}
        }
        
        if description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]
            }
        
        # Add custom fields
        fields.update(kwargs)
        
        data = {"fields": fields}
        return await self.client.post("issue", json_data=data)

    async def update_issue(
        self,
        issue_key: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update issue fields.
        
        Args:
            issue_key: Issue key
            summary: New summary
            description: New description
            **kwargs: Other fields to update
            
        Returns:
            Empty dict on success
        """
        fields = {}
        
        if summary:
            fields["summary"] = summary
        
        if description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]
            }
        
        fields.update(kwargs)
        
        data = {"fields": fields}
        return await self.client.put(f"issue/{issue_key}", json_data=data)

    async def assign_issue(
        self,
        issue_key: str,
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assign issue to a user.
        
        Args:
            issue_key: Issue key
            account_id: User account ID (None to unassign)
            
        Returns:
            Empty dict on success
        """
        data = {"accountId": account_id} if account_id else {"accountId": "-1"}  # "-1" unassigns in Jira
        
        return await self.client.put(f"issue/{issue_key}/assignee", json_data=data)

    async def add_comment(
        self,
        issue_key: str,
        comment_text: str
    ) -> Dict[str, Any]:
        """
        Add comment to issue.
        
        Args:
            issue_key: Issue key
            comment_text: Comment text
            
        Returns:
            Created comment data
        """
        data = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment_text}]}]
            }
        }
        
        return await self.client.post(f"issue/{issue_key}/comment", json_data=data)

    async def add_worklog(
        self,
        issue_key: str,
        time_spent: str,
        comment: Optional[str] = None,
        started: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add worklog entry.
        
        Args:
            issue_key: Issue key
            time_spent: Time spent (e.g., "2h 30m")
            comment: Optional comment
            started: Start time (ISO format)
            
        Returns:
            Created worklog data
        """
        data = {"timeSpent": time_spent}
        
        if comment:
            data["comment"] = {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}]
            }
        
        if started:
            data["started"] = started
        
        return await self.client.post(f"issue/{issue_key}/worklog", json_data=data)

    async def link_issues(
        self,
        inward_issue: str,
        outward_issue: str,
        link_type: str = "relates to"
    ) -> Dict[str, Any]:
        """
        Link two issues.
        
        Args:
            inward_issue: Inward issue key
            outward_issue: Outward issue key
            link_type: Link type (e.g., "relates to", "blocks", "is blocked by")
            
        Returns:
            Created link data
        """
        data = {
            "type": {"name": link_type},
            "inwardIssue": {"key": inward_issue},
            "outwardIssue": {"key": outward_issue}
        }
        
        return await self.client.post("issueLink", json_data=data)

    async def set_story_points(
        self,
        issue_key: str,
        story_points: int
    ) -> Dict[str, Any]:
        """
        Set story points for an issue.
        
        Args:
            issue_key: Issue key
            story_points: Story points value
            
        Returns:
            Empty dict on success
        """
        # Story points field ID varies by Jira instance
        # Common field IDs: customfield_10016, customfield_10002
        # We'll try to find it or use a common one
        data = {
            "fields": {
                "customfield_10016": story_points  # Common story points field
            }
        }
        
        return await self.client.put(f"issue/{issue_key}", json_data=data)

    async def add_labels(
        self,
        issue_key: str,
        labels: List[str]
    ) -> Dict[str, Any]:
        """
        Add labels to issue.
        
        Args:
            issue_key: Issue key
            labels: List of label names
            
        Returns:
            Empty dict on success
        """
        # Get current issue to preserve existing labels
        issue = await self.get_issue(issue_key)
        current_labels = issue.get("fields", {}).get("labels", [])
        
        # Merge labels
        new_labels = list(set(current_labels + labels))
        
        data = {"fields": {"labels": new_labels}}
        return await self.client.put(f"issue/{issue_key}", json_data=data)

    async def bulk_assign(
        self,
        issue_keys: List[str],
        account_id: str
    ) -> Dict[str, Any]:
        """
        Bulk assign issues.
        
        Args:
            issue_keys: List of issue keys
            account_id: User account ID
            
        Returns:
            Bulk operation result
        """
        results = []
        for key in issue_keys:
            try:
                await self.assign_issue(key, account_id)
                results.append({"key": key, "status": "success"})
            except Exception as e:
                results.append({"key": key, "status": "error", "error": str(e)})
        
        return {"results": results}

    async def bulk_transition(
        self,
        issue_keys: List[str],
        transition_id: str
    ) -> Dict[str, Any]:
        """
        Bulk transition issues.
        
        Args:
            issue_keys: List of issue keys
            transition_id: Transition ID
            
        Returns:
            Bulk operation result
        """
        results = []
        for key in issue_keys:
            try:
                await self.transition_issue(key, transition_id)
                results.append({"key": key, "status": "success"})
            except Exception as e:
                results.append({"key": key, "status": "error", "error": str(e)})
        
        return {"results": results}

    async def bulk_add_labels(
        self,
        issue_keys: List[str],
        labels: List[str]
    ) -> Dict[str, Any]:
        """
        Bulk add labels to issues.
        
        Args:
            issue_keys: List of issue keys
            labels: List of labels to add
            
        Returns:
            Bulk operation result
        """
        results = []
        for key in issue_keys:
            try:
                await self.add_labels(key, labels)
                results.append({"key": key, "status": "success"})
            except Exception as e:
                results.append({"key": key, "status": "error", "error": str(e)})
        
        return {"results": results}

