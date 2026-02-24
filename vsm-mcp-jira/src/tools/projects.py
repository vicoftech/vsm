"""
Jira Projects Tools for MCP.
Implements project operations.
"""

from typing import Dict, Any, Optional, List
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jira_client import JiraClient


class ProjectsTools:
    """Tools for managing Jira projects."""

    def __init__(self, client: JiraClient):
        """Initialize with Jira client."""
        self.client = client

    async def get_projects(
        self,
        expand: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all projects.
        
        Args:
            expand: Optional expand parameter
            
        Returns:
            List of projects
        """
        params = {}
        if expand:
            params["expand"] = expand
        
        result = await self.client.get("project", params=params)
        # API returns a list directly
        return result if isinstance(result, list) else result.get("values", [])

    async def get_project(
        self,
        project_key: str,
        expand: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get project by key.
        
        Args:
            project_key: Project key
            expand: Optional expand parameter
            
        Returns:
            Project data
        """
        params = {}
        if expand:
            params["expand"] = expand
        
        return await self.client.get(f"project/{project_key}", params=params)

    async def create_project(
        self,
        key: str,
        name: str,
        lead: str,
        project_type: str = "software",
        description: Optional[str] = None,
        project_template_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a project.
        
        Args:
            key: Project key (uppercase, alphanumeric, max 10 chars)
            name: Project name
            lead: Lead account ID
            project_type: Project type (default: "software")
            description: Optional description
            project_template_key: Template key (e.g., "gh-scrum-template", 
                          "gh-kanban-template", "basic-software-development-template")
            
        Returns:
            Created project data
        """
        data = {
            "key": key,
            "name": name,
            "projectTypeKey": project_type,
            "leadAccountId": lead
        }
        
        if description:
            data["description"] = description
        
        if project_template_key:
            data["projectTemplateKey"] = project_template_key
        
        return await self.client.post("project", json_data=data)

    async def update_project(
        self,
        project_key: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        lead: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update project.
        
        Args:
            project_key: Project key
            name: New name
            description: New description
            lead: New lead account ID
            
        Returns:
            Updated project data
        """
        data = {}
        
        if name:
            data["name"] = name
        if description:
            data["description"] = description
        if lead:
            data["leadAccountId"] = lead
        
        return await self.client.put(f"project/{project_key}", json_data=data)

    async def get_project_roles(self, project_key: str) -> Dict[str, Any]:
        """
        Get project roles.
        
        Args:
            project_key: Project key
            
        Returns:
            Project roles
        """
        return await self.client.get(f"project/{project_key}/role")

    async def add_user_to_project(
        self,
        project_key: str,
        account_id: str,
        role_id: int
    ) -> Dict[str, Any]:
        """
        Add user to project with a specific role.
        
        Args:
            project_key: Project key
            account_id: User account ID
            role_id: Role ID (from get_project_roles)
            
        Returns:
            Empty dict on success
        """
        # Get role URL
        roles = await self.get_project_roles(project_key)
        role_name = None
        for name, url in roles.items():
            if str(role_id) in url or url.endswith(f"/{role_id}"):
                role_name = name
                break
        
        if not role_name:
            raise ValueError(f"Role ID {role_id} not found in project")
        
        # Add user to role
        data = [account_id]
        return await self.client.post(
            f"project/{project_key}/role/{role_id}",
            json_data=data
        )

