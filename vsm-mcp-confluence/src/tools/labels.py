"""
Confluence Labels Tools for MCP.
Implements label-related operations.
"""

from typing import Dict, Any, List
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from confluence_client import ConfluenceClient


class LabelsTools:
    """Tools for managing Confluence labels."""

    def __init__(self, client: ConfluenceClient):
        """Initialize with Confluence client."""
        self.client = client

    async def add_labels(
        self,
        page_id: str,
        labels: List[str]
    ) -> Dict[str, Any]:
        """
        Add labels to a page.
        
        Args:
            page_id: Page ID
            labels: List of label names
            
        Returns:
            Updated labels
        """
        labels_data = [
            {"prefix": "global", "name": label}
            for label in labels
        ]
        
        return await self.client.post(f"content/{page_id}/label", json_data=labels_data)

    async def get_labels(self, page_id: str) -> Dict[str, Any]:
        """
        Get labels for a page.
        
        Args:
            page_id: Page ID
            
        Returns:
            List of labels
        """
        return await self.client.get(f"content/{page_id}/label")

    async def remove_label(
        self,
        page_id: str,
        label_name: str
    ) -> Dict[str, Any]:
        """
        Remove a label from a page.
        
        Args:
            page_id: Page ID
            label_name: Label name to remove
            
        Returns:
            Empty dict on success
        """
        return await self.client.delete(f"content/{page_id}/label/{label_name}")


