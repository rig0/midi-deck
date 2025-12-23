"""
Web Routes and API Endpoints

Defines Flask routes for both web pages and RESTful API endpoints.
"""

import logging

from flask import Blueprint, jsonify, render_template, request

from app.database.db import get_complete_config, get_system_status
from app.database.models import add_hardware_output as create_hardware_output
from app.database.models import (
    create_session,
    create_virtual_sink,
    delete_hardware_output,
    delete_session,
    delete_virtual_sink,
    get_all_config_items,
    get_all_hardware_outputs,
    get_all_midi_mappings,
    get_all_sessions,
    get_all_virtual_sinks,
    get_config_value,
    get_hardware_output_by_id,
    get_midi_mapping_by_id,
    get_session_by_id,
    get_virtual_sink_by_id,
    set_config_value,
    set_current_session,
    update_hardware_output,
    update_midi_mapping,
    update_session,
    update_virtual_sink,
)

from .app import get_managers

logger = logging.getLogger(__name__)

# Create blueprints
web_bp = Blueprint("web", __name__)
api_bp = Blueprint("api", __name__)


# =============================================================================
# Web Page Routes (Phase 6)
# =============================================================================


@web_bp.route("/")
def index():
    """Dashboard/overview page."""
    return render_template("index.html")


@web_bp.route("/config")
def config_page():
    """Configuration page."""
    return render_template("config.html")


@web_bp.route("/sessions")
def sessions_page():
    """Session management page."""
    return render_template("sessions.html")


@web_bp.route("/control")
def control_page():
    """Real-time audio control page."""
    return render_template("control.html")


@web_bp.route("/midi")
def midi_page():
    """MIDI mapping configuration page."""
    return render_template("midi.html")


# =============================================================================
# API Endpoints - Configuration
# =============================================================================


@api_bp.route("/config", methods=["GET"])
def get_config():
    """Get all configuration values."""
    try:
        config = get_all_config_items()
        return jsonify(
            [
                {
                    "id": c.id,
                    "key": c.key,
                    "value": c.value,
                    "description": c.description,
                    "value_type": c.value_type,
                }
                for c in config
            ]
        )
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/config", methods=["POST"])
def update_config_bulk():
    """Update multiple configuration values."""
    try:
        data = request.json
        if not data or "config" not in data:
            return jsonify({"error": "Missing config data"}), 400

        for key, value in data["config"].items():
            set_config_value(key, str(value))

        return jsonify({"success": True, "message": "Configuration updated"})
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/config/<key>", methods=["PUT"])
def update_config_key(key):
    """Update a single configuration value."""
    try:
        data = request.json
        if not data or "value" not in data:
            return jsonify({"error": "Missing value"}), 400

        set_config_value(key, str(data["value"]))
        return jsonify({"success": True, "key": key, "value": data["value"]})
    except Exception as e:
        logger.error(f"Error updating config key {key}: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# API Endpoints - Hardware Outputs
# =============================================================================


@api_bp.route("/hardware-outputs", methods=["GET"])
def list_hardware_outputs():
    """List all hardware outputs."""
    try:
        outputs = get_all_hardware_outputs()
        return jsonify(
            [
                {
                    "id": o.id,
                    "name": o.name,
                    "device_name": o.device_name,
                    "description": o.description,
                    "is_active": o.is_active,
                }
                for o in outputs
            ]
        )
    except Exception as e:
        logger.error(f"Error listing hardware outputs: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/hardware-outputs", methods=["POST"])
def add_hardware_output():
    """Create new hardware output."""
    try:
        data = request.json
        if not data or "name" not in data or "device_name" not in data:
            return jsonify({"error": "Missing required fields"}), 400

        output = create_hardware_output(
            name=data["name"],
            device_name=data["device_name"],
            description=data.get("description", ""),
            is_active=data.get("is_active", True),
        )

        return jsonify({"success": True, "id": output.id, "name": output.name}), 201
    except Exception as e:
        logger.error(f"Error creating hardware output: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/hardware-outputs/<int:output_id>", methods=["GET"])
def get_hardware_output(output_id):
    """Get hardware output by ID."""
    try:
        output = get_hardware_output_by_id(output_id)
        if not output:
            return jsonify({"error": "Hardware output not found"}), 404

        return jsonify(
            {
                "id": output.id,
                "name": output.name,
                "device_name": output.device_name,
                "description": output.description,
                "is_active": output.is_active,
            }
        )
    except Exception as e:
        logger.error(f"Error getting hardware output: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/hardware-outputs/<int:output_id>", methods=["PUT"])
def update_output(output_id):
    """Update hardware output."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Missing data"}), 400

        output = update_hardware_output(output_id, **data)
        if not output:
            return jsonify({"error": "Hardware output not found"}), 404

        return jsonify({"success": True, "id": output.id})
    except Exception as e:
        logger.error(f"Error updating hardware output: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/hardware-outputs/<int:output_id>", methods=["DELETE"])
def delete_output(output_id):
    """Delete hardware output."""
    try:
        success = delete_hardware_output(output_id)
        if not success:
            return jsonify({"error": "Hardware output not found"}), 404

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error deleting hardware output: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# API Endpoints - Virtual Sinks
# =============================================================================


@api_bp.route("/virtual-sinks", methods=["GET"])
def list_virtual_sinks():
    """List all virtual sinks."""
    try:
        sinks = get_all_virtual_sinks()
        return jsonify(
            [
                {
                    "id": s.id,
                    "channel_number": s.channel_number,
                    "name": s.name,
                    "description": s.description,
                    "is_active": s.is_active,
                }
                for s in sinks
            ]
        )
    except Exception as e:
        logger.error(f"Error listing virtual sinks: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/virtual-sinks", methods=["POST"])
def add_virtual_sink():
    """Create new virtual sink."""
    try:
        data = request.json
        if not data or "channel_number" not in data or "name" not in data:
            return jsonify({"error": "Missing required fields"}), 400

        audio_manager, _, _ = get_managers()
        if audio_manager:
            # Create the sink in PulseAudio
            success = audio_manager.create_virtual_sink(
                data["name"], data.get("description", "")
            )
            if not success:
                return jsonify({"error": "Failed to create sink in PulseAudio"}), 500

        # Create database entry
        sink = create_virtual_sink(
            channel_number=data["channel_number"],
            name=data["name"],
            description=data.get("description", ""),
            is_active=data.get("is_active", True),
        )

        return jsonify({"success": True, "id": sink.id, "name": sink.name}), 201
    except Exception as e:
        logger.error(f"Error creating virtual sink: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/virtual-sinks/<int:sink_id>", methods=["GET"])
def get_virtual_sink(sink_id):
    """Get virtual sink by ID."""
    try:
        sink = get_virtual_sink_by_id(sink_id)
        if not sink:
            return jsonify({"error": "Virtual sink not found"}), 404

        return jsonify(
            {
                "id": sink.id,
                "channel_number": sink.channel_number,
                "name": sink.name,
                "description": sink.description,
                "is_active": sink.is_active,
            }
        )
    except Exception as e:
        logger.error(f"Error getting virtual sink: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/virtual-sinks/<int:sink_id>", methods=["PUT"])
def update_sink(sink_id):
    """Update virtual sink."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Missing data"}), 400

        sink = update_virtual_sink(sink_id, **data)
        if not sink:
            return jsonify({"error": "Virtual sink not found"}), 404

        return jsonify({"success": True, "id": sink.id})
    except Exception as e:
        logger.error(f"Error updating virtual sink: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/virtual-sinks/<int:sink_id>", methods=["DELETE"])
def delete_sink(sink_id):
    """Delete virtual sink."""
    try:
        sink = get_virtual_sink_by_id(sink_id)
        if not sink:
            return jsonify({"error": "Virtual sink not found"}), 404

        audio_manager, _, _ = get_managers()
        if audio_manager:
            # Remove from PulseAudio
            audio_manager.remove_virtual_sink(sink.name)

        # Delete from database
        success = delete_virtual_sink(sink_id)
        if not success:
            return jsonify({"error": "Failed to delete from database"}), 500

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error deleting virtual sink: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# API Endpoints - MIDI Mappings
# =============================================================================


@api_bp.route("/midi-mappings", methods=["GET"])
def list_midi_mappings():
    """List all MIDI mappings."""
    try:
        mappings = get_all_midi_mappings()
        return jsonify(mappings)
    except Exception as e:
        logger.error(f"Error listing MIDI mappings: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/midi-mappings/<int:mapping_id>", methods=["GET"])
def get_midi_mapping(mapping_id):
    """Get MIDI mapping by ID."""
    try:
        mapping = get_midi_mapping_by_id(mapping_id)
        if not mapping:
            return jsonify({"error": "MIDI mapping not found"}), 404

        return jsonify(
            {
                "id": mapping.id,
                "midi_note": mapping.midi_note,
                "sink_id": mapping.sink_id,
                "sink_name": mapping.sink.name if mapping.sink else None,
                "action": mapping.action,
                "description": mapping.description,
            }
        )
    except Exception as e:
        logger.error(f"Error getting MIDI mapping: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/midi-mappings/<int:mapping_id>", methods=["PUT"])
def update_mapping(mapping_id):
    """Update MIDI mapping."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Missing data"}), 400

        mapping = update_midi_mapping(mapping_id, **data)
        if not mapping:
            return jsonify({"error": "MIDI mapping not found"}), 404

        return jsonify({"success": True, "id": mapping.id})
    except Exception as e:
        logger.error(f"Error updating MIDI mapping: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# API Endpoints - Sessions
# =============================================================================


@api_bp.route("/sessions", methods=["GET"])
def list_sessions():
    """List all sessions."""
    try:
        sessions = get_all_sessions()
        return jsonify(
            [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "is_current": s.is_current,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                }
                for s in sessions
            ]
        )
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/sessions", methods=["POST"])
def create_new_session():
    """Create new session."""
    try:
        data = request.json
        if not data or "name" not in data:
            return jsonify({"error": "Missing name"}), 400

        _, _, session_manager = get_managers()
        if not session_manager:
            return jsonify({"error": "Session manager not available"}), 503

        session_id = session_manager.create_session(
            data["name"], data.get("description", "")
        )

        return jsonify({"success": True, "id": session_id, "name": data["name"]}), 201
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/sessions/<int:session_id>", methods=["GET"])
def get_session(session_id):
    """Get session by ID."""
    try:
        session = get_session_by_id(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404

        return jsonify(
            {
                "id": session.id,
                "name": session.name,
                "description": session.description,
                "is_current": session.is_current,
                "created_at": session.created_at.isoformat()
                if session.created_at
                else None,
                "updated_at": session.updated_at.isoformat()
                if session.updated_at
                else None,
            }
        )
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/sessions/<int:session_id>", methods=["PUT"])
def update_session_info(session_id):
    """Update session metadata."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Missing data"}), 400

        session = update_session(session_id, **data)
        if not session:
            return jsonify({"error": "Session not found"}), 404

        return jsonify({"success": True, "id": session.id})
    except Exception as e:
        logger.error(f"Error updating session: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/sessions/<int:session_id>", methods=["DELETE"])
def remove_session(session_id):
    """Delete session."""
    try:
        _, _, session_manager = get_managers()
        if session_manager:
            session_manager.delete_session(session_id)
        else:
            success = delete_session(session_id)
            if not success:
                return jsonify({"error": "Session not found"}), 404

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/sessions/<int:session_id>/activate", methods=["POST"])
def activate_session(session_id):
    """Switch to a different session (load and set as current)."""
    try:
        _, _, session_manager = get_managers()
        if not session_manager:
            # Fallback to just setting current in database
            set_current_session(session_id)
            return jsonify({"success": True, "message": "Session marked as current"})

        # Load the session (this also sets it as current)
        session_manager.load_session(session_id)
        session_manager.set_current_session(session_id)

        return jsonify({"success": True, "message": "Session loaded and activated"})
    except Exception as e:
        logger.error(f"Error activating session: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/sessions/<int:session_id>/save", methods=["POST"])
def save_session_state(session_id):
    """Save current audio state to specific session."""
    try:
        _, _, session_manager = get_managers()
        if not session_manager:
            return jsonify({"error": "Session manager not available"}), 503

        session_manager.save_session(session_id)
        return jsonify({"success": True, "message": "Session saved"})
    except Exception as e:
        logger.error(f"Error saving session: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# API Endpoints - Real-time Audio Control
# =============================================================================


@api_bp.route("/status", methods=["GET"])
def get_status():
    """Get current audio system status."""
    try:
        audio_manager, loopback_manager, _ = get_managers()
        if not audio_manager:
            return jsonify({"error": "Audio manager not available"}), 503

        # Get all virtual sinks from database
        sinks = get_all_virtual_sinks()
        outputs = get_all_hardware_outputs()

        status = {"sinks": [], "outputs": [], "connections": []}

        # Get status for each sink
        for sink in sinks:
            if not sink.is_active:
                continue

            volume = audio_manager.get_volume(sink.name)
            muted = audio_manager.is_muted(sink.name)

            status["sinks"].append(
                {
                    "id": sink.id,
                    "name": sink.name,
                    "channel": sink.channel_number,
                    "volume": volume if volume is not None else 0.5,
                    "muted": muted if muted is not None else False,
                }
            )

        # Get outputs
        for output in outputs:
            status["outputs"].append(
                {"id": output.id, "name": output.name, "device_name": output.device_name}
            )

        # Get connections if loopback manager available
        if loopback_manager:
            for sink in sinks:
                if not sink.is_active:
                    continue
                for output in outputs:
                    if not output.is_active:
                        continue
                    connected = loopback_manager.is_connected(
                        sink.name, output.device_name
                    )
                    status["connections"].append(
                        {
                            "sink_id": sink.id,
                            "output_id": output.id,
                            "connected": connected,
                        }
                    )

        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/sinks/<int:sink_id>/volume", methods=["POST"])
def set_sink_volume(sink_id):
    """Set volume for a sink."""
    try:
        data = request.json
        if not data or "volume" not in data:
            return jsonify({"error": "Missing volume"}), 400

        volume = float(data["volume"])
        if not (0.0 <= volume <= 1.0):
            return jsonify({"error": "Volume must be between 0.0 and 1.0"}), 400

        audio_manager, _, _ = get_managers()
        if not audio_manager:
            return jsonify({"error": "Audio manager not available"}), 503

        sink = get_virtual_sink_by_id(sink_id)
        if not sink:
            return jsonify({"error": "Sink not found"}), 404

        success = audio_manager.set_volume(sink.name, volume)
        if not success:
            return jsonify({"error": "Failed to set volume"}), 500

        return jsonify({"success": True, "volume": volume})
    except Exception as e:
        logger.error(f"Error setting volume: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/sinks/<int:sink_id>/mute", methods=["POST"])
def set_sink_mute(sink_id):
    """Set mute state for a sink."""
    try:
        data = request.json
        if not data or "muted" not in data:
            return jsonify({"error": "Missing muted state"}), 400

        muted = bool(data["muted"])

        audio_manager, _, _ = get_managers()
        if not audio_manager:
            return jsonify({"error": "Audio manager not available"}), 503

        sink = get_virtual_sink_by_id(sink_id)
        if not sink:
            return jsonify({"error": "Sink not found"}), 404

        success = audio_manager.set_mute(sink.name, muted)
        if not success:
            return jsonify({"error": "Failed to set mute"}), 500

        return jsonify({"success": True, "muted": muted})
    except Exception as e:
        logger.error(f"Error setting mute: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/connections/<int:sink_id>/<int:output_id>", methods=["POST"])
def toggle_connection(sink_id, output_id):
    """Toggle loopback connection between sink and output."""
    try:
        _, loopback_manager, _ = get_managers()
        if not loopback_manager:
            return jsonify({"error": "Loopback manager not available"}), 503

        sink = get_virtual_sink_by_id(sink_id)
        if not sink:
            return jsonify({"error": "Sink not found"}), 404

        output = get_hardware_output_by_id(output_id)
        if not output:
            return jsonify({"error": "Output not found"}), 404

        new_state = loopback_manager.toggle(sink.name, output.device_name)

        return jsonify(
            {
                "success": True,
                "connected": new_state,
                "sink": sink.name,
                "output": output.name,
            }
        )
    except Exception as e:
        logger.error(f"Error toggling connection: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# API Endpoints - Hardware Discovery
# =============================================================================


@api_bp.route("/hardware/discover", methods=["GET"])
def discover_hardware():
    """Discover available hardware audio devices."""
    try:
        audio_manager, _, _ = get_managers()
        if not audio_manager:
            return jsonify({"error": "Audio manager not available"}), 503

        devices = audio_manager.list_hardware_sinks()

        return jsonify({"success": True, "devices": devices})
    except Exception as e:
        logger.error(f"Error discovering hardware: {e}")
        return jsonify({"error": str(e)}), 500


logger.info("Routes module loaded successfully")
