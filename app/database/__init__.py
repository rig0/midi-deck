"""
Database Layer Module

Handles database connections, ORM models, and data persistence.
Provides repository-style functions for accessing configuration
and session data.
"""

# Import database access layer functions
from .db import (
    get_active_output_names,
    get_active_sink_names,
    get_button_actions_for_sink,
    get_complete_config,
    get_current_session_state,
    get_fader_mapping,
    get_hardware_device_map,
    get_sink_channel_map,
    get_system_status,
    load_session_state,
    save_session_state,
    validate_output_name,
    validate_sink_name,
)

# Import migration utilities
from .migrations import (
    apply_migrations,
    backup_database,
    check_schema_version,
    export_config_to_dict,
    import_config_from_dict,
    migrate_from_hardcoded_config,
    reset_database,
)

# Import ORM models and initialization
from .models import (
    Config,
    HardwareOutput,
    MidiMapping,
    Session,
    SessionConnection,
    SessionMute,
    SessionVolume,
    VirtualSink,
    create_session,
    delete_session,
    get_all_config,
    get_all_hardware_outputs,
    get_all_midi_mappings,
    get_all_sessions,
    get_all_virtual_sinks,
    get_config_value,
    get_current_session,
    get_db_session,
    get_hardware_output_by_name,
    get_midi_mapping,
    get_virtual_sink_by_channel,
    get_virtual_sink_by_name,
    init_database,
    set_config_value,
    set_current_session,
)

__all__ = [
    # ORM Models
    "Config",
    "HardwareOutput",
    "VirtualSink",
    "MidiMapping",
    "Session",
    "SessionVolume",
    "SessionConnection",
    "SessionMute",
    # Database initialization
    "init_database",
    "get_db_session",
    # Config CRUD
    "get_config_value",
    "set_config_value",
    "get_all_config",
    # Hardware outputs CRUD
    "get_all_hardware_outputs",
    "get_hardware_output_by_name",
    # Virtual sinks CRUD
    "get_all_virtual_sinks",
    "get_virtual_sink_by_name",
    "get_virtual_sink_by_channel",
    # MIDI mappings CRUD
    "get_midi_mapping",
    "get_all_midi_mappings",
    # Sessions CRUD
    "get_all_sessions",
    "get_current_session",
    "create_session",
    "set_current_session",
    "delete_session",
    # Migration utilities
    "migrate_from_hardcoded_config",
    "apply_migrations",
    "check_schema_version",
    "backup_database",
    "reset_database",
    "export_config_to_dict",
    "import_config_from_dict",
    # Database access layer
    "save_session_state",
    "load_session_state",
    "get_current_session_state",
    "get_fader_mapping",
    "get_button_actions_for_sink",
    "get_hardware_device_map",
    "get_sink_channel_map",
    "get_active_sink_names",
    "get_active_output_names",
    "validate_sink_name",
    "validate_output_name",
    "get_complete_config",
    "get_system_status",
]
