"""
Set commands for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import click

from ..core.client import DynamoDBClient
from ..core.set_operations import add_to_set, get_members, get_set_size, is_member, remove_from_set
from ..exceptions import KVStoreError
from ..utils import error_json, error_text, output_json, output_text


@click.command("sadd")
@click.argument("set_name")
@click.argument("member")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option("--verbose", "-V", is_flag=True, help="Verbose output")
@click.pass_context
def sadd_command(
    ctx: click.Context,
    set_name: str,
    member: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """Add a member to a set.

    This operation is idempotent: adding an existing member has no effect.
    Uses composite sort key pattern for efficient membership checks and scans.

    Examples:

    \b
        # Add member to set
        aws-primitives-tool kvstore sadd active-agents agent-001

    \b
        # Add with verbose output
        aws-primitives-tool kvstore sadd active-agents agent-001 --verbose

    \b
        # Use in registration script
        AGENT_ID="agent-$(uuidgen)"
        aws-primitives-tool kvstore sadd active-agents "$AGENT_ID"

    \b
        # Add multiple members (idempotent - safe to repeat)
        for agent in agent-001 agent-002 agent-003; do
            aws-primitives-tool kvstore sadd active-agents "$agent"
        done

    \b
    Output Format:
        Returns JSON:
        {"set": "active-agents", "member": "agent-001", "added": true}
    """
    try:
        if verbose:
            click.echo(f"Adding member '{member}' to set '{set_name}'...", err=True)

        client = DynamoDBClient(table, region, profile)
        result = add_to_set(client, set_name, member)

        if text:
            output_text(f"Added '{member}' to set '{set_name}'")
        else:
            output_json(result)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("scard")
@click.argument("set_name")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option("--verbose", "-V", is_flag=True, help="Verbose output")
@click.pass_context
def scard_command(
    ctx: click.Context,
    set_name: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """Get the size (cardinality) of a set.

    This operation efficiently counts set members using DynamoDB's COUNT query,
    which doesn't consume read capacity for item data.

    Examples:

    \b
        # Get set size
        aws-primitives-tool kvstore scard active-agents

    \b
        # Extract size with jq
        aws-primitives-tool kvstore scard active-agents | jq -r '.size'

    \b
        # Use in shell script to check set cardinality
        SIZE=$(aws-primitives-tool kvstore scard active-agents | jq -r '.size')
        if [ "$SIZE" -gt 10 ]; then
            echo "Too many active agents: $SIZE"
        fi

    \b
    Output Format:
        Returns JSON:
        {"set": "active-agents", "size": 2}
    """
    try:
        if verbose:
            click.echo(f"Getting size of set '{set_name}'...", err=True)

        client = DynamoDBClient(table, region, profile)
        result = get_set_size(client, set_name)

        if text:
            output_text(f"Set '{set_name}' has {result['size']} members")
        else:
            output_json(result)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("srem")
@click.argument("set_name")
@click.argument("member")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option("--verbose", "-V", is_flag=True, help="Verbose output")
@click.pass_context
def srem_command(
    ctx: click.Context,
    set_name: str,
    member: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """Remove member from set.

    This operation is idempotent - no error if member doesn't exist.
    Uses DeleteItem for efficient removal.

    Examples:

    \b
        # Remove member from set
        aws-primitives-tool kvstore srem active-agents agent-001

    \b
        # Remove with verbose output
        aws-primitives-tool kvstore srem active-agents agent-001 --verbose

    \b
        # Use in cleanup script
        aws-primitives-tool kvstore srem active-agents terminated-agent

    \b
    Output Format:
        Returns JSON:
        {"set": "active-agents", "member": "agent-001", "removed": true}
    """
    try:
        if verbose:
            click.echo(f"Removing member '{member}' from set '{set_name}'...", err=True)

        client = DynamoDBClient(table, region, profile)
        result = remove_from_set(client, set_name, member)

        if text:
            output_text(f"Removed '{member}' from set '{set_name}'")
        else:
            output_json(result)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("smembers")
@click.argument("set_name")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option("--verbose", "-V", is_flag=True, help="Verbose output")
@click.pass_context
def smembers_command(
    ctx: click.Context,
    set_name: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """List all members of a set.

    This operation queries DynamoDB to retrieve all members of a set.
    Returns the members array and total count.

    Examples:

    \b
        # List all members of a set
        aws-primitives-tool kvstore smembers active-agents

    \b
        # Extract members with jq
        aws-primitives-tool kvstore smembers active-agents | jq -r '.members[]'

    \b
        # Count members directly
        aws-primitives-tool kvstore smembers active-agents | jq -r '.count'

    \b
        # Use in shell script to iterate over members
        for member in $(aws-primitives-tool kvstore smembers active-agents | jq -r '.members[]'); do
            echo "Processing: $member"
        done

    \b
    Output Format:
        Returns JSON:
        {"set": "active-agents", "members": ["agent-123", "agent-456"], "count": 2}
    """
    try:
        if verbose:
            click.echo(f"Getting members of set '{set_name}'...", err=True)

        client = DynamoDBClient(table, region, profile)
        result = get_members(client, set_name)

        if text:
            if result["count"] == 0:
                output_text(f"Set '{set_name}' has no members")
            else:
                output_text(f"Set '{set_name}' has {result['count']} member(s):")
                for member in result["members"]:
                    output_text(f"  {member}")
        else:
            output_json(result)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("sismember")
@click.argument("set_name")
@click.argument("member")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option("--verbose", "-V", is_flag=True, help="Verbose output")
@click.pass_context
def sismember_command(
    ctx: click.Context,
    set_name: str,
    member: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """Check if member exists in set.

    Exit codes:
    - 0: Member exists
    - 1: Member does not exist
    - 3: AWS error (table not found, permissions, etc.)

    Examples:

    \b
        # Check if member exists in set
        aws-primitives-tool kvstore sismember active-agents agent-001

    \b
        # Use in shell script
        if aws-primitives-tool kvstore sismember active-agents agent-001; then
            echo "Agent is active"
        else
            echo "Agent is not active"
        fi

    \b
        # Extract boolean value with jq
        aws-primitives-tool kvstore sismember active-agents agent-001 | jq -r '.is_member'

    \b
    Output Format:
        Returns JSON:
        {"set": "active-agents", "member": "agent-001", "is_member": true}
    """
    try:
        if verbose:
            click.echo(f"Checking if '{member}' is in set '{set_name}'...", err=True)

        client = DynamoDBClient(table, region, profile)
        is_member_result = is_member(client, set_name, member)

        if text:
            if is_member_result:
                output_text(f"✅ Member '{member}' exists in set '{set_name}'")
            else:
                output_text(f"❌ Member '{member}' does not exist in set '{set_name}'")
        else:
            output_json({"set": set_name, "member": member, "is_member": is_member_result})

        if not is_member_result:
            ctx.exit(1)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)
