"""
CLI commands for transaction operations.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""


import click

from ..core.client import DynamoDBClient
from ..core.transaction_operations import execute_transaction, load_transaction_file
from ..exceptions import KVStoreError
from ..utils import output_error, output_json, output_text, validate_table_name


@click.command("transaction")
@click.option(
    "--file",
    "-f",
    "file_path",
    required=True,
    type=click.Path(exists=True),
    help="Path to JSON file containing transaction operations",
)
@click.option("--table", required=True, envvar="KVSTORE_TABLE", help="DynamoDB table name")
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option("--quiet", is_flag=True, help="Suppress output")
def transaction_command(
    file_path: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    quiet: bool,
) -> None:
    """Execute multiple operations atomically using DynamoDB transactions.

    Transactions support up to 100 operations with ACID guarantees.
    Operations can be Put, Update, or Delete across kv, counter, lock, and leader types.

    \b
    Transaction File Format (JSON):
        {
          "operations": [
            {
              "action": "Put",
              "type": "kv",
              "key": "user:123",
              "value": "John Doe",
              "condition": "attribute_not_exists(PK)"
            },
            {
              "action": "Update",
              "type": "counter",
              "key": "user_count",
              "operation": "inc",
              "value": 1
            },
            {
              "action": "Delete",
              "type": "kv",
              "key": "temp:xyz"
            }
          ]
        }

    \b
    Operation Fields:
        - action: "Put", "Update", or "Delete" (required)
        - type: "kv", "counter", "lock", "leader" (required)
        - key: Key name (required)
        - value: Value for Put/Update operations
        - condition: Condition expression (optional)
        - operation: For counters: "inc" or "dec"

    \b
    Exit Codes:
        0 = success
        2 = validation error
        3 = transaction failed (conflict, condition failed, etc.)

    Examples:

    \b
        # Execute transaction from file
        aws-primitives-tool kvstore transaction --file transaction.json \\
            --table kvstore-table

    \b
        # Atomic user creation with counter increment
        cat > user-create.json <<'EOF'
        {
          "operations": [
            {
              "action": "Put",
              "type": "kv",
              "key": "user:alice",
              "value": "Alice Smith",
              "condition": "attribute_not_exists(PK)"
            },
            {
              "action": "Update",
              "type": "counter",
              "key": "user_count",
              "operation": "inc",
              "value": 1
            }
          ]
        }
        EOF
        aws-primitives-tool kvstore transaction -f user-create.json \\
            --table kvstore-table

    \b
        # Conditional update with lock check
        cat > conditional-update.json <<'EOF'
        {
          "operations": [
            {
              "action": "Update",
              "type": "kv",
              "key": "config:version",
              "value": "2.0",
              "condition": "#val = :old_val",
              "expression_attribute_names": {"#val": "value"},
              "expression_attribute_values": {":old_val": "1.0"}
            },
            {
              "action": "Put",
              "type": "kv",
              "key": "config:updated_by",
              "value": "admin"
            }
          ]
        }
        EOF
        aws-primitives-tool kvstore transaction -f conditional-update.json \\
            --table kvstore-table

    \b
    Output Format:
        {
          "success": true,
          "operations_count": 3,
          "timestamp": 1234567890
        }
    """
    try:
        validate_table_name(table)

        # Load transaction operations from file
        operations = load_transaction_file(file_path)

        # Execute transaction
        client = DynamoDBClient(table, region, profile)
        result = execute_transaction(client, operations)

        if text:
            output_text(
                f"✅ Transaction succeeded: {result['operations_count']} operations executed",
                quiet,
            )
        else:
            output_json(result, quiet)

    except KVStoreError as e:
        output_error(str(e), "Check transaction file and AWS credentials", 3, text)
    except Exception as e:
        output_error(str(e), "Check transaction file format and table", 3, text)
