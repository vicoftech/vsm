"""
Jira Boards Tools for MCP.
Implements board (Scrum/Kanban) operations.
"""

from typing import Dict, Any, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jira_client import JiraClient


class BoardsTools:
    """Tools for managing Jira boards."""

    def __init__(self, client: JiraClient):
        """Initialize with Jira client."""
        self.client = client

    async def get_boards(
        self,
        project_key: Optional[str] = None,
        board_type: Optional[str] = None,
        max_results: int = 50,
        start_at: int = 0
    ) -> Dict[str, Any]:
        """
        Get boards (Scrum or Kanban).
        
        Args:
            project_key: Filter by project key
            board_type: Filter by type ("scrum" or "kanban")
            max_results: Maximum results
            start_at: Starting index
            
        Returns:
            List of boards
        """
        params = {
            "maxResults": max_results,
            "startAt": start_at
        }
        
        if project_key:
            params["projectKeyOrId"] = project_key
        
        if board_type:
            params["type"] = board_type
        
        return await self.client.get_agile("board", params=params)

    async def create_board(
        self,
        name: str,
        type: str,
        filter_id: int
    ) -> Dict[str, Any]:
        """
        Create a board (Scrum or Kanban).
        
        Note: Requires a saved filter (created with create_filter).
        
        Args:
            name: Board name
            type: Board type ("scrum" or "kanban")
            filter_id: Filter ID (from create_filter)
            
        Returns:
            Created board data (includes id)
        """
        if type not in ["scrum", "kanban"]:
            raise ValueError("Board type must be 'scrum' or 'kanban'")
        
        data = {
            "name": name,
            "type": type,
            "filterId": filter_id
        }
        
        return await self.client.post_agile("board", json_data=data)

    async def get_board(self, board_id: int) -> Dict[str, Any]:
        """
        Get board by ID.
        
        Args:
            board_id: Board ID
            
        Returns:
            Board data
        """
        return await self.client.get_agile(f"board/{board_id}")

