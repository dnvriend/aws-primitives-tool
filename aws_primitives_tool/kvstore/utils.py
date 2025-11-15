"""
Utility functions for kvstore operations.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import json
import sys
from typing import Any


def format_key(prefix: str, key: str) -> str:
    """
    Format a key with namespace prefix.

    Args:
        prefix: Namespace prefix (e.g., 'kv', 'counter', 'lock')
        key: User-provided key

    Returns:
        Formatted key with prefix (e.g., 'kv:mykey')
    """
    return f"{prefix}:{key}"


def parse_key(full_key: str) -> tuple[str, str]:
    """
    Parse a formatted key into prefix and key.

    Args:
        full_key: Full key with prefix (e.g., 'kv:mykey')

    Returns:
        Tuple of (prefix, key)
    """
    parts = full_key.split(":", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return "", full_key


def output_json(data: dict[str, Any], quiet: bool = False) -> None:
    """
    Output JSON to stdout.

    Args:
        data: Data to output as JSON
        quiet: If True, suppress output
    """
    if not quiet:
        print(json.dumps(data))


def output_text(message: str, quiet: bool = False) -> None:
    """
    Output text to stdout.

    Args:
        message: Message to output
        quiet: If True, suppress output
    """
    if not quiet:
        print(message)


def error_json(error: str, solution: str, exit_code: int) -> dict[str, Any]:
    """
    Format error as JSON.

    Args:
        error: Error message
        solution: Solution suggestion
        exit_code: Exit code

    Returns:
        Error dictionary
    """
    return {"error": error, "solution": solution, "exit_code": exit_code}


def error_text(error: str, solution: str) -> str:
    """
    Format error as human-readable text.

    Args:
        error: Error message
        solution: Solution suggestion

    Returns:
        Formatted error message
    """
    return f"❌ Error: {error}\n\n💡 Solution: {solution}"


def output_error(error: str, solution: str, exit_code: int, text_format: bool = False) -> None:
    """
    Output error message and exit.

    Args:
        error: Error message
        solution: Solution suggestion
        exit_code: Exit code
        text_format: If True, output as text; otherwise JSON
    """
    if text_format:
        sys.stderr.write(error_text(error, solution) + "\n")
    else:
        sys.stderr.write(json.dumps(error_json(error, solution, exit_code)) + "\n")
    sys.exit(exit_code)


def validate_table_name(table_name: str) -> bool:
    """
    Validate DynamoDB table name.

    Args:
        table_name: Table name to validate

    Returns:
        True if valid

    Raises:
        ValueError: If table name is invalid
    """
    if not table_name:
        raise ValueError("Table name cannot be empty")
    if len(table_name) < 3 or len(table_name) > 255:
        raise ValueError("Table name must be between 3 and 255 characters")
    if not all(c.isalnum() or c in "-_." for c in table_name):
        raise ValueError(
            "Table name can only contain alphanumeric characters, hyphens, underscores, and periods"
        )
    return True


def validate_key(key: str) -> bool:
    """
    Validate key name.

    Args:
        key: Key to validate

    Returns:
        True if valid

    Raises:
        ValueError: If key is invalid
    """
    if not key:
        raise ValueError("Key cannot be empty")
    if len(key) > 1024:
        raise ValueError("Key cannot exceed 1024 characters")
    return True
