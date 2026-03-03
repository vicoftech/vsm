"""
Thin DynamoDB helper layer for Agent Core repositories.

We deliberately avoid external ORMs and keep this as a minimal wrapper
around low-level boto3 clients, to keep cold start time low.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

try:
    import boto3
    from botocore.exceptions import ClientError

    _BOTO3_AVAILABLE = True
except ImportError:  # pragma: no cover - local dev without AWS SDK
    boto3 = None  # type: ignore
    ClientError = Exception  # type: ignore
    _BOTO3_AVAILABLE = False


class DynamoClient:
    """
    Lazy-initialized DynamoDB client.

    Falls back to a no-op in environments where boto3 is not available
    (e.g., local unit tests), so that the rest of the code can still run.
    """

    _client = None

    @classmethod
    def client(cls):
        if cls._client is None and _BOTO3_AVAILABLE:
            region = os.getenv("AWS_REGION", "us-east-1")
            cls._client = boto3.client("dynamodb", region_name=region)
        return cls._client


def put_item(table_name: str, item: Dict[str, Any]) -> None:
    """
    Best-effort write.

    If the table does not exist or there is any DynamoDB error, we
    swallow it so that observability features (audit, traces, tokens)
    never rompan el flujo principal del agente.
    """
    client = DynamoClient.client()
    if not client:
        return
    try:
        client.put_item(TableName=table_name, Item=item)
    except ClientError:
        # Non-critical for the main agent flow
        return


def get_item(table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    client = DynamoClient.client()
    if not client:
        return None
    try:
        resp = client.get_item(TableName=table_name, Key=key)
    except ClientError:
        return None
    return resp.get("Item")


def update_item(
    table_name: str,
    key: Dict[str, Any],
    update_expression: str,
    expression_values: Dict[str, Any],
) -> None:
    client = DynamoClient.client()
    if not client:
        return
    try:
        client.update_item(
            TableName=table_name,
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
        )
    except ClientError:
        # Treat as best-effort
        return


def query_items(
    table_name: str,
    key_condition_expression: str,
    expression_attribute_values: Dict[str, Any],
    limit: Optional[int] = None,
    scan_index_forward: bool = True,
) -> List[Dict[str, Any]]:
    """
    Best-effort Query wrapper.

    Args:
        table_name: DynamoDB table name
        key_condition_expression: KeyConditionExpression string
        expression_attribute_values: ExpressionAttributeValues dict
        limit: Optional maximum number of items
        scan_index_forward: Sort order on range key
    """
    client = DynamoClient.client()
    if not client:
        return []

    try:
        params: Dict[str, Any] = {
            "TableName": table_name,
            "KeyConditionExpression": key_condition_expression,
            "ExpressionAttributeValues": expression_attribute_values,
            "ScanIndexForward": scan_index_forward,
        }
        if limit is not None:
            params["Limit"] = limit

        resp = client.query(**params)
        return resp.get("Items", [])
    except ClientError:
        return []



