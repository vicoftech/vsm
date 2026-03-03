"""
Unit tests for Jira Sprints Tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.tools.sprints import SprintsTools
from src.jira_client import JiraClient


@pytest.fixture
def mock_client():
    """Create a mock Jira client."""
    client = MagicMock(spec=JiraClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    return client


@pytest.fixture
def sprints_tools(mock_client):
    """Create SprintsTools instance with mock client."""
    return SprintsTools(mock_client)


@pytest.mark.asyncio
async def test_get_sprints(sprints_tools, mock_client):
    """Test getting sprints for a board."""
    mock_client.get.return_value = {
        "values": [
            {"id": 1, "name": "Sprint 1", "state": "active"},
            {"id": 2, "name": "Sprint 2", "state": "closed"}
        ]
    }
    
    result = await sprints_tools.get_sprints(board_id=1, state="active")
    
    assert len(result["values"]) == 2
    mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_create_sprint(sprints_tools, mock_client):
    """Test creating a sprint."""
    mock_client.post.return_value = {
        "id": 3,
        "name": "Sprint 3",
        "state": "future"
    }
    
    result = await sprints_tools.create_sprint(
        board_id=1,
        name="Sprint 3",
        start_date="2024-01-15",
        end_date="2024-01-29",
        goal="Complete user stories"
    )
    
    assert result["id"] == 3
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_add_to_sprint(sprints_tools, mock_client):
    """Test adding issues to sprint."""
    mock_client.post.return_value = {}
    
    result = await sprints_tools.add_to_sprint(
        sprint_id=1,
        issue_keys=["PROJ-123", "PROJ-124"]
    )
    
    assert result == {}
    mock_client.post.assert_called_once()





