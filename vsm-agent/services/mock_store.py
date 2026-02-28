"""
Mock Store Service.
Manages mock responses stored in DynamoDB for testing purposes.
When MOCK_MODE is enabled, MCP services will use stored mocks instead of simulated responses.
"""

import json
import os
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

# Check if running in AWS Lambda with boto3 available
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    ClientError = Exception


@dataclass
class MockEntry:
    """Represents a mock entry."""
    mock_id: str
    mcp_type: str  # "jira" or "confluence"
    operation: str
    request_pattern: Dict[str, Any]  # Pattern to match requests
    response: Dict[str, Any]
    description: str = ""
    enabled: bool = True
    priority: int = 0  # Higher priority mocks are matched first
    created_at: str = ""
    updated_at: str = ""
    created_by: str = ""
    hit_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mockId": self.mock_id,
            "mcpType": self.mcp_type,
            "operation": self.operation,
            "requestPattern": self.request_pattern,
            "response": self.response,
            "description": self.description,
            "enabled": self.enabled,
            "priority": self.priority,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "createdBy": self.created_by,
            "hitCount": self.hit_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MockEntry":
        return cls(
            mock_id=data.get("mockId", ""),
            mcp_type=data.get("mcpType", ""),
            operation=data.get("operation", ""),
            request_pattern=data.get("requestPattern", {}),
            response=data.get("response", {}),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 0),
            created_at=data.get("createdAt", ""),
            updated_at=data.get("updatedAt", ""),
            created_by=data.get("createdBy", ""),
            hit_count=data.get("hitCount", 0)
        )

    @classmethod
    def from_dynamodb(cls, item: Dict[str, Any]) -> "MockEntry":
        """Create MockEntry from DynamoDB item format."""
        return cls(
            mock_id=item.get("mock_id", {}).get("S", ""),
            mcp_type=item.get("mcp_type", {}).get("S", ""),
            operation=item.get("operation", {}).get("S", ""),
            request_pattern=json.loads(item.get("request_pattern", {}).get("S", "{}")),
            response=json.loads(item.get("response", {}).get("S", "{}")),
            description=item.get("description", {}).get("S", ""),
            enabled=item.get("enabled", {}).get("BOOL", True),
            priority=int(item.get("priority", {}).get("N", "0")),
            created_at=item.get("created_at", {}).get("S", ""),
            updated_at=item.get("updated_at", {}).get("S", ""),
            created_by=item.get("created_by", {}).get("S", ""),
            hit_count=int(item.get("hit_count", {}).get("N", "0"))
        )

    def to_dynamodb(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        return {
            "mock_id": {"S": self.mock_id},
            "mcp_type": {"S": self.mcp_type},
            "operation": {"S": self.operation},
            "request_pattern": {"S": json.dumps(self.request_pattern)},
            "response": {"S": json.dumps(self.response)},
            "description": {"S": self.description},
            "enabled": {"BOOL": self.enabled},
            "priority": {"N": str(self.priority)},
            "created_at": {"S": self.created_at},
            "updated_at": {"S": self.updated_at},
            "created_by": {"S": self.created_by},
            "hit_count": {"N": str(self.hit_count)},
            # GSI sort key for querying by mcp_type and operation
            "mcp_operation": {"S": f"{self.mcp_type}#{self.operation}"}
        }


def generate_mock_id(mcp_type: str, operation: str, request_pattern: Dict[str, Any]) -> str:
    """Generate a unique mock ID based on the mock configuration."""
    pattern_str = json.dumps(request_pattern, sort_keys=True)
    content = f"{mcp_type}:{operation}:{pattern_str}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def is_mock_mode_enabled() -> bool:
    """Check if mock mode is enabled via environment variable."""
    return os.environ.get("MOCK_MODE", "true").lower() == "true"


def get_mock_table_name() -> str:
    """Get the DynamoDB table name for mocks."""
    return os.environ.get("MOCK_TABLE_NAME", "vsm-agent-mocks")


class MockStoreService:
    """
    Service for managing mock responses in DynamoDB.
    
    Table Schema:
    - PK: mock_id (string)
    - GSI: mcp_operation-index
      - PK: mcp_operation (string) - format: "{mcp_type}#{operation}"
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.table_name = get_mock_table_name()
        self._client = None
        self._local_cache: Dict[str, MockEntry] = {}
        self._use_local_cache = not BOTO3_AVAILABLE or os.environ.get("USE_LOCAL_MOCK_CACHE", "false").lower() == "true"

    @property
    def client(self):
        """Lazy initialization of DynamoDB client."""
        if self._client is None and BOTO3_AVAILABLE:
            self._client = boto3.client("dynamodb")
        return self._client

    # === CRUD Operations ===

    def create_mock(self, mock_data: Dict[str, Any], created_by: str = "api") -> MockEntry:
        """
        Create a new mock entry.
        
        Args:
            mock_data: Mock configuration
            created_by: Creator identifier
            
        Returns:
            Created MockEntry
        """
        now = datetime.utcnow().isoformat() + "Z"
        
        mock_id = mock_data.get("mockId") or generate_mock_id(
            mock_data.get("mcpType", ""),
            mock_data.get("operation", ""),
            mock_data.get("requestPattern", {})
        )
        
        entry = MockEntry(
            mock_id=mock_id,
            mcp_type=mock_data.get("mcpType", ""),
            operation=mock_data.get("operation", ""),
            request_pattern=mock_data.get("requestPattern", {}),
            response=mock_data.get("response", {}),
            description=mock_data.get("description", ""),
            enabled=mock_data.get("enabled", True),
            priority=mock_data.get("priority", 0),
            created_at=now,
            updated_at=now,
            created_by=created_by,
            hit_count=0
        )
        
        if self._use_local_cache:
            self._local_cache[mock_id] = entry
        else:
            self.client.put_item(
                TableName=self.table_name,
                Item=entry.to_dynamodb()
            )
        
        return entry

    def get_mock(self, mock_id: str) -> Optional[MockEntry]:
        """Get a mock entry by ID."""
        if self._use_local_cache:
            return self._local_cache.get(mock_id)
        
        try:
            response = self.client.get_item(
                TableName=self.table_name,
                Key={"mock_id": {"S": mock_id}}
            )
            
            if "Item" in response:
                return MockEntry.from_dynamodb(response["Item"])
            return None
            
        except ClientError:
            return None

    def update_mock(self, mock_id: str, updates: Dict[str, Any]) -> Optional[MockEntry]:
        """Update an existing mock entry."""
        existing = self.get_mock(mock_id)
        if not existing:
            return None
        
        now = datetime.utcnow().isoformat() + "Z"
        
        # Apply updates
        if "response" in updates:
            existing.response = updates["response"]
        if "requestPattern" in updates:
            existing.request_pattern = updates["requestPattern"]
        if "description" in updates:
            existing.description = updates["description"]
        if "enabled" in updates:
            existing.enabled = updates["enabled"]
        if "priority" in updates:
            existing.priority = updates["priority"]
        
        existing.updated_at = now
        
        if self._use_local_cache:
            self._local_cache[mock_id] = existing
        else:
            self.client.put_item(
                TableName=self.table_name,
                Item=existing.to_dynamodb()
            )
        
        return existing

    def delete_mock(self, mock_id: str) -> bool:
        """Delete a mock entry."""
        if self._use_local_cache:
            if mock_id in self._local_cache:
                del self._local_cache[mock_id]
                return True
            return False
        
        try:
            self.client.delete_item(
                TableName=self.table_name,
                Key={"mock_id": {"S": mock_id}}
            )
            return True
        except ClientError:
            return False

    def list_mocks(self, mcp_type: Optional[str] = None, 
                   operation: Optional[str] = None,
                   enabled_only: bool = False) -> List[MockEntry]:
        """
        List mock entries with optional filters.
        
        Args:
            mcp_type: Filter by MCP type (jira, confluence)
            operation: Filter by operation
            enabled_only: Only return enabled mocks
            
        Returns:
            List of MockEntry
        """
        if self._use_local_cache:
            mocks = list(self._local_cache.values())
            
            if mcp_type:
                mocks = [m for m in mocks if m.mcp_type == mcp_type]
            if operation:
                mocks = [m for m in mocks if m.operation == operation]
            if enabled_only:
                mocks = [m for m in mocks if m.enabled]
            
            return sorted(mocks, key=lambda m: -m.priority)
        
        try:
            # Use GSI if filtering by mcp_type and operation
            if mcp_type and operation:
                response = self.client.query(
                    TableName=self.table_name,
                    IndexName="mcp_operation-index",
                    KeyConditionExpression="mcp_operation = :mo",
                    ExpressionAttributeValues={
                        ":mo": {"S": f"{mcp_type}#{operation}"}
                    }
                )
            else:
                # Full scan (not ideal for large datasets)
                response = self.client.scan(TableName=self.table_name)
            
            mocks = [MockEntry.from_dynamodb(item) for item in response.get("Items", [])]
            
            # Apply remaining filters
            if mcp_type and not operation:
                mocks = [m for m in mocks if m.mcp_type == mcp_type]
            if enabled_only:
                mocks = [m for m in mocks if m.enabled]
            
            return sorted(mocks, key=lambda m: -m.priority)
            
        except ClientError:
            return []

    # === Mock Matching ===

    def find_matching_mock(self, mcp_type: str, operation: str, 
                           request_params: Dict[str, Any]) -> Optional[MockEntry]:
        """
        Find a mock that matches the given request.
        
        Matching rules:
        1. mcp_type must match exactly
        2. operation must match exactly
        3. All keys in requestPattern must exist in request_params with matching values
        4. If multiple mocks match, return the one with highest priority
        
        Args:
            mcp_type: MCP type (jira, confluence)
            operation: Operation name
            request_params: Request parameters to match against
            
        Returns:
            Matching MockEntry or None
        """
        mocks = self.list_mocks(mcp_type=mcp_type, operation=operation, enabled_only=True)
        
        for mock in mocks:  # Already sorted by priority descending
            if self._matches_pattern(mock.request_pattern, request_params):
                # Increment hit count (async in production)
                self._increment_hit_count(mock.mock_id)
                return mock
        
        return None

    def _matches_pattern(self, pattern: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """
        Check if params match the pattern.
        
        Pattern matching rules:
        - Empty pattern matches everything
        - "*" as a value matches any value
        - Nested objects are matched recursively
        - Arrays match if all pattern elements exist in params array
        """
        if not pattern:
            return True
        
        for key, pattern_value in pattern.items():
            if key not in params:
                return False
            
            param_value = params[key]
            
            # Wildcard matches anything
            if pattern_value == "*":
                continue
            
            # Recursive matching for nested objects
            if isinstance(pattern_value, dict) and isinstance(param_value, dict):
                if not self._matches_pattern(pattern_value, param_value):
                    return False
            # Array matching
            elif isinstance(pattern_value, list) and isinstance(param_value, list):
                for pv in pattern_value:
                    if pv not in param_value:
                        return False
            # Direct comparison
            elif pattern_value != param_value:
                return False
        
        return True

    def _increment_hit_count(self, mock_id: str) -> None:
        """Increment the hit count for a mock."""
        if self._use_local_cache:
            if mock_id in self._local_cache:
                self._local_cache[mock_id].hit_count += 1
        else:
            try:
                self.client.update_item(
                    TableName=self.table_name,
                    Key={"mock_id": {"S": mock_id}},
                    UpdateExpression="SET hit_count = hit_count + :inc",
                    ExpressionAttributeValues={":inc": {"N": "1"}}
                )
            except ClientError:
                pass  # Non-critical operation

    # === Bulk Operations ===

    def import_mocks(self, mocks: List[Dict[str, Any]], created_by: str = "import") -> Tuple[int, int]:
        """
        Import multiple mocks.
        
        Args:
            mocks: List of mock configurations
            created_by: Creator identifier
            
        Returns:
            Tuple of (success_count, error_count)
        """
        success = 0
        errors = 0
        
        for mock_data in mocks:
            try:
                self.create_mock(mock_data, created_by)
                success += 1
            except Exception:
                errors += 1
        
        return success, errors

    def export_mocks(self, mcp_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Export mocks as a list of dictionaries.
        
        Args:
            mcp_type: Optional filter by MCP type
            
        Returns:
            List of mock dictionaries
        """
        mocks = self.list_mocks(mcp_type=mcp_type)
        return [m.to_dict() for m in mocks]

    def clear_all_mocks(self) -> int:
        """
        Delete all mocks. Use with caution!
        
        Returns:
            Number of mocks deleted
        """
        if self._use_local_cache:
            count = len(self._local_cache)
            self._local_cache.clear()
            return count
        
        mocks = self.list_mocks()
        count = 0
        
        for mock in mocks:
            if self.delete_mock(mock.mock_id):
                count += 1
        
        return count

    def reset_hit_counts(self) -> int:
        """Reset hit counts for all mocks."""
        mocks = self.list_mocks()
        count = 0
        
        for mock in mocks:
            mock.hit_count = 0
            if self._use_local_cache:
                self._local_cache[mock.mock_id] = mock
                count += 1
            else:
                try:
                    self.client.update_item(
                        TableName=self.table_name,
                        Key={"mock_id": {"S": mock.mock_id}},
                        UpdateExpression="SET hit_count = :zero",
                        ExpressionAttributeValues={":zero": {"N": "0"}}
                    )
                    count += 1
                except ClientError:
                    pass
        
        return count


# === Pre-built Mock Templates ===

def get_default_jira_mocks() -> List[Dict[str, Any]]:
    """Get default Jira mock templates."""
    return [
        {
            "mcpType": "jira",
            "operation": "search_issues",
            "requestPattern": {"projectKey": "DEMO"},
            "response": [
                {
                    "key": "DEMO-1",
                    "summary": "Demo issue for testing",
                    "status": "To Do",
                    "storyPoints": 5,
                    "assignee": "demo.user@example.com",
                    "type": "Story",
                    "hasAcceptanceCriteria": True
                }
            ],
            "description": "Default mock for DEMO project search",
            "priority": 10
        },
        {
            "mcpType": "jira",
            "operation": "get_sprint",
            "requestPattern": {},
            "response": {
                "id": "999",
                "name": "Mock Sprint",
                "state": "active",
                "startDate": "2026-02-24",
                "endDate": "2026-03-09",
                "goal": "Demo sprint for testing"
            },
            "description": "Default mock for get_sprint",
            "priority": 1
        }
    ]


def get_default_confluence_mocks() -> List[Dict[str, Any]]:
    """Get default Confluence mock templates."""
    return [
        {
            "mcpType": "confluence",
            "operation": "create_page",
            "requestPattern": {},
            "response": {
                "id": "9999",
                "title": "Mock Page",
                "spaceKey": "MOCK",
                "version": 1,
                "url": "https://confluence.example.com/display/MOCK/Mock+Page",
                "createdAt": "2026-02-24T10:00:00Z"
            },
            "description": "Default mock for page creation",
            "priority": 1
        }
    ]

