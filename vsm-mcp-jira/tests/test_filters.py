"""
Unit tests for Jira Filters Tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.tools.filters import FiltersTools
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
def filters_tools(mock_client):
    """Create FiltersTools instance with mock client."""
    return FiltersTools(mock_client)


@pytest.mark.asyncio
async def test_create_filter(filters_tools, mock_client):
    """Test creating a filter."""
    mock_client.post.return_value = {
        "id": "10000",
        "name": "My Filter",
        "jql": "project = PROJ"
    }
    
    result = await filters_tools.create_filter(
        name="My Filter",
        jql="project = PROJ",
        description="Test filter"
    )
    
    assert result["id"] == "10000"
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_get_filter(filters_tools, mock_client):
    """Test getting a filter."""
    mock_client.get.return_value = {
        "id": "10000",
        "name": "My Filter",
        "jql": "project = PROJ"
    }
    
    result = await filters_tools.get_filter("10000")
    
    assert result["id"] == "10000"
    mock_client.get.assert_called_once_with("filter/10000")


@pytest.mark.asyncio
async def test_search_filters(filters_tools, mock_client):
    """Test searching filters."""
    mock_client.get.return_value = {
        "values": [
            {"id": "10000", "name": "Filter 1"},
            {"id": "10001", "name": "Filter 2"}
        ]
    }
    
    result = await filters_tools.search_filters(filter_name="Filter")
    
    assert len(result["values"]) == 2
    mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_update_filter(filters_tools, mock_client):
    """Test updating a filter."""
    mock_client.put.return_value = {
        "id": "10000",
        "name": "Updated Filter"
    }
    
    result = await filters_tools.update_filter(
        filter_id="10000",
        name="Updated Filter"
    )
    
    assert result["name"] == "Updated Filter"
    mock_client.put.assert_called_once()


@pytest.mark.asyncio
async def test_delete_filter(filters_tools, mock_client):
    """Test deleting a filter."""
    mock_client.delete.return_value = {}
    
    result = await filters_tools.delete_filter("10000")
    
    assert result == {}
    mock_client.delete.assert_called_once_with("filter/10000")


