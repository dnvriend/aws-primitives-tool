"""
Status operations for kvstore - DynamoDB table health and CloudWatch metrics.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from datetime import datetime, timedelta
from typing import Any

import boto3
from botocore.exceptions import ClientError

from ..exceptions import KVStoreError, TableNotFoundError


def get_table_status(
    table_name: str,
    region: str | None = None,
    profile: str | None = None
) -> dict[str, Any]:
    """Get DynamoDB table status, CloudWatch metrics, and cost estimates.

    Returns table configuration, metrics, and capacity information.
    """
    # Create session with profile if provided
    session = boto3.Session(profile_name=profile, region_name=region)
    dynamodb = session.client("dynamodb")
    cloudwatch = session.client("cloudwatch")

    try:
        # Get table description
        response = dynamodb.describe_table(TableName=table_name)
        table = response["Table"]

        # Basic table info
        status_info: dict[str, Any] = {
            "table_name": table_name,
            "status": table["TableStatus"],
            "arn": table["TableArn"],
            "creation_time": table["CreationDateTime"].isoformat(),
            "item_count": table.get("ItemCount", 0),
            "size_bytes": table.get("TableSizeBytes", 0),
        }

        # Billing mode
        billing = table.get("BillingModeSummary", {})
        status_info["billing_mode"] = billing.get("BillingMode", "PROVISIONED")

        # Provisioned throughput (if applicable)
        if status_info["billing_mode"] == "PROVISIONED":
            throughput = table.get("ProvisionedThroughput", {})
            status_info["read_capacity"] = throughput.get("ReadCapacityUnits", 0)
            status_info["write_capacity"] = throughput.get("WriteCapacityUnits", 0)

        # Get CloudWatch metrics for last hour
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)

        # Consumed read capacity
        try:
            read_response = cloudwatch.get_metric_statistics(
                Namespace="AWS/DynamoDB",
                MetricName="ConsumedReadCapacityUnits",
                Dimensions=[{"Name": "TableName", "Value": table_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=["Sum", "Average"]
            )

            if read_response["Datapoints"]:
                datapoint = read_response["Datapoints"][0]
                status_info["read_consumed_last_hour"] = datapoint.get("Sum", 0)
                status_info["read_avg_per_second"] = datapoint.get("Average", 0)
        except ClientError:
            pass  # CloudWatch metrics may not be available yet

        # Consumed write capacity
        try:
            write_response = cloudwatch.get_metric_statistics(
                Namespace="AWS/DynamoDB",
                MetricName="ConsumedWriteCapacityUnits",
                Dimensions=[{"Name": "TableName", "Value": table_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=["Sum", "Average"]
            )

            if write_response["Datapoints"]:
                datapoint = write_response["Datapoints"][0]
                status_info["write_consumed_last_hour"] = datapoint.get("Sum", 0)
                status_info["write_avg_per_second"] = datapoint.get("Average", 0)
        except ClientError:
            pass

        # GSI information
        gsi_list = table.get("GlobalSecondaryIndexes", [])
        if gsi_list:
            status_info["global_secondary_indexes"] = len(gsi_list)
            status_info["gsi_details"] = [
                {
                    "name": gsi["IndexName"],
                    "status": gsi["IndexStatus"],
                    "size_bytes": gsi.get("IndexSizeBytes", 0),
                    "item_count": gsi.get("ItemCount", 0)
                }
                for gsi in gsi_list
            ]

        return status_info

    except dynamodb.exceptions.ResourceNotFoundException:
        raise TableNotFoundError(f"Table '{table_name}' not found")
    except ClientError as e:
        raise KVStoreError(f"Failed to get table status: {e}")
