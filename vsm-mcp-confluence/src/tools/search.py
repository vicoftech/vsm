"""
Confluence Search Tools for MCP.
Implements CQL (Confluence Query Language) search.
"""

from typing import Dict, Any, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from confluence_client import ConfluenceClient


class SearchTools:
    """Tools for searching Confluence content."""

    def __init__(self, client: ConfluenceClient):
        """Initialize with Confluence client."""
        self.client = client

    async def search_cql(
        self,
        cql: str,
        limit: int = 25,
        start: int = 0
    ) -> Dict[str, Any]:
        """
        Search using CQL (Confluence Query Language).
        
        Args:
            cql: CQL query string
            limit: Maximum results
            start: Starting index
            
        Returns:
            Search results
        """
        return await self.client.get("content/search", params={
            "cql": cql,
            "limit": limit,
            "start": start
        })

    async def search_by_title(
        self,
        title: str,
        space_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search pages by title.
        
        Args:
            title: Title to search
            space_key: Optional space key filter
            
        Returns:
            Search results
        """
        cql = f'text ~ "{title}"'
        if space_key:
            cql += f' AND space = {space_key}'
        return await self.search_cql(cql)

    async def search_by_label(
        self,
        label: str,
        space_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search pages by label.
        
        Args:
            label: Label to search
            space_key: Optional space key filter
            
        Returns:
            Search results
        """
        cql = f'label = "{label}"'
        if space_key:
            cql += f' AND space = {space_key}'
        return await self.search_cql(cql)


