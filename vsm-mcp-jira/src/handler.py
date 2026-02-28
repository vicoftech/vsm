"""
AWS Lambda Handler for Jira MCP.
Exposes Jira MCP tools as HTTP API endpoints.
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

from jira_client import JiraClient
from tools import (
    IssuesTools,
    FiltersTools,
    BoardsTools,
    DashboardsTools,
    ProjectsTools,
    SprintsTools
)


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Tool registry
TOOLS_REGISTRY = {
    # Issues
    "get_issue": ("issues", "get_issue"),
    "search_issues": ("issues", "search_issues"),
    "get_transitions": ("issues", "get_transitions"),
    "transition_issue": ("issues", "transition_issue"),
    "create_epic": ("issues", "create_epic"),
    "create_story": ("issues", "create_story"),
    "create_task": ("issues", "create_task"),
    "create_bug": ("issues", "create_bug"),
    "create_subtask": ("issues", "create_subtask"),
    "update_issue": ("issues", "update_issue"),
    "assign_issue": ("issues", "assign_issue"),
    "add_comment": ("issues", "add_comment"),
    "add_worklog": ("issues", "add_worklog"),
    "link_issues": ("issues", "link_issues"),
    "set_story_points": ("issues", "set_story_points"),
    "add_labels": ("issues", "add_labels"),
    "bulk_assign": ("issues", "bulk_assign"),
    "bulk_transition": ("issues", "bulk_transition"),
    "bulk_add_labels": ("issues", "bulk_add_labels"),
    
    # Filters
    "create_filter": ("filters", "create_filter"),
    "get_filter": ("filters", "get_filter"),
    "search_filters": ("filters", "search_filters"),
    "update_filter": ("filters", "update_filter"),
    "delete_filter": ("filters", "delete_filter"),
    
    # Boards
    "get_boards": ("boards", "get_boards"),
    "create_board": ("boards", "create_board"),
    "get_board": ("boards", "get_board"),
    
    # Dashboards
    "create_dashboard": ("dashboards", "create_dashboard"),
    "get_dashboard": ("dashboards", "get_dashboard"),
    "get_dashboards": ("dashboards", "get_dashboards"),
    "update_dashboard": ("dashboards", "update_dashboard"),
    "delete_dashboard": ("dashboards", "delete_dashboard"),
    
    # Projects
    "get_projects": ("projects", "get_projects"),
    "get_project": ("projects", "get_project"),
    "create_project": ("projects", "create_project"),
    "update_project": ("projects", "update_project"),
    "delete_project": ("projects", "delete_project"),
    "get_project_roles": ("projects", "get_project_roles"),
    "add_user_to_project": ("projects", "add_user_to_project"),
    
    # Sprints
    "get_sprints": ("sprints", "get_sprints"),
    "create_sprint": ("sprints", "create_sprint"),
    "add_to_sprint": ("sprints", "add_to_sprint"),
    "start_sprint": ("sprints", "start_sprint"),
    "complete_sprint": ("sprints", "complete_sprint"),
    "get_sprint": ("sprints", "get_sprint"),
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
    client = JiraClient()
    
    # Initialize tool instance
    if tool_category == "issues":
        tool = IssuesTools(client)
    elif tool_category == "filters":
        tool = FiltersTools(client)
    elif tool_category == "boards":
        tool = BoardsTools(client)
    elif tool_category == "dashboards":
        tool = DashboardsTools(client)
    elif tool_category == "projects":
        tool = ProjectsTools(client)
    elif tool_category == "sprints":
        tool = SprintsTools(client)
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
        "body": "{\"tool\": \"get_issue\", \"params\": {\"issue_key\": \"PROJ-123\"}}"
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
                "service": "vsm-mcp-jira",
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

