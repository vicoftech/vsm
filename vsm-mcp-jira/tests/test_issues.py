"""
Unit tests for Jira Issues Tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.tools.issues import IssuesTools
from src.jira_client import JiraClient


@pytest.fixture
def mock_client():
    """Create a mock Jira client."""
    client = MagicMock(spec=JiraClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    return client


@pytest.fixture
def issues_tools(mock_client):
    """Create IssuesTools instance with mock client."""
    return IssuesTools(mock_client)


@pytest.mark.asyncio
async def test_get_issue(issues_tools, mock_client):
    """Test getting an issue."""
    mock_client.get.return_value = {
        "key": "PROJ-123",
        "fields": {
            "summary": "Test Issue",
            "status": {"name": "To Do"}
        }
    }
    
    result = await issues_tools.get_issue("PROJ-123")
    
    assert result["key"] == "PROJ-123"
    mock_client.get.assert_called_once_with("issue/PROJ-123")


@pytest.mark.asyncio
async def test_search_issues(issues_tools, mock_client):
    """Test searching issues with JQL."""
    mock_client.get.return_value = {
        "issues": [
            {"key": "PROJ-123", "fields": {"summary": "Issue 1"}},
            {"key": "PROJ-124", "fields": {"summary": "Issue 2"}}
        ],
        "total": 2
    }
    
    result = await issues_tools.search_issues("project = PROJ", max_results=10)
    
    assert len(result["issues"]) == 2
    mock_client.get.assert_called_once()
    call_args = mock_client.get.call_args
    # get(endpoint, params=...) - params is a keyword argument
    assert call_args[0][0] == "search"
    assert "jql" in call_args[1]["params"]


@pytest.mark.asyncio
async def test_create_story(issues_tools, mock_client):
    """Test creating a story."""
    mock_client.post.return_value = {
        "id": "12345",
        "key": "PROJ-125",
        "self": "https://agentvsm.atlassian.net/rest/api/3/issue/12345"
    }
    
    result = await issues_tools.create_story(
        project="PROJ",
        summary="New Story",
        description="Story description"
    )
    
    assert result["key"] == "PROJ-125"
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    # post(endpoint, json_data=..., params=...)
    assert call_args[0][0] == "issue"
    assert call_args[1]["json_data"]["fields"]["summary"] == "New Story"


@pytest.mark.asyncio
async def test_transition_issue(issues_tools, mock_client):
    """Test transitioning an issue."""
    mock_client.post.return_value = {}
    
    result = await issues_tools.transition_issue(
        issue_key="PROJ-123",
        transition_id="21",
        comment="Moving to In Progress"
    )
    
    assert result == {}
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    # post(endpoint, json_data=...)
    assert "transitions" in call_args[0][0]


@pytest.mark.asyncio
async def test_assign_issue(issues_tools, mock_client):
    """Test assigning an issue."""
    mock_client.put.return_value = {}
    
    result = await issues_tools.assign_issue(
        issue_key="PROJ-123",
        account_id="user-123"
    )
    
    assert result == {}
    mock_client.put.assert_called_once()
    call_args = mock_client.put.call_args
    # put(endpoint, json_data=...)
    assert "assignee" in call_args[0][0]
    assert call_args[1]["json_data"]["accountId"] == "user-123"


@pytest.mark.asyncio
async def test_add_comment(issues_tools, mock_client):
    """Test adding a comment."""
    mock_client.post.return_value = {
        "id": "10000",
        "body": "Test comment"
    }
    
    result = await issues_tools.add_comment(
        issue_key="PROJ-123",
        comment_text="This is a test comment"
    )
    
    assert result["id"] == "10000"
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_bulk_assign(issues_tools, mock_client):
    """Test bulk assigning issues."""
    mock_client.put.return_value = {}
    
    result = await issues_tools.bulk_assign(
        issue_keys=["PROJ-123", "PROJ-124"],
        account_id="user-123"
    )
    
    assert len(result["results"]) == 2
    assert all(r["status"] in ["success", "error"] for r in result["results"])


@pytest.mark.asyncio
async def test_set_story_points(issues_tools, mock_client):
    """Test setting story points."""
    mock_client.put.return_value = {}
    
    result = await issues_tools.set_story_points(
        issue_key="PROJ-123",
        story_points=5
    )
    
    assert result == {}
    mock_client.put.assert_called_once()

