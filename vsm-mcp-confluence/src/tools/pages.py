"""
Confluence Pages Tools for MCP.
Implements page-related operations.
"""

from typing import Dict, Any, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from confluence_client import ConfluenceClient


class PagesTools:
    """Tools for managing Confluence pages."""

    def __init__(self, client: ConfluenceClient):
        """Initialize with Confluence client."""
        self.client = client

    async def create_page(
        self,
        space_key: str,
        title: str,
        body: str,
        parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a page.
        
        Args:
            space_key: Space key
            title: Page title
            body: Page body (in Confluence storage format or markdown)
            parent_id: Optional parent page ID
            
        Returns:
            Created page data
        """
        page_data = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": body,
                    "representation": "storage"
                }
            }
        }
        
        if parent_id:
            page_data["ancestors"] = [{"id": parent_id}]
        
        return await self.client.post("content", json_data=page_data)

    async def update_page(
        self,
        page_id: str,
        title: str,
        body: str,
        version: int
    ) -> Dict[str, Any]:
        """
        Update a page.
        
        Args:
            page_id: Page ID
            title: New title
            body: New body
            version: Current version number
            
        Returns:
            Updated page data
        """
        page_data = {
            "title": title,
            "type": "page",
            "body": {
                "storage": {
                    "value": body,
                    "representation": "storage"
                }
            },
            "version": {"number": version + 1}
        }
        
        return await self.client.put(f"content/{page_id}", json_data=page_data)

    async def get_page(
        self,
        page_id: str,
        expand: str = "body.storage,version,space"
    ) -> Dict[str, Any]:
        """
        Get page by ID.
        
        Args:
            page_id: Page ID
            expand: Optional expand parameter
            
        Returns:
            Page data
        """
        return await self.client.get(f"content/{page_id}", params={"expand": expand})

    async def get_page_content(self, page_id: str) -> str:
        """
        Get page content.
        
        Args:
            page_id: Page ID
            
        Returns:
            Page content
        """
        page = await self.get_page(page_id)
        return page.get("body", {}).get("storage", {}).get("value", "")

    async def delete_page(self, page_id: str) -> Dict[str, Any]:
        """
        Delete a page.
        
        Args:
            page_id: Page ID
            
        Returns:
            Empty dict on success
        """
        return await self.client.delete(f"content/{page_id}")

    async def get_pages(
        self,
        space_key: str,
        limit: int = 25,
        start: int = 0
    ) -> Dict[str, Any]:
        """
        Get pages in a space.
        
        Args:
            space_key: Space key
            limit: Maximum results
            start: Starting index
            
        Returns:
            List of pages
        """
        return await self.client.get("content", params={
            "spaceKey": space_key,
            "type": "page",
            "limit": limit,
            "start": start
        })


