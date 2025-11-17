"""Centralized logging configuration with multi-level verbosity support.

This module provides setup_logging() for configuring logging based on
verbosity count from CLI arguments (-v, -vv, -vvv).

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import logging
import sys


def setup_logging(verbose_count: int = 0) -> None:
    """Configure logging based on verbosity level.

    Maps CLI verbosity count to Python logging levels and configures
    both application and dependent library loggers.

    Args:
        verbose_count: Number of -v flags (0-3+)
            0: WARNING level (quiet mode)
            1: INFO level (normal verbose)
            2: DEBUG level (detailed debugging)
            3+: DEBUG + enable dependent library logging (trace mode)

    Example:
        >>> setup_logging(0)  # No -v flag: WARNING only
        >>> setup_logging(1)  # -v: INFO level
        >>> setup_logging(2)  # -vv: DEBUG level
        >>> setup_logging(3)  # -vvv: DEBUG + library internals
    """
    # Map verbosity count to logging levels
    if verbose_count == 0:
        level = logging.WARNING
    elif verbose_count == 1:
        level = logging.INFO
    elif verbose_count >= 2:
        level = logging.DEBUG
    else:
        level = logging.WARNING

    # Configure root logger with appropriate format based on level
    if verbose_count >= 2:
        # More detailed format for DEBUG
        fmt = "[%(levelname)s] %(name)s:%(lineno)d - %(message)s"
    else:
        # Simple format for INFO/WARNING
        fmt = "[%(levelname)s] %(message)s"

    logging.basicConfig(
        level=level,
        format=fmt,
        stream=sys.stderr,
        force=True,  # Override any existing configuration
    )

    # Configure dependent library loggers at TRACE level (-vvv)
    if verbose_count >= 3:
        # boto3/botocore (AWS SDK) - show API calls
        logging.getLogger("boto3").setLevel(logging.DEBUG)
        logging.getLogger("botocore").setLevel(logging.DEBUG)
        logging.getLogger("botocore.credentials").setLevel(logging.INFO)  # Less noise

        # urllib3 (HTTP client used by boto3)
        logging.getLogger("urllib3").setLevel(logging.DEBUG)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)

    else:
        # Suppress noisy libraries at lower verbosity levels
        logging.getLogger("boto3").setLevel(logging.WARNING)
        logging.getLogger("botocore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    This is a convenience wrapper around logging.getLogger() that
    ensures consistent logger naming across your application.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Operation started")
        >>> logger.debug("Detailed operation info")
    """
    return logging.getLogger(name)
