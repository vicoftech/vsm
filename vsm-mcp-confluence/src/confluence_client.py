"""
Confluence API Client for MCP Lambda.
Handles authentication and HTTP requests to Confluence Cloud API.
"""

import os
import base64
import json
from typing import Dict, Any, Optional
import aiohttp
import boto3
from botocore.exceptions import ClientError


class ConfluenceClient:
    """Client for interacting with Confluence Cloud API."""

    def __init__(
        self,
        domain: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None
    ):
        """
        Initialize Confluence client.
        
        Args:
            domain: Confluence domain (e.g., agentvsm.atlassian.net)
            email: Confluence user email
            api_token: Confluence API token
        """
        # Try to get credentials from Secrets Manager first, then fallback to environment variables
        if not all([domain, email, api_token]):
            secrets = self._get_secrets()
            self.domain = domain or secrets.get("CONFLUENCE_DOMAIN") or os.environ.get("CONFLUENCE_DOMAIN", "")
            self.email = email or secrets.get("CONFLUENCE_EMAIL") or os.environ.get("CONFLUENCE_EMAIL", "")
            self.api_token = api_token or secrets.get("CONFLUENCE_API_TOKEN") or os.environ.get("CONFLUENCE_API_TOKEN", "")
        else:
            self.domain = domain
            self.email = email
            self.api_token = api_token
        
        if not all([self.domain, self.email, self.api_token]):
            raise ValueError(
                "Confluence credentials missing. Set CONFLUENCE_DOMAIN, CONFLUENCE_EMAIL, and CONFLUENCE_API_TOKEN in Secrets Manager or environment variables"
            )
        
        # Create basic auth header
        credentials = f"{self.email}:{self.api_token}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        self.base_url = f"https://{self.domain}"
        self.api_url = f"{self.base_url}/wiki/rest/api"

    def _get_secrets(self) -> Dict[str, str]:
        """
        Get secrets from AWS Secrets Manager.
        Falls back to empty dict if secrets are not available.
        """
        secret_name = os.environ.get("CONFLUENCE_SECRET_NAME", "vsm-mcp-confluence-credentials")
        
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
        Make async HTTP request to Confluence API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to /wiki/rest/api)
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
                response.raise_for_status()
                
                # Handle empty responses
                if response.status == 204:
                    return {}
                
                return await response.json()

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


