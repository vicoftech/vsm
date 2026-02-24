"""
Jira Sprints Tools for MCP.
Implements sprint (Scrum) operations.
"""

from typing import Dict, Any, Optional, List
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jira_client import JiraClient


class SprintsTools:
    """Tools for managing Jira sprints."""

    def __init__(self, client: JiraClient):
        """Initialize with Jira client."""
        self.client = client

    async def get_sprints(
        self,
        board_id: int,
        state: Optional[str] = None,
        max_results: int = 50,
        start_at: int = 0
    ) -> Dict[str, Any]:
        """
        Get sprints for a board.
        
        Args:
            board_id: Board ID
            state: Filter by state ("active", "closed", "future")
            max_results: Maximum results
            start_at: Starting index
            
        Returns:
            List of sprints
        """
        params = {
            "maxResults": max_results,
            "startAt": start_at
        }
        
        if state:
            params["state"] = state
        
        return await self.client.get(f"board/{board_id}/sprint", params=params)

    async def create_sprint(
        self,
        board_id: int,
        name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        goal: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a sprint.
        
        Args:
            board_id: Board ID
            name: Sprint name
            start_date: Start date (ISO format: YYYY-MM-DD)
            end_date: End date (ISO format: YYYY-MM-DD)
            goal: Sprint goal
            
        Returns:
            Created sprint data (includes id)
        """
        data = {
            "name": name,
            "originBoardId": board_id
        }
        
        if start_date:
            data["startDate"] = start_date
        if end_date:
            data["endDate"] = end_date
        if goal:
            data["goal"] = goal
        
        return await self.client.post("sprint", json_data=data)

    async def add_to_sprint(
        self,
        sprint_id: int,
        issue_keys: List[str]
    ) -> Dict[str, Any]:
        """
        Add issues to sprint.
        
        Args:
            sprint_id: Sprint ID
            issue_keys: List of issue keys
            
        Returns:
            Empty dict on success
        """
        data = {"issues": issue_keys}
        return await self.client.post(f"sprint/{sprint_id}/issue", json_data=data)

    async def start_sprint(self, sprint_id: int) -> Dict[str, Any]:
        """
        Start a sprint.
        
        Args:
            sprint_id: Sprint ID
            
        Returns:
            Empty dict on success
        """
        data = {"id": sprint_id}
        return await self.client.post(f"sprint/{sprint_id}", json_data=data)

    async def complete_sprint(self, sprint_id: int) -> Dict[str, Any]:
        """
        Complete (close) a sprint.
        
        Args:
            sprint_id: Sprint ID
            
        Returns:
            Empty dict on success
        """
        # Get current sprint to update state
        sprint = await self.get_sprint(sprint_id)
        data = {
            "id": sprint_id,
            "state": "closed"
        }
        return await self.client.put(f"sprint/{sprint_id}", json_data=data)

    async def get_sprint(self, sprint_id: int) -> Dict[str, Any]:
        """
        Get sprint by ID.
        
        Args:
            sprint_id: Sprint ID
            
        Returns:
            Sprint data
        """
        return await self.client.get(f"sprint/{sprint_id}")

