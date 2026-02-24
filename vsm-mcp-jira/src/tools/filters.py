"""
Jira Filters Tools for MCP.
Implements filter (saved JQL) operations.
"""

from typing import Dict, Any, Optional, List
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jira_client import JiraClient


class FiltersTools:
    """Tools for managing Jira filters."""

    def __init__(self, client: JiraClient):
        """Initialize with Jira client."""
        self.client = client

    async def create_filter(
        self,
        name: str,
        jql: str,
        description: Optional[str] = None,
        favourite: bool = False
    ) -> Dict[str, Any]:
        """
        Create a saved filter (saved JQL).
        
        Args:
            name: Filter name
            jql: JQL query string
            description: Optional description
            favourite: Mark as favourite
            
        Returns:
            Created filter data (includes id)
        """
        data = {
            "name": name,
            "jql": jql
        }
        
        if description:
            data["description"] = description
        
        if favourite:
            data["favourite"] = True
        
        return await self.client.post("filter", json_data=data)

    async def get_filter(self, filter_id: str) -> Dict[str, Any]:
        """
        Get filter by ID.
        
        Args:
            filter_id: Filter ID
            
        Returns:
            Filter data
        """
        return await self.client.get(f"filter/{filter_id}")

    async def search_filters(
        self,
        filter_name: Optional[str] = None,
        account_id: Optional[str] = None,
        max_results: int = 50,
        start_at: int = 0
    ) -> Dict[str, Any]:
        """
        Search filters.
        
        Args:
            filter_name: Filter name to search
            account_id: User account ID (for user's filters)
            max_results: Maximum results
            start_at: Starting index
            
        Returns:
            List of filters
        """
        params = {
            "maxResults": max_results,
            "startAt": start_at
        }
        
        if filter_name:
            params["filterName"] = filter_name
        
        if account_id:
            params["accountId"] = account_id
        
        return await self.client.get("filter/search", params=params)

    async def update_filter(
        self,
        filter_id: str,
        name: Optional[str] = None,
        jql: Optional[str] = None,
        description: Optional[str] = None,
        favourite: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Update filter.
        
        Args:
            filter_id: Filter ID
            name: New name
            jql: New JQL
            description: New description
            favourite: Mark as favourite
            
        Returns:
            Updated filter data
        """
        data = {}
        
        if name:
            data["name"] = name
        if jql:
            data["jql"] = jql
        if description:
            data["description"] = description
        if favourite is not None:
            data["favourite"] = favourite
        
        return await self.client.put(f"filter/{filter_id}", json_data=data)

    async def delete_filter(self, filter_id: str) -> Dict[str, Any]:
        """
        Delete filter.
        
        Args:
            filter_id: Filter ID
            
        Returns:
            Empty dict on success
        """
        return await self.client.delete(f"filter/{filter_id}")

