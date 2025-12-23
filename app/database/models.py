"""
Database Models Module

SQLAlchemy ORM models for database tables.
Provides data models and database interaction functions.
"""

import logging
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

logger = logging.getLogger(__name__)

# Create declarative base
Base = declarative_base()

# Global engine and session factory (initialized by init_database)
_engine = None
_SessionFactory = None


# =============================================================================
# ORM Models
# =============================================================================


class Config(Base):
    """Configuration key-value store."""

    __tablename__ = "config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    description = Column(Text)
    value_type = Column(String, default="string")  # string, integer, float, boolean, json
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Config(key='{self.key}', value='{self.value}')>"


class HardwareOutput(Base):
    """Hardware audio output devices."""

    __tablename__ = "hardware_outputs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    device_name = Column(String, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    session_connections = relationship(
        "SessionConnection", back_populates="output", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<HardwareOutput(name='{self.name}', device='{self.device_name}')>"


class VirtualSink(Base):
    """Virtual audio sinks/channels."""

    __tablename__ = "virtual_sinks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_number = Column(Integer, unique=True, nullable=False)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    midi_mappings = relationship(
        "MidiMapping", back_populates="sink", cascade="all, delete-orphan"
    )
    session_volumes = relationship(
        "SessionVolume", back_populates="sink", cascade="all, delete-orphan"
    )
    session_connections = relationship(
        "SessionConnection", back_populates="sink", cascade="all, delete-orphan"
    )
    session_mutes = relationship(
        "SessionMute", back_populates="sink", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<VirtualSink(channel={self.channel_number}, name='{self.name}')>"


class MidiMapping(Base):
    """MIDI button to action mappings."""

    __tablename__ = "midi_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    midi_note = Column(Integer, unique=True, nullable=False, index=True)
    sink_id = Column(
        Integer, ForeignKey("virtual_sinks.id", ondelete="CASCADE"), nullable=False
    )
    action = Column(String, nullable=False)  # 'speaker', 'headphone', 'mute'
    description = Column(Text)

    # Relationships
    sink = relationship("VirtualSink", back_populates="midi_mappings")

    def __repr__(self):
        return f"<MidiMapping(note={self.midi_note}, action='{self.action}')>"


class Session(Base):
    """Saved audio state sessions."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    is_current = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    volumes = relationship(
        "SessionVolume", back_populates="session", cascade="all, delete-orphan"
    )
    connections = relationship(
        "SessionConnection", back_populates="session", cascade="all, delete-orphan"
    )
    mutes = relationship(
        "SessionMute", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Session(name='{self.name}', current={self.is_current})>"


class SessionVolume(Base):
    """Session volume state."""

    __tablename__ = "session_volumes"
    __table_args__ = (
        UniqueConstraint("session_id", "sink_id", name="uq_session_sink_volume"),
        Index("idx_session_volumes", "session_id", "sink_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    sink_id = Column(
        Integer, ForeignKey("virtual_sinks.id", ondelete="CASCADE"), nullable=False
    )
    volume = Column(Float, nullable=False)  # 0.0 to 1.0

    # Relationships
    session = relationship("Session", back_populates="volumes")
    sink = relationship("VirtualSink", back_populates="session_volumes")

    def __repr__(self):
        return f"<SessionVolume(session_id={self.session_id}, sink_id={self.sink_id}, vol={self.volume})>"


class SessionConnection(Base):
    """Session connection state."""

    __tablename__ = "session_connections"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "sink_id", "output_id", name="uq_session_sink_output"
        ),
        Index("idx_session_connections", "session_id", "sink_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    sink_id = Column(
        Integer, ForeignKey("virtual_sinks.id", ondelete="CASCADE"), nullable=False
    )
    output_id = Column(
        Integer, ForeignKey("hardware_outputs.id", ondelete="CASCADE"), nullable=False
    )
    is_connected = Column(Boolean, default=True)

    # Relationships
    session = relationship("Session", back_populates="connections")
    sink = relationship("VirtualSink", back_populates="session_connections")
    output = relationship("HardwareOutput", back_populates="session_connections")

    def __repr__(self):
        return f"<SessionConnection(session_id={self.session_id}, sink_id={self.sink_id}, output_id={self.output_id})>"


class SessionMute(Base):
    """Session mute state."""

    __tablename__ = "session_mutes"
    __table_args__ = (
        UniqueConstraint("session_id", "sink_id", name="uq_session_sink_mute"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    sink_id = Column(
        Integer, ForeignKey("virtual_sinks.id", ondelete="CASCADE"), nullable=False
    )
    is_muted = Column(Boolean, default=False)

    # Relationships
    session = relationship("Session", back_populates="mutes")
    sink = relationship("VirtualSink", back_populates="session_mutes")

    def __repr__(self):
        return f"<SessionMute(session_id={self.session_id}, sink_id={self.sink_id}, muted={self.is_muted})>"


# =============================================================================
# Database Initialization and Management
# =============================================================================


def _ensure_single_current_session(mapper, connection, target):
    """
    SQLAlchemy event listener to ensure only one session is marked as current.
    This is a Python-side implementation of the trigger from schema.sql.
    """
    if target.is_current:
        # Clear is_current flag from all other sessions
        connection.execute(
            Session.__table__.update()
            .where(Session.id != target.id)
            .values(is_current=False)
        )


# Register the event listener
event.listen(Session, "before_update", _ensure_single_current_session)
event.listen(Session, "before_insert", _ensure_single_current_session)


def init_database(db_path: str = None) -> bool:
    """
    Initialize database with schema and default data.

    Args:
        db_path: Path to SQLite database file. If None, uses default path.

    Returns:
        True if initialization successful, False otherwise
    """
    global _engine, _SessionFactory

    try:
        # Use default path if not provided
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "../../data/midi_deck.db")

        # Ensure the directory exists
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # Create engine
        db_url = f"sqlite:///{db_path}"
        _engine = create_engine(db_url, echo=False)

        # Create session factory (expire_on_commit=False to avoid detached instance errors)
        _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)

        # Create all tables
        Base.metadata.create_all(_engine)

        logger.info(f"Database initialized at: {db_path}")

        # Populate with default data if tables are empty
        _populate_default_data()

        return True

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        return False


def _populate_default_data():
    """Populate database with default configuration data."""
    with get_db_session() as session:
        # Check if database is already populated
        if session.query(Config).count() > 0:
            logger.debug("Database already contains data, skipping default population")
            return

        logger.info("Populating database with default data...")

        # Default configuration values
        default_configs = [
            (
                "midi_device_name",
                "MIDI Deck",
                "Name of MIDI device to connect to",
                "string",
            ),
            ("jitter_threshold", "2", "Threshold for filtering MIDI jitter", "integer"),
            ("default_output", "MainSink", "Default system output sink", "string"),
            (
                "log_level",
                "INFO",
                "Logging level (DEBUG, INFO, WARNING, ERROR)",
                "string",
            ),
            ("web_host", "127.0.0.1", "Web interface host", "string"),
            ("web_port", "5000", "Web interface port", "integer"),
            (
                "auto_save_session",
                "true",
                "Automatically save session on changes",
                "boolean",
            ),
        ]

        for key, value, description, value_type in default_configs:
            config = Config(
                key=key, value=value, description=description, value_type=value_type
            )
            session.add(config)

        # Default hardware outputs
        default_outputs = [
            (
                "SpeakerOut",
                "alsa_output.pci-0000_00_1f.3.analog-stereo",
                "Built-in Speakers",
            ),
            (
                "HeadphoneOut",
                "alsa_output.usb-3142_fifine_Microphone-00.analog-stereo",
                "USB Headphones",
            ),
        ]

        for name, device_name, description in default_outputs:
            output = HardwareOutput(
                name=name, device_name=device_name, description=description
            )
            session.add(output)

        # Default virtual sinks
        default_sinks = [
            (1, "MainSink", "Main Audio Channel"),
            (2, "WebSink", "Web Browser Audio"),
            (3, "MusicSink", "Music Player Audio"),
            (4, "DiscordSink", "Discord/VoIP Audio"),
        ]

        sink_map = {}
        for channel_number, name, description in default_sinks:
            sink = VirtualSink(
                channel_number=channel_number, name=name, description=description
            )
            session.add(sink)
            session.flush()  # Flush to get the ID
            sink_map[name] = sink.id

        # Default MIDI mappings
        default_mappings = [
            # MainSink (Channel 1)
            (36, "MainSink", "speaker", "MainSink -> Speaker Toggle"),
            (37, "MainSink", "headphone", "MainSink -> Headphone Toggle"),
            (38, "MainSink", "mute", "MainSink -> Mute Toggle"),
            # WebSink (Channel 2)
            (40, "WebSink", "speaker", "WebSink -> Speaker Toggle"),
            (41, "WebSink", "headphone", "WebSink -> Headphone Toggle"),
            (42, "WebSink", "mute", "WebSink -> Mute Toggle"),
            # MusicSink (Channel 3)
            (44, "MusicSink", "speaker", "MusicSink -> Speaker Toggle"),
            (45, "MusicSink", "headphone", "MusicSink -> Headphone Toggle"),
            (46, "MusicSink", "mute", "MusicSink -> Mute Toggle"),
            # DiscordSink (Channel 4)
            (48, "DiscordSink", "speaker", "DiscordSink -> Speaker Toggle"),
            (49, "DiscordSink", "headphone", "DiscordSink -> Headphone Toggle"),
            (50, "DiscordSink", "mute", "DiscordSink -> Mute Toggle"),
        ]

        for midi_note, sink_name, action, description in default_mappings:
            mapping = MidiMapping(
                midi_note=midi_note,
                sink_id=sink_map[sink_name],
                action=action,
                description=description,
            )
            session.add(mapping)

        # Create default session
        default_session = Session(
            name="Default", description="Default audio configuration", is_current=True
        )
        session.add(default_session)
        session.flush()

        # Add default volumes for each sink (0.5 = 50% volume)
        for sink_name, sink_id in sink_map.items():
            volume = SessionVolume(
                session_id=default_session.id, sink_id=sink_id, volume=0.5
            )
            session.add(volume)

        # Add default mute states (all unmuted)
        for sink_name, sink_id in sink_map.items():
            mute = SessionMute(
                session_id=default_session.id, sink_id=sink_id, is_muted=False
            )
            session.add(mute)

        session.commit()
        logger.info("Default data populated successfully")


@contextmanager
def get_db_session() -> DBSession:
    """
    Get database session as a context manager.

    Yields:
        SQLAlchemy session

    Example:
        with get_db_session() as session:
            config = session.query(Config).filter_by(key='log_level').first()
    """
    if _SessionFactory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# =============================================================================
# CRUD Operations - Config
# =============================================================================


def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get configuration value.

    Args:
        key: Configuration key
        default: Default value if not found

    Returns:
        Configuration value or default
    """
    try:
        with get_db_session() as session:
            config = session.query(Config).filter_by(key=key).first()
            if config is None:
                return default

            # Convert value based on type
            if config.value_type == "integer":
                return int(config.value)
            elif config.value_type == "float":
                return float(config.value)
            elif config.value_type == "boolean":
                return config.value.lower() in ("true", "1", "yes")
            else:
                return config.value
    except Exception as e:
        logger.error(f"Error getting config value '{key}': {e}")
        return default


def set_config_value(
    key: str, value: Any, description: str = None, value_type: str = None
):
    """
    Set configuration value.

    Args:
        key: Configuration key
        value: Value to set
        description: Optional description
        value_type: Optional value type (string, integer, float, boolean, json)
    """
    try:
        with get_db_session() as session:
            config = session.query(Config).filter_by(key=key).first()

            if config is None:
                # Create new config entry
                config = Config(
                    key=key,
                    value=str(value),
                    description=description,
                    value_type=value_type or "string",
                )
                session.add(config)
            else:
                # Update existing config
                config.value = str(value)
                config.updated_at = datetime.utcnow()
                if description is not None:
                    config.description = description
                if value_type is not None:
                    config.value_type = value_type

            session.commit()
            logger.debug(f"Config updated: {key} = {value}")
    except Exception as e:
        logger.error(f"Error setting config value '{key}': {e}")
        raise


def get_all_config() -> Dict[str, Any]:
    """
    Get all configuration values as a dictionary.

    Returns:
        Dictionary of all config key-value pairs
    """
    try:
        with get_db_session() as session:
            configs = session.query(Config).all()
            result = {}
            for config in configs:
                # Convert value based on type
                if config.value_type == "integer":
                    result[config.key] = int(config.value)
                elif config.value_type == "float":
                    result[config.key] = float(config.value)
                elif config.value_type == "boolean":
                    result[config.key] = config.value.lower() in ("true", "1", "yes")
                else:
                    result[config.key] = config.value
            return result
    except Exception as e:
        logger.error(f"Error getting all config: {e}")
        return {}


# =============================================================================
# CRUD Operations - Hardware Outputs
# =============================================================================


def get_all_hardware_outputs(active_only: bool = False) -> List[HardwareOutput]:
    """
    Get all hardware outputs.

    Args:
        active_only: If True, only return active outputs

    Returns:
        List of HardwareOutput objects
    """
    try:
        with get_db_session() as session:
            query = session.query(HardwareOutput)
            if active_only:
                query = query.filter_by(is_active=True)
            # Eager load to avoid detached instance errors
            results = query.all()
            # Trigger attribute loading while in session
            for output in results:
                _ = output.name, output.device_name, output.description, output.is_active
            return results
    except Exception as e:
        logger.error(f"Error getting hardware outputs: {e}")
        return []


def get_hardware_output_by_name(name: str) -> Optional[HardwareOutput]:
    """
    Get hardware output by name.

    Args:
        name: Output name

    Returns:
        HardwareOutput object or None
    """
    try:
        with get_db_session() as session:
            return session.query(HardwareOutput).filter_by(name=name).first()
    except Exception as e:
        logger.error(f"Error getting hardware output '{name}': {e}")
        return None


def add_hardware_output(name: str, device_name: str, description: str = None) -> bool:
    """
    Add new hardware output.

    Args:
        name: Output name
        device_name: PulseAudio device name
        description: Optional description

    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db_session() as session:
            output = HardwareOutput(
                name=name, device_name=device_name, description=description
            )
            session.add(output)
            session.commit()
            logger.info(f"Hardware output added: {name}")
            return True
    except Exception as e:
        logger.error(f"Error adding hardware output '{name}': {e}")
        return False


def get_hardware_output_by_id(output_id: int) -> Optional[HardwareOutput]:
    """Get hardware output by ID."""
    try:
        with get_db_session() as session:
            return session.query(HardwareOutput).filter_by(id=output_id).first()
    except Exception as e:
        logger.error(f"Error getting hardware output by ID {output_id}: {e}")
        return None


def update_hardware_output(output_id: int, **kwargs) -> Optional[HardwareOutput]:
    """Update hardware output."""
    try:
        with get_db_session() as session:
            output = session.query(HardwareOutput).filter_by(id=output_id).first()
            if not output:
                return None
            for key, value in kwargs.items():
                if hasattr(output, key):
                    setattr(output, key, value)
            session.commit()
            logger.info(f"Updated hardware output ID {output_id}")
            return output
    except Exception as e:
        logger.error(f"Error updating hardware output {output_id}: {e}")
        return None


def delete_hardware_output(output_id: int) -> bool:
    """Delete hardware output by ID."""
    try:
        with get_db_session() as session:
            output = session.query(HardwareOutput).filter_by(id=output_id).first()
            if not output:
                return False
            session.delete(output)
            session.commit()
            logger.info(f"Deleted hardware output ID {output_id}")
            return True
    except Exception as e:
        logger.error(f"Error deleting hardware output {output_id}: {e}")
        return False


# =============================================================================
# CRUD Operations - Virtual Sinks
# =============================================================================


def get_all_virtual_sinks(active_only: bool = False) -> List[VirtualSink]:
    """
    Get all virtual sinks.

    Args:
        active_only: If True, only return active sinks

    Returns:
        List of VirtualSink objects
    """
    try:
        with get_db_session() as session:
            query = session.query(VirtualSink).order_by(VirtualSink.channel_number)
            if active_only:
                query = query.filter_by(is_active=True)
            results = query.all()
            # Trigger attribute loading while in session
            for sink in results:
                _ = sink.name, sink.channel_number, sink.description, sink.is_active
            return results
    except Exception as e:
        logger.error(f"Error getting virtual sinks: {e}")
        return []


def get_virtual_sink_by_name(name: str) -> Optional[VirtualSink]:
    """
    Get virtual sink by name.

    Args:
        name: Sink name

    Returns:
        VirtualSink object or None
    """
    try:
        with get_db_session() as session:
            return session.query(VirtualSink).filter_by(name=name).first()
    except Exception as e:
        logger.error(f"Error getting virtual sink '{name}': {e}")
        return None


def get_virtual_sink_by_channel(channel_number: int) -> Optional[VirtualSink]:
    """
    Get virtual sink by channel number.

    Args:
        channel_number: Channel number (1-4)

    Returns:
        VirtualSink object or None
    """
    try:
        with get_db_session() as session:
            return (
                session.query(VirtualSink)
                .filter_by(channel_number=channel_number)
                .first()
            )
    except Exception as e:
        logger.error(f"Error getting virtual sink for channel {channel_number}: {e}")
        return None


def get_virtual_sink_by_id(sink_id: int) -> Optional[VirtualSink]:
    """Get virtual sink by ID."""
    try:
        with get_db_session() as session:
            return session.query(VirtualSink).filter_by(id=sink_id).first()
    except Exception as e:
        logger.error(f"Error getting virtual sink by ID {sink_id}: {e}")
        return None


def create_virtual_sink(
    name: str, description: str, channel_number: int, **kwargs
) -> Optional[VirtualSink]:
    """Create a new virtual sink."""
    try:
        with get_db_session() as session:
            sink = VirtualSink(
                name=name,
                description=description,
                channel_number=channel_number,
                **kwargs,
            )
            session.add(sink)
            session.commit()
            logger.info(f"Created virtual sink: {name}")
            return sink
    except Exception as e:
        logger.error(f"Error creating virtual sink '{name}': {e}")
        return None


def update_virtual_sink(sink_id: int, **kwargs) -> Optional[VirtualSink]:
    """Update virtual sink."""
    try:
        with get_db_session() as session:
            sink = session.query(VirtualSink).filter_by(id=sink_id).first()
            if not sink:
                return None
            for key, value in kwargs.items():
                if hasattr(sink, key):
                    setattr(sink, key, value)
            session.commit()
            logger.info(f"Updated virtual sink ID {sink_id}")
            return sink
    except Exception as e:
        logger.error(f"Error updating virtual sink {sink_id}: {e}")
        return None


def delete_virtual_sink(sink_id: int) -> bool:
    """Delete virtual sink by ID."""
    try:
        with get_db_session() as session:
            sink = session.query(VirtualSink).filter_by(id=sink_id).first()
            if not sink:
                return False
            session.delete(sink)
            session.commit()
            logger.info(f"Deleted virtual sink ID {sink_id}")
            return True
    except Exception as e:
        logger.error(f"Error deleting virtual sink {sink_id}: {e}")
        return False


# =============================================================================
# CRUD Operations - MIDI Mappings
# =============================================================================


def get_midi_mapping(note: int) -> Optional[Dict[str, Any]]:
    """
    Get MIDI mapping for a note.

    Args:
        note: MIDI note number

    Returns:
        Dictionary with mapping info or None
    """
    try:
        with get_db_session() as session:
            mapping = session.query(MidiMapping).filter_by(midi_note=note).first()
            if mapping is None:
                return None

            return {
                "midi_note": mapping.midi_note,
                "sink_id": mapping.sink_id,
                "sink_name": mapping.sink.name,
                "action": mapping.action,
                "description": mapping.description,
            }
    except Exception as e:
        logger.error(f"Error getting MIDI mapping for note {note}: {e}")
        return None


def get_all_midi_mappings() -> List[Dict[str, Any]]:
    """
    Get all MIDI mappings.

    Returns:
        List of dictionaries with mapping info
    """
    try:
        with get_db_session() as session:
            mappings = session.query(MidiMapping).order_by(MidiMapping.midi_note).all()
            return [
                {
                    "id": m.id,
                    "midi_note": m.midi_note,
                    "sink_id": m.sink_id,
                    "sink_name": m.sink.name,
                    "action": m.action,
                    "description": m.description,
                }
                for m in mappings
            ]
    except Exception as e:
        logger.error(f"Error getting all MIDI mappings: {e}")
        return []


def get_midi_mapping_by_id(mapping_id: int) -> Optional[MidiMapping]:
    """Get MIDI mapping by ID."""
    try:
        with get_db_session() as session:
            return session.query(MidiMapping).filter_by(id=mapping_id).first()
    except Exception as e:
        logger.error(f"Error getting MIDI mapping by ID {mapping_id}: {e}")
        return None


def update_midi_mapping(mapping_id: int, **kwargs) -> Optional[MidiMapping]:
    """Update MIDI mapping."""
    try:
        with get_db_session() as session:
            mapping = session.query(MidiMapping).filter_by(id=mapping_id).first()
            if not mapping:
                return None
            for key, value in kwargs.items():
                if hasattr(mapping, key):
                    setattr(mapping, key, value)
            session.commit()
            logger.info(f"Updated MIDI mapping ID {mapping_id}")
            return mapping
    except Exception as e:
        logger.error(f"Error updating MIDI mapping {mapping_id}: {e}")
        return None


# =============================================================================
# CRUD Operations - Sessions
# =============================================================================


def get_all_sessions() -> List[Session]:
    """
    Get all sessions.

    Returns:
        List of Session objects
    """
    try:
        with get_db_session() as session:
            results = session.query(Session).order_by(Session.updated_at.desc()).all()
            # Trigger attribute loading while in session
            for sess in results:
                _ = (
                    sess.name,
                    sess.description,
                    sess.is_current,
                    sess.created_at,
                    sess.updated_at,
                )
            return results
    except Exception as e:
        logger.error(f"Error getting all sessions: {e}")
        return []


def get_current_session() -> Optional[Session]:
    """
    Get the current active session.

    Returns:
        Session object or None
    """
    try:
        with get_db_session() as session:
            result = session.query(Session).filter_by(is_current=True).first()
            if result:
                # Trigger attribute loading while in session
                _ = (
                    result.name,
                    result.description,
                    result.is_current,
                    result.created_at,
                    result.updated_at,
                )
            return result
    except Exception as e:
        logger.error(f"Error getting current session: {e}")
        return None


def create_session(
    name: str, description: str = None, set_as_current: bool = False
) -> Optional[int]:
    """
    Create new session.

    Args:
        name: Session name
        description: Optional description
        set_as_current: If True, set as current session

    Returns:
        Session ID if successful, None otherwise
    """
    try:
        with get_db_session() as session:
            new_session = Session(
                name=name, description=description, is_current=set_as_current
            )
            session.add(new_session)
            session.commit()
            logger.info(f"Session created: {name}")
            return new_session.id
    except Exception as e:
        logger.error(f"Error creating session '{name}': {e}")
        return None


def set_current_session(session_id: int) -> bool:
    """
    Set a session as current.

    Args:
        session_id: Session ID

    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db_session() as session:
            # Clear current flag from all sessions
            session.query(Session).update({Session.is_current: False})

            # Set the specified session as current
            target_session = session.query(Session).filter_by(id=session_id).first()
            if target_session:
                target_session.is_current = True
                session.commit()
                logger.info(f"Current session set to: {target_session.name}")
                return True
            else:
                logger.warning(f"Session {session_id} not found")
                return False
    except Exception as e:
        logger.error(f"Error setting current session {session_id}: {e}")
        return False


def delete_session(session_id: int) -> bool:
    """
    Delete a session.

    Args:
        session_id: Session ID

    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db_session() as session:
            target_session = session.query(Session).filter_by(id=session_id).first()
            if target_session:
                session.delete(target_session)
                session.commit()
                logger.info(f"Session deleted: {target_session.name}")
                return True
            else:
                logger.warning(f"Session {session_id} not found")
                return False
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        return False


def get_session_by_id(session_id: int) -> Optional[Session]:
    """Get session by ID."""
    try:
        with get_db_session() as session:
            result = session.query(Session).filter_by(id=session_id).first()
            if result:
                _ = result.name, result.description, result.is_current
            return result
    except Exception as e:
        logger.error(f"Error getting session by ID {session_id}: {e}")
        return None


def update_session(session_id: int, **kwargs) -> Optional[Session]:
    """Update session."""
    try:
        with get_db_session() as session:
            sess = session.query(Session).filter_by(id=session_id).first()
            if not sess:
                return None
            for key, value in kwargs.items():
                if hasattr(sess, key) and key != "id":
                    setattr(sess, key, value)
            session.commit()
            logger.info(f"Updated session ID {session_id}")
            return sess
    except Exception as e:
        logger.error(f"Error updating session {session_id}: {e}")
        return None
