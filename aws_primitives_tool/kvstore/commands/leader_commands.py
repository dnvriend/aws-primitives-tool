"""
Leader commands for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import click

from ..core.client import DynamoDBClient
from ..core.leader_operations import check_leader, elect_leader, heartbeat_leader, resign_leader
from ..core.lock_operations import generate_default_owner
from ..exceptions import ConditionFailedError, KVStoreError, LeaderElectionError
from ..logging_config import get_logger, setup_logging
from ..utils import error_json, error_text, output_json, output_text

logger = get_logger(__name__)


@click.command("leader-elect")
@click.argument("pool_name")
@click.option("--ttl", type=int, default=30, help="Leadership lease TTL in seconds (default: 30)")
@click.option("--id", "agent_id", help="Agent ID (default: hostname-pid)")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (-v INFO, -vv DEBUG, -vvv TRACE)",
)
@click.pass_context
def leader_elect_command(
    ctx: click.Context,
    pool_name: str,
    ttl: int,
    agent_id: str | None,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: int,
) -> None:
    """Elect leader in a pool using atomic conditional write.

    Leader election enables distributed coordination where only one agent
    can become the leader for a given pool. Uses DynamoDB conditional writes
    for atomic election.

    The leader lease expires after TTL seconds. Other agents can attempt
    election after the lease expires.

    Examples:

    \b
        # Elect leader with 30-second lease
        aws-primitives-tool kvstore leader-elect deployment-pool

    \b
        # Elect with custom TTL and agent ID
        aws-primitives-tool kvstore leader-elect task-pool \\
            --ttl 60 \\
            --id worker-001

    \b
        # Use in shell script with exit code check
        if aws-primitives-tool kvstore leader-elect deployment-pool; then
            echo "I am the leader, starting deployment..."
            deploy.sh
        else
            echo "Another agent is leader, waiting..."
        fi

    \b
        # Heartbeat pattern - extend leadership
        while true; do
            aws-primitives-tool kvstore leader-elect deployment-pool --ttl 60
            if [ $? -eq 0 ]; then
                echo "Leadership maintained"
            fi
            sleep 30
        done

    \b
    Output Format:
        Returns JSON on success:
        {"pool": "deployment-pool", "leader": "hostname-12345", "ttl": 1731696330}

        Returns JSON on failure:
        {"error": "...", "solution": "...", "exit_code": 4}

    \b
    Exit Codes:
        0 - Successfully elected as leader
        4 - Another agent is the leader
        3 - AWS error (table not found, credentials, etc.)
    """
    setup_logging(verbose)

    try:
        # Generate default agent ID if not provided
        if not agent_id:
            agent_id = generate_default_owner()

        logger.info(f"Leader election for pool '{pool_name}' as {agent_id}")
        logger.debug(f"TTL: {ttl}s, Table: {table}")

        client = DynamoDBClient(table, region, profile)
        result = elect_leader(client, pool_name, agent_id, ttl)

        if text:
            output_text(f"✅ Elected as leader for pool '{pool_name}'")
            output_text(f"Agent: {agent_id}")
            output_text(f"Lease expires in: {ttl} seconds")
        else:
            output_json(result)

    except LeaderElectionError as e:
        if text:
            solution = (
                f"Wait for the current leader's lease to expire, or check leadership status with "
                f"'aws-primitives-tool kvstore leader-check {pool_name}'"
            )
            click.echo(
                error_text(str(e), solution),
                err=True,
            )
        else:
            click.echo(
                error_json(
                    str(e),
                    "Wait for lease expiration or check leader status",
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


@click.command("leader-resign")
@click.argument("pool_name")
@click.option("--id", "agent_id", help="Agent ID (default: hostname-pid)")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (-v INFO, -vv DEBUG, -vvv TRACE)",
)
@click.pass_context
def leader_resign_command(
    ctx: click.Context,
    pool_name: str,
    agent_id: str | None,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: int,
) -> None:
    """Resign from leader position.

    Only the current leader can resign. Operation is idempotent - if no leader
    exists, the operation still succeeds.

    Examples:

    \b
        # Resign as leader (using default agent ID)
        aws-primitives-tool kvstore leader-resign deploy-pool

    \b
        # Resign with explicit agent ID
        aws-primitives-tool kvstore leader-resign task-pool --id agent-123

    \b
        # Use in shell script
        if aws-primitives-tool kvstore leader-resign deploy-pool; then
            echo "Successfully resigned from leadership"
        fi

    \b
    Output Format:
        Returns JSON:
        {"pool": "deploy-pool", "resigned": true}
    """
    setup_logging(verbose)

    try:
        # Generate default agent ID if not provided
        if not agent_id:
            agent_id = generate_default_owner()

        logger.info(f"Resigning from leader pool '{pool_name}' as {agent_id}")

        client = DynamoDBClient(table, region, profile)
        result = resign_leader(client, pool_name, agent_id)

        if text:
            output_text(f"✅ Resigned from leader pool '{pool_name}' as {agent_id}")
        else:
            output_json(result)

    except ConditionFailedError as e:
        if text:
            click.echo(
                error_text(
                    str(e),
                    (
                        f"Agent '{agent_id}' is not the current leader of pool '{pool_name}'. "
                        f"Only the current leader can resign."
                    ),
                ),
                err=True,
            )
        else:
            click.echo(
                error_json(
                    str(e),
                    "Not the current leader - only leader can resign",
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


@click.command("leader-check")
@click.argument("pool_name")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (-v INFO, -vv DEBUG, -vvv TRACE)",
)
@click.pass_context
def leader_check_command(
    ctx: click.Context,
    pool_name: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: int,
) -> None:
    """Check if a leader exists for the pool.

    Returns leader information if a leader exists.
    Exit code 0 if leader exists, 1 if no leader.

    Examples:

    \b
        # Check leader status
        aws-primitives-tool kvstore leader-check deploy-pool

    \b
        # Use in shell script
        if aws-primitives-tool kvstore leader-check deploy-pool; then
            echo "Leader exists"
        else
            echo "No leader"
        fi

    \b
    Output Format:
        Returns JSON if leader exists:
        {"pool": "deploy-pool", "leader": "agent-123", "ttl": 1731696300, "elected_at": 1731696000}

        Returns JSON if no leader:
        {"pool": "deploy-pool", "status": "no_leader"}
    """
    setup_logging(verbose)

    try:
        logger.info(f"Checking leader for pool '{pool_name}'")

        client = DynamoDBClient(table, region, profile)
        result = check_leader(client, pool_name)

        if result:
            # Leader exists
            if text:
                output_text(f"Leader for pool '{pool_name}' is {result['leader']}")
                if result.get("ttl"):
                    output_text(f"TTL: {result['ttl']}")
                if result.get("elected_at"):
                    output_text(f"Elected at: {result['elected_at']}")
            else:
                output_json(result)
            ctx.exit(0)
        else:
            # No leader
            no_leader_result = {"pool": pool_name, "status": "no_leader"}
            if text:
                output_text(f"No leader for pool '{pool_name}'")
            else:
                output_json(no_leader_result)
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


@click.command("leader-heartbeat")
@click.argument("pool_name")
@click.option("--ttl", type=int, default=30, help="TTL extension in seconds (default: 30)")
@click.option("--id", "agent_id", help="Agent ID (default: hostname-pid)")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (-v INFO, -vv DEBUG, -vvv TRACE)",
)
@click.pass_context
def leader_heartbeat_command(
    ctx: click.Context,
    pool_name: str,
    ttl: int,
    agent_id: str | None,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: int,
) -> None:
    """Send heartbeat to extend leadership lease.

    Only the current leader can send heartbeat. Updates TTL to maintain
    leadership and prevent lease expiration.

    Examples:

    \b
        # Send heartbeat with default 30-second TTL
        aws-primitives-tool kvstore leader-heartbeat deploy-pool

    \b
        # Send heartbeat with 60-second TTL extension
        aws-primitives-tool kvstore leader-heartbeat task-pool --ttl 60

    \b
        # Heartbeat pattern in shell script
        while true; do
            aws-primitives-tool kvstore leader-heartbeat deploy-pool --ttl 30
            sleep 10
        done

    \b
        # With explicit agent ID
        aws-primitives-tool kvstore leader-heartbeat task-pool \\
            --id agent-123 --ttl 45

    \b
    Output Format:
        Returns JSON:
        {"pool": "deploy-pool", "leader": "agent-123", "ttl": 1731696330, "heartbeat": true}
    """
    setup_logging(verbose)

    try:
        # Generate default agent ID if not provided
        if not agent_id:
            agent_id = generate_default_owner()

        logger.info(f"Heartbeat for pool '{pool_name}' as {agent_id}")
        logger.debug(f"TTL: {ttl}s, Table: {table}")

        client = DynamoDBClient(table, region, profile)
        result = heartbeat_leader(client, pool_name, agent_id, ttl)

        if text:
            output_text(f"✅ Heartbeat sent for pool '{pool_name}' by {agent_id}")
            output_text(f"New TTL: {result['ttl']} (expires in {ttl} seconds)")
        else:
            output_json(result)

    except ConditionFailedError as e:
        if text:
            solution = (
                f"Agent '{agent_id}' is not the current leader. "
                f"Check with 'aws-primitives-tool kvstore leader-check {pool_name}'"
            )
            click.echo(error_text(str(e), solution), err=True)
        else:
            click.echo(
                error_json(str(e), "Not the current leader - only leader can heartbeat", 2),
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
