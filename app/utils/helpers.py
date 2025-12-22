"""
Helper Utility Functions

Provides common helper functions for formatting, parsing,
and general utility operations.

This module will be fully implemented in later phases of the refactor.
"""

import logging

logger = logging.getLogger(__name__)


def format_volume(volume: float) -> str:
    """
    Format volume value for display.

    Args:
        volume: Volume level (0.0-1.0)

    Returns:
        Formatted volume string (e.g., "75%")
    """
    if volume is None:
        return "N/A"

    percent = int(volume * 100)
    return f"{percent}%"


def parse_volume(volume_str: str) -> float:
    """
    Parse volume string to float value.

    Args:
        volume_str: Volume string (e.g., "75%" or "0.75")

    Returns:
        Volume as float (0.0-1.0)
    """
    try:
        # Remove % if present
        if volume_str.endswith("%"):
            return float(volume_str.rstrip("%")) / 100.0
        else:
            return float(volume_str)
    except (ValueError, AttributeError):
        logger.warning(f"Failed to parse volume: {volume_str}")
        return 0.0


def parse_device_info(device_string: str) -> dict:
    """
    Parse PulseAudio device information string.

    Args:
        device_string: Device information string from PulseAudio

    Returns:
        Dictionary with parsed device information
    """
    # TODO: Phase 1 (later) - Implement device info parsing
    logger.warning(f"parse_device_info({device_string}) not yet implemented")
    return {}


def format_timestamp(timestamp) -> str:
    """
    Format timestamp for display.

    Args:
        timestamp: Timestamp object

    Returns:
        Formatted timestamp string
    """
    # TODO: Phase 2 - Implement timestamp formatting
    if timestamp is None:
        return "Never"

    try:
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
    except AttributeError:
        return str(timestamp)


def get_short_device_name(device_name: str, max_length: int = 30) -> str:
    """
    Get shortened device name for display.

    Args:
        device_name: Full device name
        max_length: Maximum length for display

    Returns:
        Shortened device name
    """
    if len(device_name) <= max_length:
        return device_name

    # Truncate and add ellipsis
    return device_name[: max_length - 3] + "..."


def ensure_list(value) -> list:
    """
    Ensure value is a list.

    Args:
        value: Any value

    Returns:
        List containing the value(s)
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
