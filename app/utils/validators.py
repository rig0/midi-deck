"""
Input Validation Utilities

Provides validation functions for user input, configuration values,
and data sanitization.
"""

import logging
import re

logger = logging.getLogger(__name__)


def validate_sink_name(name: str) -> bool:
    """
    Validate sink name format.

    Args:
        name: Sink name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False

    pattern = r"^[a-zA-Z][a-zA-Z0-9_]*$"
    return bool(re.match(pattern, name))


def validate_device_name(device: str) -> bool:
    """
    Validate PulseAudio device name format.

    Args:
        device: Device name to validate

    Returns:
        True if valid, False otherwise
    """
    if not device:
        return False

    pattern = r"^[a-zA-Z0-9._-]+$"
    return bool(re.match(pattern, device))


def validate_midi_note(note: int) -> bool:
    """
    Validate MIDI note number (0-127).

    Args:
        note: MIDI note number

    Returns:
        True if valid, False otherwise
    """
    return isinstance(note, int) and 0 <= note <= 127


def validate_volume(volume: float) -> bool:
    """
    Validate volume value (0.0-1.0).

    Args:
        volume: Volume level to validate

    Returns:
        True if valid, False otherwise
    """
    return isinstance(volume, (int, float)) and 0.0 <= volume <= 1.0


def sanitize_input(value: str) -> str:
    """
    Sanitize user input to prevent injection attacks.

    Args:
        value: Input string to sanitize

    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return ""

    sanitized = value.strip()
    sanitized = sanitized.replace("\x00", "")

    return sanitized


def validate_config_key(key: str) -> bool:
    """
    Validate configuration key format.

    Args:
        key: Configuration key to validate

    Returns:
        True if valid, False otherwise
    """
    if not key:
        return False

    pattern = r"^[a-z][a-z0-9_]*$"
    return bool(re.match(pattern, key))


def validate_session_name(name: str) -> bool:
    """
    Validate session name format.

    Args:
        name: Session name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name or len(name) > 100:
        return False

    pattern = r"^[a-zA-Z0-9][a-zA-Z0-9 _-]*$"
    return bool(re.match(pattern, name))
