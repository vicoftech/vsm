"""
Confluence Spaces Tools for MCP.
Implements space-related operations.
"""

from typing import Dict, Any, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from confluence_client import ConfluenceClient


class SpacesTools:
    """Tools for managing Confluence spaces."""

    def __init__(self, client: ConfluenceClient):
        """Initialize with Confluence client."""
        self.client = client

    async def get_spaces(
        self,
        limit: int = 25,
        start: int = 0
    ) -> Dict[str, Any]:
        """
        Get all spaces.
        
        Args:
            limit: Maximum results
            start: Starting index
            
        Returns:
            List of spaces
        """
        return await self.client.get("space", params={"limit": limit, "start": start})

    async def get_space(
        self,
        space_key: str,
        expand: str = "homepage"
    ) -> Dict[str, Any]:
        """
        Get space by key.
        
        Args:
            space_key: Space key
            expand: Optional expand parameter
            
        Returns:
            Space data
        """
        return await self.client.get(f"space/{space_key}", params={"expand": expand})

    async def create_space(
        self,
        key: str,
        name: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a space.
        
        Args:
            key: Space key
            name: Space name
            description: Optional description
            
        Returns:
            Created space data
        """
        space_data = {
            "key": key,
            "name": name,
            "type": "global"
        }
        
        if description:
            space_data["description"] = {
                "plain": {
                    "value": description,
                    "representation": "plain"
                }
            }
        
        return await self.client.post("space", json_data=space_data)


