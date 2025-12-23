"""
Unit Tests for Database Layer

Tests for database models, CRUD operations, and data integrity.
"""

import os
import tempfile
import unittest
from pathlib import Path

import app.database.db as db_helpers
import app.database.models as db
from app.database.db import (
    get_active_sink_names,
    get_button_actions_for_sink,
    get_fader_mapping,
    get_system_status,
    load_session_state,
    save_session_state,
)
from app.database.models import (
    Config,
    HardwareOutput,
    MidiMapping,
    Session,
    SessionConnection,
    SessionMute,
    SessionVolume,
    VirtualSink,
    add_hardware_output,
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


class TestDatabase(unittest.TestCase):
    """Test cases for database layer."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database file
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_midi_deck.db")

        # Initialize test database
        init_database(self.db_path)

    def tearDown(self):
        """Clean up after tests."""
        # Remove test database
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_database_initialization(self):
        """Test database initialization."""
        # Verify database file exists
        self.assertTrue(os.path.exists(self.db_path))

        # Verify default data exists
        with get_db_session() as session:
            # Check default config entries
            config_count = session.query(Config).count()
            self.assertGreater(
                config_count, 0, "Database should have default config entries"
            )

            # Check default hardware outputs
            output_count = session.query(HardwareOutput).count()
            self.assertGreater(
                output_count, 0, "Database should have default hardware outputs"
            )

            # Check default virtual sinks
            sink_count = session.query(VirtualSink).count()
            self.assertEqual(
                sink_count, 4, "Database should have 4 default virtual sinks"
            )

            # Check default MIDI mappings
            mapping_count = session.query(MidiMapping).count()
            self.assertEqual(
                mapping_count, 12, "Database should have 12 default MIDI mappings"
            )

            # Check default session
            session_count = session.query(Session).count()
            self.assertGreater(
                session_count, 0, "Database should have at least one default session"
            )

    def test_config_crud(self):
        """Test configuration CRUD operations."""
        # Create
        new_key = "test_key"
        new_value = "test_value"
        db.set_config_value(new_key, new_value, description="Test configuration")

        # Read
        retrieved_value = db.get_config_value(new_key)
        self.assertEqual(
            retrieved_value, new_value, "Retrieved value should match stored value"
        )

        # Update
        updated_value = "updated_value"
        db.set_config_value(new_key, updated_value)
        retrieved_value = db.get_config_value(new_key)
        self.assertEqual(
            retrieved_value, updated_value, "Retrieved value should be updated"
        )

        # Test default value
        non_existent = db.get_config_value("non_existent_key", default="default_value")
        self.assertEqual(
            non_existent, "default_value", "Should return default for non-existent key"
        )

        # Test integer value (stored as string in database)
        db.set_config_value("int_key", 42)
        int_value = db.get_config_value("int_key")
        self.assertEqual(int(int_value), 42, "Should store and retrieve integer")

    def test_hardware_outputs_crud(self):
        """Test hardware outputs CRUD operations."""
        # Create
        result = add_hardware_output(
            name="TestOutput",
            device_name="test_device_name",
            description="Test hardware output",
        )
        self.assertTrue(result, "Should create new hardware output")

        # Read - fetch the created output
        new_output = db.get_hardware_output_by_name("TestOutput")
        self.assertIsNotNone(new_output, "Should find created output")
        self.assertEqual(new_output.name, "TestOutput")

        # Read all
        outputs = db.get_all_hardware_outputs()
        self.assertGreater(len(outputs), 0, "Should retrieve hardware outputs")

        output_by_name = db.get_hardware_output_by_name("TestOutput")
        self.assertIsNotNone(output_by_name, "Should find output by name")
        self.assertEqual(output_by_name.device_name, "test_device_name")

        # Update
        db.update_hardware_output(new_output.id, description="Updated description")
        updated_output = db.get_hardware_output_by_id(new_output.id)
        self.assertEqual(updated_output.description, "Updated description")

        # Delete
        db.delete_hardware_output(new_output.id)
        deleted_output = db.get_hardware_output_by_id(new_output.id)
        self.assertIsNone(deleted_output, "Should delete hardware output")

    def test_virtual_sinks_crud(self):
        """Test virtual sinks CRUD operations."""
        # Read default sinks
        sinks = db.get_all_virtual_sinks()
        self.assertEqual(len(sinks), 4, "Should have 4 default sinks")

        # Get sink by channel
        sink_ch1 = db.get_virtual_sink_by_channel(1)
        self.assertIsNotNone(sink_ch1, "Should find sink by channel")
        self.assertEqual(sink_ch1.name, "MainSink")

        # Get sink by name
        sink_by_name = db.get_virtual_sink_by_name("WebSink")
        self.assertIsNotNone(sink_by_name, "Should find sink by name")
        self.assertEqual(sink_by_name.channel_number, 2)

        # Create new sink
        new_sink = db.create_virtual_sink(
            channel_number=5, name="TestSink", description="Test virtual sink"
        )
        self.assertIsNotNone(new_sink, "Should create new virtual sink")

        # Update
        db.update_virtual_sink(new_sink.id, description="Updated sink description")
        updated_sink = db.get_virtual_sink_by_id(new_sink.id)
        self.assertEqual(updated_sink.description, "Updated sink description")

        # Delete
        db.delete_virtual_sink(new_sink.id)
        deleted_sink = db.get_virtual_sink_by_id(new_sink.id)
        self.assertIsNone(deleted_sink, "Should delete virtual sink")

    def test_midi_mappings(self):
        """Test MIDI mappings operations."""
        # Get all mappings
        mappings = db.get_all_midi_mappings()
        self.assertEqual(len(mappings), 12, "Should have 12 default MIDI mappings")

        # Get mapping by MIDI note
        mapping = db.get_midi_mapping(36)
        self.assertIsNotNone(mapping, "Should find mapping by note")
        self.assertEqual(mapping["action"], "speaker")
        self.assertIn("sink_id", mapping)
        self.assertIn("midi_note", mapping)

        # Test updating a mapping - get all mappings and pick the first one
        all_mappings_objects = get_all_midi_mappings()  # This returns the list
        if all_mappings_objects:
            first_mapping = all_mappings_objects[0]
            # Use sink_id to find the actual object
            with get_db_session() as session:
                mapping_obj = (
                    session.query(MidiMapping)
                    .filter_by(midi_note=first_mapping["midi_note"])
                    .first()
                )
                if mapping_obj:
                    original_action = mapping_obj.action
                    # Update
                    db.update_midi_mapping(mapping_obj.id, action="updated_action")
                    updated = db.get_midi_mapping_by_id(mapping_obj.id)
                    self.assertEqual(updated.action, "updated_action")
                    # Restore
                    db.update_midi_mapping(mapping_obj.id, action=original_action)

    def test_session_crud(self):
        """Test session CRUD operations."""
        # Get default session
        current_session = db.get_current_session()
        self.assertIsNotNone(current_session, "Should have a current session")

        # Create new session
        new_session_id = db.create_session(
            name="TestSession", description="Test session for unit testing"
        )
        self.assertIsNotNone(new_session_id, "Should create new session")

        # Get the created session
        new_session = db.get_session_by_id(new_session_id)
        self.assertIsNotNone(new_session, "Should find created session")
        self.assertEqual(new_session.name, "TestSession")
        self.assertFalse(
            new_session.is_current, "New session should not be current by default"
        )

        # Get all sessions
        sessions = db.get_all_sessions()
        self.assertGreater(len(sessions), 1, "Should have multiple sessions")

        # Get session by ID
        session_by_id = db.get_session_by_id(new_session_id)
        self.assertIsNotNone(session_by_id, "Should find session by ID")
        self.assertEqual(session_by_id.name, "TestSession")

        # Set as current session
        db.set_current_session(new_session_id)
        updated_session = db.get_current_session()
        self.assertEqual(
            updated_session.id, new_session_id, "Should update current session"
        )

        # Update session
        db.update_session(new_session_id, description="Updated description")
        updated_session = db.get_session_by_id(new_session_id)
        self.assertEqual(updated_session.description, "Updated description")

        # Delete session
        db.delete_session(new_session_id)
        deleted_session = db.get_session_by_id(new_session_id)
        self.assertIsNone(deleted_session, "Should delete session")

    def test_session_state_persistence(self):
        """Test session state save and load operations."""
        # Create a test session
        session_id = db.create_session(
            name="StateTestSession", description="Session for state testing"
        )

        # Create test state data
        volumes = {
            "MainSink": 0.75,
            "WebSink": 0.50,
        }
        mutes = {
            "MainSink": False,
            "WebSink": True,
        }
        connections = {
            "MainSink": ["SpeakerOut"],
            "WebSink": [],
        }

        # Save state
        save_session_state(session_id, volumes, connections, mutes)

        # Load state
        loaded_state = load_session_state(session_id)

        # Verify volumes
        self.assertIn("MainSink", loaded_state["volumes"])
        self.assertEqual(loaded_state["volumes"]["MainSink"], 0.75)
        self.assertEqual(loaded_state["volumes"]["WebSink"], 0.50)

        # Verify mutes
        self.assertIn("MainSink", loaded_state["mutes"])
        self.assertEqual(loaded_state["mutes"]["MainSink"], False)
        self.assertEqual(loaded_state["mutes"]["WebSink"], True)

        # Verify connections
        self.assertIn("MainSink", loaded_state["connections"])
        self.assertIn("SpeakerOut", loaded_state["connections"]["MainSink"])
        # WebSink has no connections, so it might not be in the dict or be empty
        if "WebSink" in loaded_state["connections"]:
            self.assertEqual(len(loaded_state["connections"]["WebSink"]), 0)

        # Clean up
        db.delete_session(session_id)

    def test_foreign_key_constraints(self):
        """Test foreign key constraints."""
        # Get a virtual sink
        sink = db.get_virtual_sink_by_name("MainSink")

        # Try to delete sink that has MIDI mappings (should handle gracefully)
        # Note: Depends on database CASCADE configuration
        with get_db_session() as session:
            mappings_before = (
                session.query(MidiMapping).filter_by(sink_id=sink.id).count()
            )
            self.assertGreater(mappings_before, 0, "Sink should have MIDI mappings")

        # Delete sink (should cascade to MIDI mappings)
        db.delete_virtual_sink(sink.id)

        with get_db_session() as session:
            mappings_after = session.query(MidiMapping).filter_by(sink_id=sink.id).count()
            self.assertEqual(
                mappings_after, 0, "MIDI mappings should be deleted with sink"
            )

            # Verify sink is deleted
            deleted_sink = session.query(VirtualSink).filter_by(id=sink.id).first()
            self.assertIsNone(deleted_sink, "Sink should be deleted")

    def test_session_state_update(self):
        """Test updating session state."""
        session = db.get_current_session()

        # Initial state
        volumes1 = {"MainSink": 0.5}
        mutes1 = {"MainSink": False}
        connections1 = {"MainSink": ["SpeakerOut"]}
        save_session_state(session.id, volumes1, connections1, mutes1)

        # Updated state
        volumes2 = {"MainSink": 0.8}
        mutes2 = {"MainSink": True}
        connections2 = {"MainSink": []}
        save_session_state(session.id, volumes2, connections2, mutes2)

        # Load and verify updated state
        loaded_state = load_session_state(session.id)
        self.assertEqual(loaded_state["volumes"]["MainSink"], 0.8)
        self.assertEqual(loaded_state["mutes"]["MainSink"], True)
        # Empty connections might not be in the dict
        if "MainSink" in loaded_state["connections"]:
            self.assertEqual(len(loaded_state["connections"]["MainSink"]), 0)
        else:
            # If not in dict, that means no connections (empty)
            self.assertTrue(True)

    def test_get_system_status(self):
        """Test get system status function."""
        status = get_system_status()

        # Verify structure
        self.assertIn("database_initialized", status)
        self.assertIn("config_entries", status)
        self.assertIn("hardware_outputs", status)
        self.assertIn("virtual_sinks", status)
        self.assertIn("total_sessions", status)
        self.assertIn("current_session", status)

        # Verify values
        self.assertTrue(status["database_initialized"])
        self.assertEqual(status["virtual_sinks"], 4)
        self.assertGreater(status["hardware_outputs"], 0)
        self.assertIsNotNone(status["current_session"])


class TestDatabaseHelpers(unittest.TestCase):
    """Test cases for database helper functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_midi_deck.db")
        init_database(self.db_path)

    def tearDown(self):
        """Clean up after tests."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_fader_mapping(self):
        """Test fader CC# to sink channel mapping."""
        # CC 0 -> Channel 1
        sink = db.get_virtual_sink_by_channel(1)
        self.assertEqual(sink.name, "MainSink")

        # CC 1 -> Channel 2
        sink = db.get_virtual_sink_by_channel(2)
        self.assertEqual(sink.name, "WebSink")

        # CC 2 -> Channel 3
        sink = db.get_virtual_sink_by_channel(3)
        self.assertEqual(sink.name, "MusicSink")

        # CC 3 -> Channel 4
        sink = db.get_virtual_sink_by_channel(4)
        self.assertEqual(sink.name, "DiscordSink")

    def test_active_filters(self):
        """Test is_active filtering."""
        # Create inactive sink
        inactive_sink = db.create_virtual_sink(
            channel_number=99, name="InactiveSink", description="Inactive test sink"
        )

        # Set as inactive
        db.update_virtual_sink(inactive_sink.id, is_active=False)

        # Get only active sinks
        active_sinks = db.get_all_virtual_sinks(active_only=True)
        active_names = [s.name for s in active_sinks]
        self.assertNotIn("InactiveSink", active_names)

        # Get all sinks
        all_sinks = db.get_all_virtual_sinks(active_only=False)
        all_names = [s.name for s in all_sinks]
        self.assertIn("InactiveSink", all_names)

        # Clean up
        db.delete_virtual_sink(inactive_sink.id)


if __name__ == "__main__":
    unittest.main()
