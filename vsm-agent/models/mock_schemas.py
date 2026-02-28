"""
Mock Management Schemas.
Request/Response models for the mock management API.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class CreateMockRequest:
    """Request to create a mock."""
    mcp_type: str  # "jira" or "confluence"
    operation: str
    request_pattern: Dict[str, Any]
    response: Dict[str, Any]
    description: str = ""
    enabled: bool = True
    priority: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CreateMockRequest":
        return cls(
            mcp_type=data.get("mcpType", ""),
            operation=data.get("operation", ""),
            request_pattern=data.get("requestPattern", {}),
            response=data.get("response", {}),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 0)
        )

    def validate(self) -> List[str]:
        errors = []
        if not self.mcp_type:
            errors.append("mcpType is required")
        elif self.mcp_type not in ["jira", "confluence"]:
            errors.append("mcpType must be 'jira' or 'confluence'")
        if not self.operation:
            errors.append("operation is required")
        if not self.response:
            errors.append("response is required")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mcpType": self.mcp_type,
            "operation": self.operation,
            "requestPattern": self.request_pattern,
            "response": self.response,
            "description": self.description,
            "enabled": self.enabled,
            "priority": self.priority
        }


@dataclass
class UpdateMockRequest:
    """Request to update a mock."""
    response: Optional[Dict[str, Any]] = None
    request_pattern: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UpdateMockRequest":
        return cls(
            response=data.get("response"),
            request_pattern=data.get("requestPattern"),
            description=data.get("description"),
            enabled=data.get("enabled"),
            priority=data.get("priority")
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.response is not None:
            result["response"] = self.response
        if self.request_pattern is not None:
            result["requestPattern"] = self.request_pattern
        if self.description is not None:
            result["description"] = self.description
        if self.enabled is not None:
            result["enabled"] = self.enabled
        if self.priority is not None:
            result["priority"] = self.priority
        return result


@dataclass
class ListMocksRequest:
    """Request to list mocks."""
    mcp_type: Optional[str] = None
    operation: Optional[str] = None
    enabled_only: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ListMocksRequest":
        return cls(
            mcp_type=data.get("mcpType"),
            operation=data.get("operation"),
            enabled_only=data.get("enabledOnly", False)
        )


@dataclass
class ImportMocksRequest:
    """Request to import multiple mocks."""
    mocks: List[Dict[str, Any]]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImportMocksRequest":
        return cls(mocks=data.get("mocks", []))

    def validate(self) -> List[str]:
        errors = []
        if not self.mocks:
            errors.append("mocks array is required and cannot be empty")
        return errors


@dataclass 
class TestMockRequest:
    """Request to test mock matching."""
    mcp_type: str
    operation: str
    request_params: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestMockRequest":
        return cls(
            mcp_type=data.get("mcpType", ""),
            operation=data.get("operation", ""),
            request_params=data.get("requestParams", {})
        )

    def validate(self) -> List[str]:
        errors = []
        if not self.mcp_type:
            errors.append("mcpType is required")
        if not self.operation:
            errors.append("operation is required")
        return errors


# === Response Data Classes ===

@dataclass
class MockData:
    """Mock entry data for responses."""
    mock_id: str
    mcp_type: str
    operation: str
    request_pattern: Dict[str, Any]
    response: Dict[str, Any]
    description: str
    enabled: bool
    priority: int
    created_at: str
    updated_at: str
    created_by: str
    hit_count: int

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


@dataclass
class ListMocksData:
    """List mocks response data."""
    mocks: List[Dict[str, Any]]
    total_count: int
    filtered_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mocks": self.mocks,
            "totalCount": self.total_count,
            "filteredCount": self.filtered_count
        }


@dataclass
class ImportMocksData:
    """Import mocks response data."""
    success_count: int
    error_count: int
    total_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "successCount": self.success_count,
            "errorCount": self.error_count,
            "totalCount": self.total_count
        }


@dataclass
class TestMockData:
    """Test mock matching response data."""
    matched: bool
    mock_id: Optional[str] = None
    mock_description: Optional[str] = None
    response_preview: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"matched": self.matched}
        if self.matched:
            result["mockId"] = self.mock_id
            result["mockDescription"] = self.mock_description
            result["responsePreview"] = self.response_preview
        return result


@dataclass
class MockConfigData:
    """Mock configuration status data."""
    mock_mode_enabled: bool
    mock_table_name: str
    total_mocks: int
    enabled_mocks: int
    jira_mocks: int
    confluence_mocks: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mockModeEnabled": self.mock_mode_enabled,
            "mockTableName": self.mock_table_name,
            "totalMocks": self.total_mocks,
            "enabledMocks": self.enabled_mocks,
            "jiraMocks": self.jira_mocks,
            "confluenceMocks": self.confluence_mocks
        }


@dataclass
class ClearMocksData:
    """Clear mocks response data."""
    deleted_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {"deletedCount": self.deleted_count}


@dataclass
class ResetHitCountsData:
    """Reset hit counts response data."""
    reset_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {"resetCount": self.reset_count}

