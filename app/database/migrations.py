"""
Database Migrations Module

Handles database migration utilities and version management.
Provides functions to migrate from hardcoded configuration to database-backed config.
"""

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def backup_database(db_path: str) -> str:
    """
    Create a backup of the database file.

    Args:
        db_path: Path to database file

    Returns:
        Path to backup file or None if backup failed
    """
    try:
        if not os.path.exists(db_path):
            logger.warning(f"Database file does not exist: {db_path}")
            return None

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.backup_{timestamp}"

        # Copy database file
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backed up to: {backup_path}")

        return backup_path

    except Exception as e:
        logger.error(f"Failed to backup database: {e}", exc_info=True)
        return None


def migrate_from_hardcoded_config(db_path: str = None) -> bool:
    """
    Migrate hardcoded configuration to database.

    This function populates the database with the current hardcoded values
    from app/config/constants.py. It is automatically called by init_database()
    if the database is empty, but can also be called manually.

    Args:
        db_path: Path to database file (optional)

    Returns:
        True if migration successful, False otherwise
    """
    try:
        from app.database.models import init_database

        # Initialize database (will populate with defaults if empty)
        success = init_database(db_path)

        if success:
            logger.info("Migration from hardcoded config completed successfully")
        else:
            logger.error("Migration from hardcoded config failed")

        return success

    except Exception as e:
        logger.error(f"Error during migration: {e}", exc_info=True)
        return False


def apply_migrations(db_path: str) -> bool:
    """
    Apply any pending database migrations.

    This is a placeholder for future migration system. Currently, the database
    schema is managed entirely by SQLAlchemy's Base.metadata.create_all(),
    which handles creating missing tables and columns.

    For future versions, consider using Alembic for proper migration management.

    Args:
        db_path: Path to database file

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Checking for pending migrations...")

        # For now, we don't have a formal migration system
        # SQLAlchemy handles schema creation automatically
        # In the future, integrate Alembic here

        logger.info("No pending migrations (using automatic schema creation)")
        return True

    except Exception as e:
        logger.error(f"Error applying migrations: {e}", exc_info=True)
        return False


def check_schema_version(db_path: str) -> str:
    """
    Check current database schema version.

    This is a placeholder for future version management. Currently returns
    the application version from VERSION file.

    Args:
        db_path: Path to database file

    Returns:
        Schema version string
    """
    try:
        # Try to read version from VERSION file
        version_file = Path(__file__).parent.parent.parent / "VERSION"
        if version_file.exists():
            version = version_file.read_text().strip()
            logger.debug(f"Database schema version: {version}")
            return version
        else:
            logger.warning("VERSION file not found, returning 'unknown'")
            return "unknown"

    except Exception as e:
        logger.error(f"Error checking schema version: {e}", exc_info=True)
        return "unknown"


def reset_database(db_path: str = None, confirm: bool = False) -> bool:
    """
    Reset database to initial state (DANGEROUS - deletes all data).

    This function:
    1. Creates a backup of the existing database
    2. Deletes the database file
    3. Reinitializes with default data

    Args:
        db_path: Path to database file (optional)
        confirm: Must be True to proceed (safety check)

    Returns:
        True if successful, False otherwise
    """
    if not confirm:
        logger.error("reset_database() requires confirm=True to proceed")
        return False

    try:
        from app.database.models import init_database

        # Use default path if not provided
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "../../data/midi_deck.db")

        # Backup existing database
        if os.path.exists(db_path):
            backup_path = backup_database(db_path)
            if backup_path:
                logger.info(f"Backup created at: {backup_path}")

            # Delete existing database
            os.remove(db_path)
            logger.info(f"Deleted database: {db_path}")

        # Reinitialize database
        success = init_database(db_path)

        if success:
            logger.info("Database reset completed successfully")
        else:
            logger.error("Database reset failed during reinitialization")

        return success

    except Exception as e:
        logger.error(f"Error resetting database: {e}", exc_info=True)
        return False


def export_config_to_dict() -> dict:
    """
    Export current database configuration to a dictionary.

    This can be used for backups, migrations, or config sharing.

    Returns:
        Dictionary containing all configuration data
    """
    try:
        from app.database.models import (
            get_all_config,
            get_all_hardware_outputs,
            get_all_midi_mappings,
            get_all_sessions,
            get_all_virtual_sinks,
        )

        config_export = {
            "version": check_schema_version(None),
            "exported_at": datetime.utcnow().isoformat(),
            "config": get_all_config(),
            "hardware_outputs": [
                {
                    "name": output.name,
                    "device_name": output.device_name,
                    "description": output.description,
                    "is_active": output.is_active,
                }
                for output in get_all_hardware_outputs()
            ],
            "virtual_sinks": [
                {
                    "channel_number": sink.channel_number,
                    "name": sink.name,
                    "description": sink.description,
                    "is_active": sink.is_active,
                }
                for sink in get_all_virtual_sinks()
            ],
            "midi_mappings": get_all_midi_mappings(),
            "sessions": [
                {
                    "name": session.name,
                    "description": session.description,
                    "is_current": session.is_current,
                }
                for session in get_all_sessions()
            ],
        }

        logger.info("Configuration exported to dictionary")
        return config_export

    except Exception as e:
        logger.error(f"Error exporting config: {e}", exc_info=True)
        return {}


def import_config_from_dict(config_dict: dict) -> bool:
    """
    Import configuration from a dictionary.

    This can be used to restore from backups or apply shared configurations.

    Args:
        config_dict: Dictionary containing configuration data

    Returns:
        True if successful, False otherwise
    """
    try:
        from app.database.models import (
            MidiMapping,
            Session,
            VirtualSink,
            add_hardware_output,
            get_db_session,
            set_config_value,
        )

        logger.info("Importing configuration from dictionary...")

        # Import config values
        if "config" in config_dict:
            for key, value in config_dict["config"].items():
                set_config_value(key, value)

        # Import hardware outputs
        if "hardware_outputs" in config_dict:
            for output in config_dict["hardware_outputs"]:
                add_hardware_output(
                    output["name"], output["device_name"], output.get("description")
                )

        # Additional imports would require more complex logic
        # to avoid duplicates and handle relationships properly
        # For now, this is a basic implementation

        logger.info("Configuration import completed")
        return True

    except Exception as e:
        logger.error(f"Error importing config: {e}", exc_info=True)
        return False
