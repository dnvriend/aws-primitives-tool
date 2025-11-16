"""
Table management commands for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from typing import Literal

import click

from ..core.table_operations import create_table, drop_table
from ..exceptions import KVStoreError, TableAlreadyExistsError, TableNotFoundError
from ..logging_config import get_logger, setup_logging
from ..utils import error_json, error_text, output_json, output_text

logger = get_logger(__name__)


@click.command("create-table")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option(
    "--billing",
    type=click.Choice(["on-demand", "provisioned"]),
    default="on-demand",
    help="Billing mode (default: on-demand)",
)
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (-v INFO, -vv DEBUG, -vvv TRACE)",
)
@click.pass_context
def create_table_command(
    ctx: click.Context,
    table: str,
    region: str | None,
    profile: str | None,
    billing: str,
    text: bool,
    verbose: int,
) -> None:
    """Create DynamoDB table for kvstore.

    Creates a table with proper schema for kvstore primitives including
    partition key (PK), sort key (SK), GSI for type-based queries, and TTL.

    Examples:

    \b
        # Create table with default name
        aws-primitives-tool kvstore create-table

    \b
        # Create table with custom name
        aws-primitives-tool kvstore create-table --table my-kvstore

    \b
        # Create with provisioned billing
        aws-primitives-tool kvstore create-table --billing provisioned

    \b
    Output Format:
        Returns JSON with table details:
        {"table": "...", "status": "CREATING", "arn": "..."}
    """
    setup_logging(verbose)

    try:
        logger.info(f"Creating table '{table}'")
        logger.debug(f"Region: {region}, Billing: {billing}")

        billing_mode: Literal["PAY_PER_REQUEST", "PROVISIONED"] = (
            "PAY_PER_REQUEST" if billing == "on-demand" else "PROVISIONED"
        )
        table_desc = create_table(table, region, profile, billing_mode)

        if text:
            output_text(f"✅ Table '{table}' created successfully")
            output_text(f"Status: {table_desc['TableStatus']}")
            output_text(f"ARN: {table_desc['TableArn']}")
        else:
            output_json(
                {
                    "table": table,
                    "status": table_desc["TableStatus"],
                    "arn": table_desc["TableArn"],
                }
            )

    except TableAlreadyExistsError as e:
        if text:
            solution = (
                f"Use a different table name or drop existing table with "
                f"'aws-primitives-tool kvstore drop-table --table {table} --approve'"
            )
            click.echo(error_text(str(e), solution), err=True)
        else:
            click.echo(
                error_json(str(e), "Use a different table name or drop existing table", 1),
                err=True,
            )
        ctx.exit(1)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check AWS credentials and permissions"), err=True)
        else:
            click.echo(error_json(str(e), "Check AWS credentials and permissions", 3), err=True)
        ctx.exit(3)


@click.command("drop-table")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option(
    "--approve",
    is_flag=True,
    help="Required flag to confirm table deletion",
)
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (-v INFO, -vv DEBUG, -vvv TRACE)",
)
@click.pass_context
def drop_table_command(
    ctx: click.Context,
    table: str,
    region: str | None,
    profile: str | None,
    approve: bool,
    text: bool,
    verbose: int,
) -> None:
    """Drop DynamoDB table for kvstore.

    WARNING: This permanently deletes the table and ALL data.

    Examples:

    \b
        # Attempt without approval (shows warning)
        aws-primitives-tool kvstore drop-table

    \b
        # Drop with approval
        aws-primitives-tool kvstore drop-table --approve

    \b
        # Drop custom table
        aws-primitives-tool kvstore drop-table --table my-kvstore --approve

    \b
    Output Format:
        Returns JSON with confirmation:
        {"table": "...", "status": "DELETING"}
    """
    setup_logging(verbose)

    if not approve:
        if text:
            click.echo("⚠️  WARNING: Table deletion requires approval", err=True)
            click.echo(f"\nThis will permanently delete table '{table}' and ALL data.", err=True)
            cmd = f"aws-primitives-tool kvstore drop-table --table {table} --approve"
            click.echo(f"\nTo proceed, use: {cmd}", err=True)
        else:
            solution = (
                f"Add --approve flag to confirm: "
                f"aws-primitives-tool kvstore drop-table --table {table} --approve"
            )
            click.echo(
                error_json("Table deletion requires approval", solution, 2),
                err=True,
            )
        ctx.exit(2)

    try:
        logger.info(f"Dropping table '{table}'")
        logger.debug(f"Region: {region}, Approved: {approve}")

        table_desc = drop_table(table, region, profile)

        if text:
            output_text(f"✅ Table '{table}' deletion initiated")
            output_text(f"Status: {table_desc['TableStatus']}")
        else:
            output_json({"table": table, "status": table_desc["TableStatus"]})

    except TableNotFoundError as e:
        if text:
            click.echo(error_text(str(e), "Check table name or list tables with AWS CLI"), err=True)
        else:
            click.echo(error_json(str(e), "Check table name", 1), err=True)
        ctx.exit(1)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check AWS credentials and permissions"), err=True)
        else:
            click.echo(error_json(str(e), "Check AWS credentials and permissions", 3), err=True)
        ctx.exit(3)


# Alias: delete-table is the same as drop-table
@click.command("delete-table")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option(
    "--approve",
    is_flag=True,
    help="Required flag to confirm table deletion",
)
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (-v INFO, -vv DEBUG, -vvv TRACE)",
)
@click.pass_context
def delete_table_command(
    ctx: click.Context,
    table: str,
    region: str | None,
    profile: str | None,
    approve: bool,
    text: bool,
    verbose: int,
) -> None:
    """Alias for drop-table command.

    See 'aws-primitives-tool kvstore drop-table --help' for full documentation.
    """
    # Call the drop-table implementation directly
    ctx.invoke(drop_table_command, table=table, region=region, profile=profile,
               approve=approve, text=text, verbose=verbose)
