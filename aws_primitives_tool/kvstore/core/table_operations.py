"""
Table management operations for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from typing import Any, Literal

import boto3
from botocore.exceptions import ClientError

from ..exceptions import TableAlreadyExistsError, TableNotFoundError


def create_table(
    table_name: str,
    region: str | None = None,
    profile: str | None = None,
    billing_mode: Literal["PAY_PER_REQUEST", "PROVISIONED"] = "PAY_PER_REQUEST",
) -> dict[str, Any]:
    """
    Create DynamoDB table for kvstore.

    Args:
        table_name: Table name
        region: AWS region (optional)
        profile: AWS profile (optional)
        billing_mode: Billing mode (PAY_PER_REQUEST or PROVISIONED)

    Returns:
        Table description

    Raises:
        TableAlreadyExistsError: If table already exists
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    dynamodb = session.client("dynamodb")

    try:
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},  # Partition key
                {"AttributeName": "SK", "KeyType": "RANGE"},  # Sort key
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "type", "AttributeType": "S"},
                {"AttributeName": "updated_at", "AttributeType": "N"},
            ],
            BillingMode=billing_mode,
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI-1",
                    "KeySchema": [
                        {"AttributeName": "type", "KeyType": "HASH"},
                        {"AttributeName": "updated_at", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            Tags=[
                {"Key": "ManagedBy", "Value": "aws-primitives-tool"},
                {"Key": "Purpose", "Value": "kvstore"},
            ],
        )

        # Enable TTL
        dynamodb.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
        )

        return response["TableDescription"]  # type: ignore[return-value]

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            raise TableAlreadyExistsError(f"Table '{table_name}' already exists")
        raise


def drop_table(
    table_name: str, region: str | None = None, profile: str | None = None
) -> dict[str, Any]:
    """
    Drop DynamoDB table.

    Args:
        table_name: Table name
        region: AWS region (optional)
        profile: AWS profile (optional)

    Returns:
        Table description

    Raises:
        TableNotFoundError: If table does not exist
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    dynamodb = session.client("dynamodb")

    try:
        response = dynamodb.delete_table(TableName=table_name)
        return response["TableDescription"]  # type: ignore[return-value]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            raise TableNotFoundError(f"Table '{table_name}' not found")
        raise


def check_table_exists(
    table_name: str, region: str | None = None, profile: str | None = None
) -> bool:
    """
    Check if table exists.

    Args:
        table_name: Table name
        region: AWS region (optional)
        profile: AWS profile (optional)

    Returns:
        True if table exists, False otherwise
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    dynamodb = session.client("dynamodb")

    try:
        dynamodb.describe_table(TableName=table_name)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        raise
