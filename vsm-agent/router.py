"""
Internal Router for the VSM Agent Lambda.
Routes requests to appropriate handlers based on path and method.
No external dependencies - pure Python implementation.
Designed for future Bedrock Agent Action Group compatibility.
"""

import re
from typing import Callable, Dict, Any, Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class Route:
    """Represents a route definition."""
    method: str
    path_pattern: str
    handler: Callable
    path_regex: re.Pattern
    path_params: List[str]


class Router:
    """
    Simple HTTP router for Lambda proxy integration.
    
    Features:
    - Path parameter extraction (e.g., /sprint/{sprintId})
    - Method-based routing
    - Prefix support for versioning
    
    Usage:
        router = Router(prefix="/v1/agent")
        router.add_route("POST", "/sprint/plan", handle_sprint_plan)
        router.add_route("GET", "/sprint/{sprintId}/status", handle_sprint_status)
        
        handler, path_params = router.match("POST", "/v1/agent/sprint/plan")
    """

    def __init__(self, prefix: str = ""):
        self.prefix = prefix.rstrip("/")
        self.routes: List[Route] = []

    def _path_to_regex(self, path: str) -> Tuple[re.Pattern, List[str]]:
        """
        Convert a path pattern to a regex pattern.
        Extracts path parameters like {sprintId}.
        
        Returns:
            Tuple of (compiled regex, list of param names)
        """
        param_names = []
        regex_parts = []
        
        # Split path and process each segment
        segments = path.strip("/").split("/")
        
        for segment in segments:
            if segment.startswith("{") and segment.endswith("}"):
                # This is a path parameter
                param_name = segment[1:-1]
                param_names.append(param_name)
                # Match any non-slash characters
                regex_parts.append(r"([^/]+)")
            else:
                # Literal segment - escape any regex special chars
                regex_parts.append(re.escape(segment))
        
        # Build full regex
        full_pattern = "^" + self.prefix + "/" + "/".join(regex_parts) + "$"
        return re.compile(full_pattern), param_names

    def add_route(self, method: str, path: str, handler: Callable) -> None:
        """
        Add a route to the router.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Path pattern (e.g., /sprint/{sprintId}/status)
            handler: Handler function to call
        """
        full_path = self.prefix + path
        path_regex, path_params = self._path_to_regex(path)
        
        route = Route(
            method=method.upper(),
            path_pattern=full_path,
            handler=handler,
            path_regex=path_regex,
            path_params=path_params
        )
        self.routes.append(route)

    def match(self, method: str, path: str) -> Tuple[Optional[Callable], Dict[str, str]]:
        """
        Match a request to a route.
        
        Args:
            method: HTTP method
            path: Request path
            
        Returns:
            Tuple of (handler function or None, dict of path parameters)
        """
        method = method.upper()
        
        for route in self.routes:
            if route.method != method:
                continue
            
            match = route.path_regex.match(path)
            if match:
                # Extract path parameters
                path_params = {}
                for i, param_name in enumerate(route.path_params):
                    path_params[param_name] = match.group(i + 1)
                
                return route.handler, path_params
        
        return None, {}

    def get(self, path: str):
        """Decorator for GET routes."""
        def decorator(func: Callable) -> Callable:
            self.add_route("GET", path, func)
            return func
        return decorator

    def post(self, path: str):
        """Decorator for POST routes."""
        def decorator(func: Callable) -> Callable:
            self.add_route("POST", path, func)
            return func
        return decorator

    def put(self, path: str):
        """Decorator for PUT routes."""
        def decorator(func: Callable) -> Callable:
            self.add_route("PUT", path, func)
            return func
        return decorator

    def delete(self, path: str):
        """Decorator for DELETE routes."""
        def decorator(func: Callable) -> Callable:
            self.add_route("DELETE", path, func)
            return func
        return decorator


# === Request/Response Helpers ===

@dataclass
class RequestContext:
    """Context for handling a request."""
    method: str
    path: str
    headers: Dict[str, str]
    query_params: Dict[str, str]
    path_params: Dict[str, str]
    body: Optional[Dict[str, Any]]
    trace_id: str
    correlation_id: str
    tenant_id: str
    raw_event: Dict[str, Any]


def extract_header(headers: Dict[str, str], name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Extract a header value (case-insensitive).
    
    API Gateway may normalize header names to lowercase.
    """
    # Try exact match first
    if name in headers:
        return headers[name]
    
    # Try lowercase
    name_lower = name.lower()
    if name_lower in headers:
        return headers[name_lower]
    
    # Try case-insensitive search
    for key, value in headers.items():
        if key.lower() == name_lower:
            return value
    
    return default


def build_response(status_code: int, body: Dict[str, Any], 
                   headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Build an API Gateway proxy response.
    
    Args:
        status_code: HTTP status code
        body: Response body (will be JSON serialized)
        headers: Additional headers
        
    Returns:
        API Gateway proxy response dict
    """
    import json
    

    response_headers = {
        "Content-Type": "application/json",
        "X-Content-Type-Options": "nosniff",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
    }
    
    if headers:
        response_headers.update(headers)
    
    return {
        "statusCode": status_code,
        "headers": response_headers,
        "body": json.dumps(body, ensure_ascii=False)
    }


def build_error_response(status_code: int, error_code: str, message: str,
                         trace_id: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Build an error response.
    
    Args:
        status_code: HTTP status code
        error_code: Error code from ErrorCode enum
        message: Human-readable error message
        trace_id: Request trace ID
        details: Additional error details
        
    Returns:
        API Gateway proxy response dict
    """
    body = {
        "error": {
            "code": error_code,
            "message": message,
            "details": details or {}
        },
        "traceId": trace_id
    }
    
    return build_response(status_code, body)


# === Common HTTP Status Responses ===

def bad_request(message: str, trace_id: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """400 Bad Request response."""
    return build_error_response(400, "VALIDATION_ERROR", message, trace_id, details)


def unauthorized(message: str, trace_id: str) -> Dict[str, Any]:
    """401 Unauthorized response."""
    return build_error_response(401, "AUTHENTICATION_ERROR", message, trace_id)


def forbidden(message: str, trace_id: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """403 Forbidden response."""
    return build_error_response(403, "AUTHORIZATION_ERROR", message, trace_id, details)


def not_found(resource: str, trace_id: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """404 Not Found response."""
    return build_error_response(404, f"{resource.upper()}_NOT_FOUND", f"{resource} not found", trace_id, details)


def internal_error(trace_id: str, message: str = "An unexpected error occurred") -> Dict[str, Any]:
    """500 Internal Server Error response."""
    return build_error_response(500, "INTERNAL_ERROR", message, trace_id)

