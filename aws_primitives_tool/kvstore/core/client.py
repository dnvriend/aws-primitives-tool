"""
DynamoDB client wrapper with error handling.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from typing import Any

import boto3
from botocore.exceptions import ClientError

from ..exceptions import (
    AWSPermissionError,
    AWSThrottlingError,
    ConditionFailedError,
    KVStoreError,
    TableNotFoundError,
)


class DynamoDBClient:
    """DynamoDB client wrapper with error handling."""

    def __init__(
        self,
        table_name: str,
        region: str | None = None,
        profile: str | None = None,
    ):
        """
        Initialize DynamoDB client.

        Args:
            table_name: DynamoDB table name
            region: AWS region (optional, uses SDK default)
            profile: AWS profile (optional, uses SDK default)
        """
        session = boto3.Session(profile_name=profile, region_name=region)
        self.dynamodb = session.resource("dynamodb")
        self.client = session.client("dynamodb")
        self.table = self.dynamodb.Table(table_name)
        self.table_name = table_name

    def put_item(
        self, item: dict[str, Any], condition_expression: str | None = None
    ) -> dict[str, Any]:
        """
        Put item with optional condition.

        Args:
            item: Item to put
            condition_expression: Optional condition expression

        Returns:
            Response from DynamoDB

        Raises:
            ConditionFailedError: If condition fails
            KVStoreError: For other DynamoDB errors
        """
        try:
            kwargs: dict[str, Any] = {"Item": item}
            if condition_expression:
                kwargs["ConditionExpression"] = condition_expression
            return self.table.put_item(**kwargs)  # type: ignore[return-value]
        except ClientError as e:
            self._handle_error(e)
            raise  # For type checker

    def get_item(self, key: dict[str, Any]) -> dict[str, Any] | None:
        """
        Get item by key.

        Args:
            key: Key to retrieve

        Returns:
            Item if found, None otherwise

        Raises:
            KVStoreError: For DynamoDB errors
        """
        try:
            response = self.table.get_item(Key=key)
            return response.get("Item")
        except ClientError as e:
            self._handle_error(e)
            raise  # For type checker

    def delete_item(
        self, key: dict[str, Any], condition_expression: str | None = None
    ) -> dict[str, Any]:
        """
        Delete item with optional condition.

        Args:
            key: Key to delete
            condition_expression: Optional condition expression

        Returns:
            Response from DynamoDB

        Raises:
            ConditionFailedError: If condition fails
            KVStoreError: For other DynamoDB errors
        """
        try:
            kwargs: dict[str, Any] = {"Key": key}
            if condition_expression:
                kwargs["ConditionExpression"] = condition_expression
            return self.table.delete_item(**kwargs)  # type: ignore[return-value]
        except ClientError as e:
            self._handle_error(e)
            raise  # For type checker

    def _handle_error(self, error: ClientError) -> None:
        """
        Convert boto3 errors to kvstore exceptions.

        Args:
            error: ClientError from boto3

        Raises:
            ConditionFailedError: If condition check failed
            TableNotFoundError: If table not found
            AWSThrottlingError: If throttled
            AWSPermissionError: If permission denied
            KVStoreError: For other errors
        """
        code = error.response["Error"]["Code"]

        if code == "ConditionalCheckFailedException":
            raise ConditionFailedError(f"Condition failed: {error}")
        elif code == "ResourceNotFoundException":
            raise TableNotFoundError(f"Table '{self.table_name}' not found")
        elif code == "ProvisionedThroughputExceededException":
            raise AWSThrottlingError("DynamoDB throttling - retry with backoff")
        elif code == "AccessDeniedException":
            raise AWSPermissionError("AWS permission denied")
        else:
            raise KVStoreError(f"DynamoDB error: {error}")
