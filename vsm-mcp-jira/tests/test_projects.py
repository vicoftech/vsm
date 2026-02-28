"""
Unit tests for Jira Projects Tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.tools.projects import ProjectsTools
from src.jira_client import JiraClient


@pytest.fixture
def mock_client():
    """Create a mock Jira client."""
    client = MagicMock(spec=JiraClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def projects_tools(mock_client):
    """Create ProjectsTools instance with mock client."""
    return ProjectsTools(mock_client)


@pytest.mark.asyncio
async def test_get_projects(projects_tools, mock_client):
    """Test getting all projects."""
    mock_client.get.return_value = [
        {"key": "PROJ", "name": "Test Project"},
        {"key": "PROJ2", "name": "Test Project 2"}
    ]
    
    result = await projects_tools.get_projects()
    
    assert len(result) == 2
    mock_client.get.assert_called_once()
    call_args = mock_client.get.call_args
    assert call_args[0][0] == "project"


@pytest.mark.asyncio
async def test_get_project(projects_tools, mock_client):
    """Test getting a project by key."""
    mock_client.get.return_value = {
        "key": "PROJ",
        "name": "Test Project",
        "id": "10000"
    }
    
    result = await projects_tools.get_project("PROJ")
    
    assert result["key"] == "PROJ"
    mock_client.get.assert_called_once()
    call_args = mock_client.get.call_args
    assert call_args[0][0] == "project/PROJ"


@pytest.mark.asyncio
async def test_create_project(projects_tools, mock_client):
    """Test creating a project."""
    mock_client.post.return_value = {
        "id": "10000",
        "key": "PROJ",
        "name": "New Project"
    }
    
    result = await projects_tools.create_project(
        key="PROJ",
        name="New Project",
        lead="user-123",
        project_template_key="gh-scrum-template"
    )
    
    assert result["key"] == "PROJ"
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args[1]["json_data"]["projectTemplateKey"] == "gh-scrum-template"


@pytest.mark.asyncio
async def test_update_project(projects_tools, mock_client):
    """Test updating a project."""
    mock_client.put.return_value = {
        "key": "PROJ",
        "name": "Updated Project"
    }
    
    result = await projects_tools.update_project(
        project_key="PROJ",
        name="Updated Project"
    )
    
    assert result["name"] == "Updated Project"
    mock_client.put.assert_called_once()


@pytest.mark.asyncio
async def test_delete_project(projects_tools, mock_client):
    """Test deleting a project."""
    mock_client.delete.return_value = {}
    
    result = await projects_tools.delete_project("PROJ")
    
    assert result == {}
    mock_client.delete.assert_called_once_with("project/PROJ")


