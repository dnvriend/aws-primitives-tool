"""
Lock commands for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import click

from ..core.client import DynamoDBClient
from ..core.lock_operations import (
    acquire_lock,
    check_lock,
    extend_lock,
    generate_default_owner,
    release_lock,
)
from ..exceptions import ConditionFailedError, KeyNotFoundError, KVStoreError, LockUnavailableError
from ..utils import error_json, error_text, output_json, output_text


@click.command("lock-acquire")
@click.argument("lock_name")
@click.option("--ttl", type=int, default=300, help="Lock TTL in seconds (default: 300)")
@click.option("--owner", help="Owner ID (default: hostname-pid)")
@click.option(
    "--wait",
    type=int,
    default=0,
    help="Wait time in seconds with exponential backoff (default: 0)",
)
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
def lock_acquire_command(
    ctx: click.Context,
    lock_name: str,
    ttl: int,
    owner: str | None,
    wait: int,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """Acquire a distributed lock.

    Locks enable coordination between distributed processes. Uses DynamoDB
    conditional writes for atomicity.

    Examples:

    \b
        # Acquire lock with 5-minute TTL
        aws-primitives-tool kvstore lock-acquire deploy-prod --ttl 300

    \b
        # Acquire with custom owner and wait
        aws-primitives-tool kvstore lock-acquire task-123 --owner agent-abc --wait 60

    \b
        # Use in shell script
        if aws-primitives-tool kvstore lock-acquire deploy; then
            deploy.sh
            aws-primitives-tool kvstore lock-release deploy
        fi

    \b
    Output Format:
        Returns JSON:
        {"lock": "deploy-prod", "owner": "agent-123", "ttl": 1731696300, "acquired_at": 1731696000}
    """
    try:
        # Generate default owner if not provided
        if not owner:
            owner = generate_default_owner()

        if verbose:
            click.echo(f"Acquiring lock '{lock_name}' as {owner}...", err=True)
            if wait > 0:
                click.echo(f"Will wait up to {wait} seconds with exponential backoff...", err=True)

        client = DynamoDBClient(table, region, profile)
        result = acquire_lock(client, lock_name, ttl, owner, wait)

        if text:
            output_text(f"✅ Lock '{lock_name}' acquired by {owner}")
            output_text(f"TTL: {ttl} seconds")
        else:
            output_json(result)

    except LockUnavailableError as e:
        if text:
            solution = (
                f"Wait for lock to expire or force release with "
                f"'aws-primitives-tool kvstore lock-release {lock_name} --force'"
            )
            click.echo(
                error_text(str(e), solution),
                err=True,
            )
        else:
            click.echo(
                error_json(
                    str(e),
                    "Wait for expiration or force release",
                    4,
                ),
                err=True,
            )
        ctx.exit(4)

    except KVStoreError as e:
        if text:
            click.echo(
                error_text(str(e), "Check table exists and AWS credentials"),
                err=True,
            )
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("lock-release")
@click.argument("lock_name")
@click.option("--owner", help="Owner ID (default: hostname-pid)")
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
def lock_release_command(
    ctx: click.Context,
    lock_name: str,
    owner: str | None,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """Release a distributed lock.

    Only the lock owner can release the lock. Uses conditional delete
    to prevent accidental releases by other processes.

    Examples:

    \b
        # Release lock (using default owner)
        aws-primitives-tool kvstore lock-release deploy-prod

    \b
        # Release with explicit owner
        aws-primitives-tool kvstore lock-release task-123 --owner agent-abc

    \b
    Output Format:
        Returns JSON:
        {"lock": "deploy-prod", "released": true}
    """
    try:
        # Generate default owner if not provided
        if not owner:
            owner = generate_default_owner()

        if verbose:
            click.echo(f"Releasing lock '{lock_name}' as {owner}...", err=True)

        client = DynamoDBClient(table, region, profile)
        result = release_lock(client, lock_name, owner)

        if text:
            output_text(f"✅ Lock '{lock_name}' released by {owner}")
        else:
            output_json(result)

    except ConditionFailedError as e:
        if text:
            click.echo(
                error_text(
                    str(e),
                    (
                        f"Lock is not owned by '{owner}'. "
                        f"Check lock owner or wait for TTL expiration"
                    ),
                ),
                err=True,
            )
        else:
            click.echo(
                error_json(
                    str(e),
                    "Lock not owned by this process",
                    2,
                ),
                err=True,
            )
        ctx.exit(2)

    except KeyNotFoundError:
        # Lock doesn't exist - treat as success (idempotent)
        if verbose:
            click.echo(f"Lock '{lock_name}' does not exist (already released)", err=True)

        result = {"lock": lock_name, "released": True}

        if text:
            output_text(f"✅ Lock '{lock_name}' does not exist (already released)")
        else:
            output_json(result)

    except KVStoreError as e:
        if text:
            click.echo(
                error_text(str(e), "Check table exists and AWS credentials"),
                err=True,
            )
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("lock-extend")
@click.argument("lock_name")
@click.option("--ttl", type=int, required=True, help="New TTL in seconds from now")
@click.option("--owner", help="Owner ID (default: hostname-pid)")
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
def lock_extend_command(
    ctx: click.Context,
    lock_name: str,
    ttl: int,
    owner: str | None,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """Extend lock TTL.

    Extends the time-to-live of a held lock. Only the owner can extend their lock.
    Useful for long-running operations that need to maintain their lock.

    Examples:

    \b
        # Extend lock TTL to 10 minutes from now
        aws-primitives-tool kvstore lock-extend deploy-prod --ttl 600

    \b
        # Extend with explicit owner
        aws-primitives-tool kvstore lock-extend task-123 --ttl 300 --owner agent-abc

    \b
        # Heartbeat pattern in shell script
        while true; do
            aws-primitives-tool kvstore lock-extend deploy --ttl 300
            sleep 60
        done

    \b
    Output Format:
        Returns JSON:
        {"lock": "deploy-prod", "owner": "agent-123", "ttl": 1731696900, "extended": true}
    """
    try:
        # Generate default owner if not provided
        if not owner:
            owner = generate_default_owner()

        if verbose:
            click.echo(f"Extending lock '{lock_name}' as {owner} with TTL {ttl}s...", err=True)

        client = DynamoDBClient(table, region, profile)
        result = extend_lock(client, lock_name, ttl, owner)

        if text:
            output_text(f"✅ Lock '{lock_name}' extended by {owner}")
            output_text(f"New TTL: {ttl} seconds from now")
        else:
            output_json(result)

    except ConditionFailedError as e:
        if text:
            click.echo(
                error_text(
                    str(e),
                    f"Verify the lock is owned by '{owner}' or check if it expired",
                ),
                err=True,
            )
        else:
            click.echo(
                error_json(
                    str(e),
                    "Verify ownership or check if lock expired",
                    2,
                ),
                err=True,
            )
        ctx.exit(2)

    except KVStoreError as e:
        if text:
            click.echo(
                error_text(str(e), "Check table exists and AWS credentials"),
                err=True,
            )
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("lock-check")
@click.argument("lock_name")
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
def lock_check_command(
    ctx: click.Context,
    lock_name: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """Check if a lock is held.

    Returns lock status and owner information if locked.
    Exit code 0 if locked, 1 if free.

    Examples:

    \b
        # Check lock status
        aws-primitives-tool kvstore lock-check deploy-prod

    \b
        # Use in shell script
        if aws-primitives-tool kvstore lock-check deploy-prod; then
            echo "Lock is held"
        else
            echo "Lock is free"
        fi

    \b
    Output Format:
        Returns JSON if locked:
        {"lock": "deploy-prod", "owner": "agent-123", "ttl": 1731696300, "acquired_at": 1731696000}

        Returns empty JSON if free:
        {"lock": "deploy-prod", "status": "free"}
    """
    try:
        if verbose:
            click.echo(f"Checking lock '{lock_name}'...", err=True)

        client = DynamoDBClient(table, region, profile)
        result = check_lock(client, lock_name)

        if result:
            # Lock is held
            if text:
                output_text(f"Lock '{lock_name}' is held by {result['owner']}")
                if result.get("ttl"):
                    output_text(f"TTL: {result['ttl']}")
                if result.get("acquired_at"):
                    output_text(f"Acquired at: {result['acquired_at']}")
            else:
                output_json(result)
            ctx.exit(0)
        else:
            # Lock is free
            free_result = {"lock": lock_name, "status": "free"}
            if text:
                output_text(f"Lock '{lock_name}' is free")
            else:
                output_json(free_result)
            ctx.exit(1)

    except KVStoreError as e:
        if text:
            click.echo(
                error_text(str(e), "Check table exists and AWS credentials"),
                err=True,
            )
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)
