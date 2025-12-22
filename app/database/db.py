"""
Database Access Layer

Additional database access functions and utilities.
Provides higher-level database operations built on top of the ORM models.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.database.models import (
    Config,
    HardwareOutput,
    MidiMapping,
    Session,
    SessionConnection,
    SessionMute,
    SessionVolume,
    VirtualSink,
    get_db_session,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Session State Management
# =============================================================================


def save_session_state(
    session_id: int,
    volumes: Dict[str, float],
    connections: Dict[str, List[str]],
    mutes: Dict[str, bool],
) -> bool:
    """
    Save complete state to a session.

    Args:
        session_id: Target session ID
        volumes: Dict mapping sink names to volume levels (0.0-1.0)
        connections: Dict mapping sink names to lists of connected output names
        mutes: Dict mapping sink names to mute states

    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db_session() as db_session:
            # Verify session exists
            session = db_session.query(Session).filter_by(id=session_id).first()
            if not session:
                logger.error(f"Session {session_id} not found")
                return False

            # Get all sinks and outputs for mapping names to IDs
            sinks = {s.name: s.id for s in db_session.query(VirtualSink).all()}
            outputs = {o.name: o.id for o in db_session.query(HardwareOutput).all()}

            # Clear existing state for this session
            db_session.query(SessionVolume).filter_by(session_id=session_id).delete()
            db_session.query(SessionConnection).filter_by(session_id=session_id).delete()
            db_session.query(SessionMute).filter_by(session_id=session_id).delete()

            # Save volumes
            for sink_name, volume in volumes.items():
                if sink_name in sinks:
                    vol = SessionVolume(
                        session_id=session_id, sink_id=sinks[sink_name], volume=volume
                    )
                    db_session.add(vol)

            # Save connections
            for sink_name, output_names in connections.items():
                if sink_name in sinks:
                    for output_name in output_names:
                        if output_name in outputs:
                            conn = SessionConnection(
                                session_id=session_id,
                                sink_id=sinks[sink_name],
                                output_id=outputs[output_name],
                                is_connected=True,
                            )
                            db_session.add(conn)

            # Save mutes
            for sink_name, is_muted in mutes.items():
                if sink_name in sinks:
                    mute = SessionMute(
                        session_id=session_id, sink_id=sinks[sink_name], is_muted=is_muted
                    )
                    db_session.add(mute)

            db_session.commit()
            logger.info(f"State saved to session {session_id}")
            return True

    except Exception as e:
        logger.error(f"Error saving session state: {e}", exc_info=True)
        return False


def load_session_state(session_id: int) -> Optional[Dict[str, Any]]:
    """
    Load complete state from a session.

    Args:
        session_id: Session ID to load

    Returns:
        Dictionary containing volumes, connections, and mutes, or None if failed
    """
    try:
        with get_db_session() as db_session:
            # Verify session exists
            session = db_session.query(Session).filter_by(id=session_id).first()
            if not session:
                logger.error(f"Session {session_id} not found")
                return None

            # Load volumes
            volumes = {}
            for vol in (
                db_session.query(SessionVolume).filter_by(session_id=session_id).all()
            ):
                volumes[vol.sink.name] = vol.volume

            # Load connections
            connections = {}
            for conn in (
                db_session.query(SessionConnection).filter_by(session_id=session_id).all()
            ):
                sink_name = conn.sink.name
                output_name = conn.output.name

                if sink_name not in connections:
                    connections[sink_name] = []

                if conn.is_connected:
                    connections[sink_name].append(output_name)

            # Load mutes
            mutes = {}
            for mute in (
                db_session.query(SessionMute).filter_by(session_id=session_id).all()
            ):
                mutes[mute.sink.name] = mute.is_muted

            state = {
                "session_id": session_id,
                "session_name": session.name,
                "volumes": volumes,
                "connections": connections,
                "mutes": mutes,
            }

            logger.info(f"State loaded from session {session_id}")
            return state

    except Exception as e:
        logger.error(f"Error loading session state: {e}", exc_info=True)
        return None


def get_current_session_state() -> Optional[Dict[str, Any]]:
    """
    Get state from the current active session.

    Returns:
        Dictionary containing current session state, or None if no current session
    """
    try:
        with get_db_session() as db_session:
            current = db_session.query(Session).filter_by(is_current=True).first()
            if not current:
                logger.warning("No current session found")
                return None

            return load_session_state(current.id)

    except Exception as e:
        logger.error(f"Error getting current session state: {e}", exc_info=True)
        return None


# =============================================================================
# MIDI Mapping Helpers
# =============================================================================


def get_fader_mapping() -> Dict[int, str]:
    """
    Get MIDI fader CC number to sink name mapping.

    In the MIDI Deck, faders are mapped to CC numbers 1-4 for channels 1-4.

    Returns:
        Dictionary mapping CC numbers to sink names
    """
    try:
        with get_db_session() as db_session:
            sinks = (
                db_session.query(VirtualSink).order_by(VirtualSink.channel_number).all()
            )
            # Map channel number to sink name (CC numbers match channel numbers)
            return {sink.channel_number: sink.name for sink in sinks}

    except Exception as e:
        logger.error(f"Error getting fader mapping: {e}", exc_info=True)
        return {}


def get_button_actions_for_sink(sink_name: str) -> Dict[str, int]:
    """
    Get button actions (MIDI notes) for a specific sink.

    Returns a dict mapping action type to MIDI note number.

    Args:
        sink_name: Name of the sink

    Returns:
        Dictionary like {'speaker': 36, 'headphone': 37, 'mute': 38}
    """
    try:
        with get_db_session() as db_session:
            sink = db_session.query(VirtualSink).filter_by(name=sink_name).first()
            if not sink:
                logger.warning(f"Sink '{sink_name}' not found")
                return {}

            mappings = db_session.query(MidiMapping).filter_by(sink_id=sink.id).all()

            return {mapping.action: mapping.midi_note for mapping in mappings}

    except Exception as e:
        logger.error(
            f"Error getting button actions for '{sink_name}': {e}", exc_info=True
        )
        return {}


# =============================================================================
# Configuration Helpers
# =============================================================================


def get_hardware_device_map() -> Dict[str, str]:
    """
    Get mapping of output names to device names.

    Returns:
        Dictionary mapping output names to PulseAudio device names
    """
    try:
        with get_db_session() as db_session:
            outputs = db_session.query(HardwareOutput).filter_by(is_active=True).all()
            return {output.name: output.device_name for output in outputs}

    except Exception as e:
        logger.error(f"Error getting hardware device map: {e}", exc_info=True)
        return {}


def get_sink_channel_map() -> Dict[str, int]:
    """
    Get mapping of sink names to channel numbers.

    Returns:
        Dictionary mapping sink names to channel numbers
    """
    try:
        with get_db_session() as db_session:
            sinks = db_session.query(VirtualSink).filter_by(is_active=True).all()
            return {sink.name: sink.channel_number for sink in sinks}

    except Exception as e:
        logger.error(f"Error getting sink channel map: {e}", exc_info=True)
        return {}


def get_active_sink_names() -> List[str]:
    """
    Get list of active sink names.

    Returns:
        List of sink names
    """
    try:
        with get_db_session() as db_session:
            sinks = (
                db_session.query(VirtualSink.name)
                .filter_by(is_active=True)
                .order_by(VirtualSink.channel_number)
                .all()
            )
            # Extract just the names from the tuples
            return [sink[0] for sink in sinks]

    except Exception as e:
        logger.error(f"Error getting active sink names: {e}", exc_info=True)
        return []


def get_active_output_names() -> List[str]:
    """
    Get list of active output names.

    Returns:
        List of output names
    """
    try:
        with get_db_session() as db_session:
            outputs = (
                db_session.query(HardwareOutput.name).filter_by(is_active=True).all()
            )
            # Extract just the names from the tuples
            return [output[0] for output in outputs]

    except Exception as e:
        logger.error(f"Error getting active output names: {e}", exc_info=True)
        return []


# =============================================================================
# Validation Helpers
# =============================================================================


def validate_sink_name(sink_name: str) -> bool:
    """
    Check if a sink name exists in the database.

    Args:
        sink_name: Name to validate

    Returns:
        True if sink exists, False otherwise
    """
    try:
        with get_db_session() as db_session:
            sink = db_session.query(VirtualSink).filter_by(name=sink_name).first()
            return sink is not None

    except Exception as e:
        logger.error(f"Error validating sink name '{sink_name}': {e}", exc_info=True)
        return False


def validate_output_name(output_name: str) -> bool:
    """
    Check if an output name exists in the database.

    Args:
        output_name: Name to validate

    Returns:
        True if output exists, False otherwise
    """
    try:
        with get_db_session() as db_session:
            output = db_session.query(HardwareOutput).filter_by(name=output_name).first()
            return output is not None

    except Exception as e:
        logger.error(f"Error validating output name '{output_name}': {e}", exc_info=True)
        return False


# =============================================================================
# Bulk Operations
# =============================================================================


def get_complete_config() -> Dict[str, Any]:
    """
    Get complete configuration including all settings, sinks, outputs, and mappings.

    Returns:
        Dictionary with complete configuration
    """
    try:
        from app.database.models import (
            get_all_config,
            get_all_hardware_outputs,
            get_all_midi_mappings,
            get_all_virtual_sinks,
        )

        config = {
            "settings": get_all_config(),
            "hardware_outputs": {
                output.name: {
                    "device_name": output.device_name,
                    "description": output.description,
                    "is_active": output.is_active,
                }
                for output in get_all_hardware_outputs()
            },
            "virtual_sinks": {
                sink.name: {
                    "channel_number": sink.channel_number,
                    "description": sink.description,
                    "is_active": sink.is_active,
                }
                for sink in get_all_virtual_sinks()
            },
            "midi_mappings": get_all_midi_mappings(),
        }

        return config

    except Exception as e:
        logger.error(f"Error getting complete config: {e}", exc_info=True)
        return {}


def get_system_status() -> Dict[str, Any]:
    """
    Get current system status including database info and configuration summary.

    Returns:
        Dictionary with system status
    """
    try:
        from app.database.models import (
            get_all_config,
            get_all_hardware_outputs,
            get_all_sessions,
            get_all_virtual_sinks,
            get_current_session,
        )

        current_session = get_current_session()

        status = {
            "database_initialized": True,
            "config_entries": len(get_all_config()),
            "hardware_outputs": len(get_all_hardware_outputs()),
            "virtual_sinks": len(get_all_virtual_sinks()),
            "total_sessions": len(get_all_sessions()),
            "current_session": current_session.name if current_session else None,
        }

        return status

    except Exception as e:
        logger.error(f"Error getting system status: {e}", exc_info=True)
        return {"database_initialized": False, "error": str(e)}
