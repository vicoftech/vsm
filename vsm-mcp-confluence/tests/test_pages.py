"""
Unit tests for Confluence Pages Tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.tools.pages import PagesTools
from src.confluence_client import ConfluenceClient


@pytest.fixture
def mock_client():
    """Create a mock Confluence client."""
    client = MagicMock(spec=ConfluenceClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def pages_tools(mock_client):
    """Create PagesTools instance with mock client."""
    return PagesTools(mock_client)


@pytest.mark.asyncio
async def test_create_page(pages_tools, mock_client):
    """Test creating a page."""
    mock_client.post.return_value = {
        "id": "12345",
        "title": "Test Page",
        "space": {"key": "TEST"}
    }
    
    result = await pages_tools.create_page("TEST", "Test Page", "Page content")
    
    assert result["id"] == "12345"
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args[0][0] == "content"
    assert call_args[1]["json_data"]["title"] == "Test Page"
    assert call_args[1]["json_data"]["space"]["key"] == "TEST"


@pytest.mark.asyncio
async def test_get_page(pages_tools, mock_client):
    """Test getting a page."""
    mock_client.get.return_value = {
        "id": "12345",
        "title": "Test Page",
        "body": {"storage": {"value": "Content"}}
    }
    
    result = await pages_tools.get_page("12345")
    
    assert result["id"] == "12345"
    mock_client.get.assert_called_once()
    call_args = mock_client.get.call_args
    assert call_args[0][0] == "content/12345"
    assert call_args[1]["params"]["expand"] == "body.storage,version,space"


@pytest.mark.asyncio
async def test_update_page(pages_tools, mock_client):
    """Test updating a page."""
    mock_client.put.return_value = {
        "id": "12345",
        "title": "Updated Page",
        "version": {"number": 2}
    }
    
    result = await pages_tools.update_page("12345", "Updated Page", "New content", 1)
    
    assert result["version"]["number"] == 2
    mock_client.put.assert_called_once()
    call_args = mock_client.put.call_args
    assert call_args[0][0] == "content/12345"
    assert call_args[1]["json_data"]["version"]["number"] == 2


@pytest.mark.asyncio
async def test_delete_page(pages_tools, mock_client):
    """Test deleting a page."""
    mock_client.delete.return_value = {}
    
    result = await pages_tools.delete_page("12345")
    
    assert result == {}
    mock_client.delete.assert_called_once_with("content/12345")


@pytest.mark.asyncio
async def test_get_page_content(pages_tools, mock_client):
    """Test getting page content."""
    mock_client.get.return_value = {
        "id": "12345",
        "body": {"storage": {"value": "Page content here"}}
    }
    
    result = await pages_tools.get_page_content("12345")
    
    assert result == "Page content here"
    # get_page_content calls get_page internally, which calls client.get
    assert mock_client.get.call_count >= 1


@pytest.mark.asyncio
async def test_get_pages(pages_tools, mock_client):
    """Test getting pages in a space."""
    mock_client.get.return_value = {
        "results": [
            {"id": "12345", "title": "Page 1"},
            {"id": "12346", "title": "Page 2"}
        ]
    }
    
    result = await pages_tools.get_pages("TEST", limit=25, start=0)
    
    assert len(result["results"]) == 2
    mock_client.get.assert_called_once()
    call_args = mock_client.get.call_args
    assert call_args[0][0] == "content"
    assert call_args[1]["params"]["spaceKey"] == "TEST"

