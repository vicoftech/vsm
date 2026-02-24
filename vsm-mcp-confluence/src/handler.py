"""
AWS Lambda Handler for Confluence MCP.
Exposes Confluence MCP tools as HTTP API endpoints.
"""

import json
import logging
import traceback
from typing import Dict, Any, Optional
import asyncio

import sys
import os

# Add current directory to path for Lambda packaging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from confluence_client import ConfluenceClient
from tools import (
    PagesTools,
    SpacesTools,
    SearchTools,
    LabelsTools
)


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Tool registry
TOOLS_REGISTRY = {
    # Pages
    "create_page": ("pages", "create_page"),
    "update_page": ("pages", "update_page"),
    "get_page": ("pages", "get_page"),
    "get_page_content": ("pages", "get_page_content"),
    "delete_page": ("pages", "delete_page"),
    "get_pages": ("pages", "get_pages"),
    
    # Spaces
    "get_spaces": ("spaces", "get_spaces"),
    "get_space": ("spaces", "get_space"),
    "create_space": ("spaces", "create_space"),
    
    # Search
    "search_cql": ("search", "search_cql"),
    "search_by_title": ("search", "search_by_title"),
    "search_by_label": ("search", "search_by_label"),
    
    # Labels
    "add_labels": ("labels", "add_labels"),
    "get_labels": ("labels", "get_labels"),
    "remove_label": ("labels", "remove_label")
}


def build_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Build API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
        },
        "body": json.dumps(body)
    }


def build_error_response(status_code: int, error: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """Build error response."""
    body = {"error": error}
    if details:
        body["details"] = details
    return build_response(status_code, body)


async def execute_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool by name.
    
    Args:
        tool_name: Name of the tool to execute
        params: Tool parameters
        
    Returns:
        Tool execution result
    """
    if tool_name not in TOOLS_REGISTRY:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    tool_category, method_name = TOOLS_REGISTRY[tool_name]
    
    # Initialize client
    client = ConfluenceClient()
    
    # Initialize tool instance
    if tool_category == "pages":
        tool = PagesTools(client)
    elif tool_category == "spaces":
        tool = SpacesTools(client)
    elif tool_category == "search":
        tool = SearchTools(client)
    elif tool_category == "labels":
        tool = LabelsTools(client)
    else:
        raise ValueError(f"Unknown tool category: {tool_category}")
    
    # Get method and execute
    method = getattr(tool, method_name)
    result = await method(**params)
    
    return result


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda entry point.
    
    Expected event format (API Gateway HTTP API):
    {
        "requestContext": {
            "http": {
                "method": "POST",
                "path": "/tool"
            }
        },
        "body": "{\"tool\": \"get_page\", \"params\": {\"page_id\": \"12345\"}}"
    }
    """
    try:
        # Parse request
        method = event.get("requestContext", {}).get("http", {}).get("method", "POST")
        path = event.get("requestContext", {}).get("http", {}).get("path", "/")
        
        # Handle OPTIONS for CORS
        if method == "OPTIONS":
            return build_response(200, {"message": "OK"})
        
        # Parse body
        body_str = event.get("body", "{}")
        if isinstance(body_str, str):
            try:
                body = json.loads(body_str)
            except json.JSONDecodeError:
                return build_error_response(400, "Invalid JSON body")
        else:
            body = body_str
        
        # Health check
        if path == "/health" or (path == "/" and method == "GET"):
            return build_response(200, {
                "status": "healthy",
                "service": "vsm-mcp-confluence",
                "tools_available": len(TOOLS_REGISTRY)
            })
        
        # Tool execution
        if path == "/tool" or path == "/execute":
            tool_name = body.get("tool")
            params = body.get("params", {})
            
            if not tool_name:
                return build_error_response(400, "Missing 'tool' parameter")
            
            # Execute tool asynchronously
            try:
                result = asyncio.run(execute_tool(tool_name, params))
                return build_response(200, {
                    "success": True,
                    "tool": tool_name,
                    "result": result
                })
            except ValueError as e:
                return build_error_response(400, str(e))
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                logger.error(traceback.format_exc())
                return build_error_response(500, "Tool execution failed", {"error": str(e)})
        
        # List available tools
        if path == "/tools" and method == "GET":
            return build_response(200, {
                "tools": list(TOOLS_REGISTRY.keys()),
                "count": len(TOOLS_REGISTRY)
            })
        
        # Unknown path
        return build_error_response(404, f"Path not found: {path}")
        
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        logger.error(traceback.format_exc())
        return build_error_response(500, "Internal server error", {"error": str(e)})


