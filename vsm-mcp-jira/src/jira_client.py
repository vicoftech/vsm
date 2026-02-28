"""
Jira API Client for MCP Lambda.
Handles authentication and HTTP requests to Jira Cloud API.
"""

import os
import base64
import json
from typing import Dict, Any, Optional, List
import aiohttp
import requests
import boto3
from botocore.exceptions import ClientError


class JiraClient:
    """Client for interacting with Jira Cloud API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None
    ):
        """
        Initialize Jira client.
        
        Args:
            base_url: Jira base URL (e.g., https://agentvsm.atlassian.net)
            email: Jira user email
            api_token: Jira API token
        """
        # Try to get credentials from Secrets Manager first, then fallback to environment variables
        if not all([base_url, email, api_token]):
            secrets = self._get_secrets()
            self.base_url = base_url or secrets.get("JIRA_BASE_URL") or os.environ.get("JIRA_BASE_URL", "").rstrip("/")
            self.email = email or secrets.get("JIRA_EMAIL") or os.environ.get("JIRA_EMAIL", "")
            self.api_token = api_token or secrets.get("JIRA_API_TOKEN") or os.environ.get("JIRA_API_TOKEN", "")
        else:
            self.base_url = base_url.rstrip("/")
            self.email = email
            self.api_token = api_token
        
        if not all([self.base_url, self.email, self.api_token]):
            raise ValueError(
                "Jira credentials missing. Set JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN in Secrets Manager or environment variables"
            )
        
        # Create basic auth header
        credentials = f"{self.email}:{self.api_token}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        self.api_url = f"{self.base_url}/rest/api/3"
        self.agile_api_url = f"{self.base_url}/rest/agile/1.0"

    def _get_secrets(self) -> Dict[str, str]:
        """
        Get secrets from AWS Secrets Manager.
        Falls back to empty dict if secrets are not available.
        """
        secret_name = os.environ.get("JIRA_SECRET_NAME", "vsm-mcp-jira-credentials")
        
        try:
            client = boto3.client("secretsmanager")
            response = client.get_secret_value(SecretId=secret_name)
            secret = json.loads(response["SecretString"])
            return secret
        except (ClientError, json.JSONDecodeError, KeyError) as e:
            # If secrets manager fails, return empty dict to fallback to env vars
            return {}

    async def _request_async(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make async HTTP request to Jira API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to /rest/api/3)
            params: Query parameters
            json_data: JSON body for POST/PUT
            
        Returns:
            Response JSON data
            
        Raises:
            Exception: If request fails
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=json_data
            ) as response:
                # Handle empty responses first
                if response.status == 204:
                    return {}
                
                # Read response body
                try:
                    if response.content_type and 'application/json' in response.content_type:
                        response_body = await response.json()
                    else:
                        response_body = await response.text()
                except Exception:
                    response_body = await response.text() if response.content else None
                
                # If there's an error, include the response body in the exception
                if response.status >= 400:
                    error_msg = f"{response.status}, message='{response.reason}', url='{url}'"
                    if response_body:
                        if isinstance(response_body, dict):
                            # Include Jira's error messages if available
                            error_details = response_body.get("errorMessages", []) or response_body.get("errors", {})
                            if error_details:
                                error_msg += f", response={json.dumps(response_body, ensure_ascii=False)}"
                            else:
                                # Include full response if no specific error messages found
                                error_msg += f", response={json.dumps(response_body, ensure_ascii=False)}"
                        else:
                            error_msg += f", response={response_body}"
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=error_msg,
                        headers=response.headers
                    )
                
                # Return successful response
                return response_body if isinstance(response_body, dict) else {}

    def _request_sync(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make synchronous HTTP request to Jira API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to /rest/api/3)
            params: Query parameters
            json_data: JSON body for POST/PUT
            
        Returns:
            Response JSON data
            
        Raises:
            Exception: If request fails
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            params=params,
            json=json_data
        )
        
        response.raise_for_status()
        
        # Handle empty responses
        if response.status_code == 204:
            return {}
        
        return response.json()

    # Convenience methods
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET request."""
        return await self._request_async("GET", endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """POST request."""
        return await self._request_async("POST", endpoint, json_data=json_data, params=params)

    async def put(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """PUT request."""
        return await self._request_async("PUT", endpoint, json_data=json_data, params=params)

    async def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """DELETE request."""
        return await self._request_async("DELETE", endpoint, params=params)

    def get_sync(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Synchronous GET request."""
        return self._request_sync("GET", endpoint, params=params)

    def post_sync(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Synchronous POST request."""
        return self._request_sync("POST", endpoint, json_data=json_data, params=params)

    def put_sync(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Synchronous PUT request."""
        return self._request_sync("PUT", endpoint, json_data=json_data, params=params)

    def delete_sync(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Synchronous DELETE request."""
        return self._request_sync("DELETE", endpoint, params=params)

    # Agile API methods (for boards, sprints, etc.)
    async def get_agile(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET request to Agile API."""
        url = f"{self.agile_api_url}/{endpoint.lstrip('/')}"
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method="GET",
                url=url,
                headers=self.headers,
                params=params
            ) as response:
                # Read response body before raising for status
                try:
                    if response.content_type and 'application/json' in response.content_type:
                        response_body = await response.json()
                    else:
                        response_body = await response.text()
                except Exception:
                    response_body = await response.text() if response.content else None
                
                if response.status >= 400:
                    error_msg = f"{response.status}, message='{response.reason}', url='{url}'"
                    if response_body:
                        if isinstance(response_body, dict):
                            error_details = response_body.get("errorMessages", []) or response_body.get("errors", {})
                            if error_details:
                                error_msg += f", response={json.dumps(response_body, ensure_ascii=False)}"
                            else:
                                error_msg += f", response={json.dumps(response_body, ensure_ascii=False)}"
                        else:
                            error_msg += f", response={response_body}"
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=error_msg,
                        headers=response.headers
                    )
                
                if response.status == 204:
                    return {}
                
                return response_body if isinstance(response_body, dict) else {}

    async def post_agile(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """POST request to Agile API."""
        url = f"{self.agile_api_url}/{endpoint.lstrip('/')}"
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method="POST",
                url=url,
                headers=self.headers,
                params=params,
                json=json_data
            ) as response:
                try:
                    if response.content_type and 'application/json' in response.content_type:
                        response_body = await response.json()
                    else:
                        response_body = await response.text()
                except Exception:
                    response_body = await response.text() if response.content else None
                
                if response.status >= 400:
                    error_msg = f"{response.status}, message='{response.reason}', url='{url}'"
                    if response_body:
                        if isinstance(response_body, dict):
                            error_details = response_body.get("errorMessages", []) or response_body.get("errors", {})
                            if error_details:
                                error_msg += f", response={json.dumps(response_body, ensure_ascii=False)}"
                            else:
                                error_msg += f", response={json.dumps(response_body, ensure_ascii=False)}"
                        else:
                            error_msg += f", response={response_body}"
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=error_msg,
                        headers=response.headers
                    )
                
                if response.status == 204:
                    return {}
                
                return response_body if isinstance(response_body, dict) else {}

    async def put_agile(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """PUT request to Agile API."""
        url = f"{self.agile_api_url}/{endpoint.lstrip('/')}"
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method="PUT",
                url=url,
                headers=self.headers,
                params=params,
                json=json_data
            ) as response:
                try:
                    if response.content_type and 'application/json' in response.content_type:
                        response_body = await response.json()
                    else:
                        response_body = await response.text()
                except Exception:
                    response_body = await response.text() if response.content else None
                
                if response.status >= 400:
                    error_msg = f"{response.status}, message='{response.reason}', url='{url}'"
                    if response_body:
                        if isinstance(response_body, dict):
                            error_details = response_body.get("errorMessages", []) or response_body.get("errors", {})
                            if error_details:
                                error_msg += f", response={json.dumps(response_body, ensure_ascii=False)}"
                            else:
                                error_msg += f", response={json.dumps(response_body, ensure_ascii=False)}"
                        else:
                            error_msg += f", response={response_body}"
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=error_msg,
                        headers=response.headers
                    )
                
                if response.status == 204:
                    return {}
                
                return response_body if isinstance(response_body, dict) else {}


