"""
Jira Dashboards Tools for MCP.
Implements dashboard operations.
"""

from typing import Dict, Any, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jira_client import JiraClient


class DashboardsTools:
    """Tools for managing Jira dashboards."""

    def __init__(self, client: JiraClient):
        """Initialize with Jira client."""
        self.client = client

    async def create_dashboard(
        self,
        name: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a dashboard.
        
        Note: Gadgets must be added from Jira UI.
        
        Args:
            name: Dashboard name
            description: Optional description
            
        Returns:
            Created dashboard data (includes id)
        """
        data = {"name": name}
        
        if description:
            data["description"] = description
        
        return await self.client.post("dashboard", json_data=data)

    async def get_dashboard(self, dashboard_id: int) -> Dict[str, Any]:
        """
        Get dashboard by ID.
        
        Args:
            dashboard_id: Dashboard ID
            
        Returns:
            Dashboard data
        """
        return await self.client.get(f"dashboard/{dashboard_id}")

    async def get_dashboards(
        self,
        filter: Optional[str] = None,
        start_at: int = 0,
        max_results: int = 50
    ) -> Dict[str, Any]:
        """
        Get dashboards.
        
        Args:
            filter: Filter string
            start_at: Starting index
            max_results: Maximum results
            
        Returns:
            List of dashboards
        """
        params = {
            "startAt": start_at,
            "maxResults": max_results
        }
        
        if filter:
            params["filter"] = filter
        
        return await self.client.get("dashboard", params=params)

    async def update_dashboard(
        self,
        dashboard_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            name: New name
            description: New description
            
        Returns:
            Updated dashboard data
        """
        data = {}
        
        if name:
            data["name"] = name
        if description:
            data["description"] = description
        
        return await self.client.put(f"dashboard/{dashboard_id}", json_data=data)

    async def delete_dashboard(self, dashboard_id: int) -> Dict[str, Any]:
        """
        Delete dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            
        Returns:
            Empty dict on success
        """
        return await self.client.delete(f"dashboard/{dashboard_id}")

