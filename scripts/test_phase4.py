#!/usr/bin/env python3
"""
Phase 4 Testing Script - Session Management

Tests the complete SessionManager implementation including:
- Session creation and management
- State capture (volumes, connections, mutes)
- State restoration
- Session switching
- Auto-save functionality
- Database persistence

Run this script from the midi-deck root directory:
    cd /home/rambo/code/midi-deck
    python scripts/test_phase4.py
"""

import logging
import os
import sys
import time

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app.core.audio_manager import AudioManager  # noqa: E402
from app.core.loopback_manager import LoopbackManager  # noqa: E402
from app.core.session_manager import SessionManager  # noqa: E402
from app.database import init_database  # noqa: E402
from app.database.db import get_active_output_names, get_active_sink_names  # noqa: E402
from app.database.models import get_all_sessions, get_current_session  # noqa: E402

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("test_phase4")


def print_separator(title=""):
    """Print a visual separator."""
    if title:
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}")
    else:
        print(f"{'='*70}\n")


def print_test_header(test_name):
    """Print test header."""
    print(f"\n--- Test: {test_name} ---")


def print_success(message):
    """Print success message."""
    print(f"  [OK] {message}")


def print_error(message):
    """Print error message."""
    print(f"  [ERROR] {message}")


def print_info(message):
    """Print info message."""
    print(f"  [INFO] {message}")


def test_database_initialization():
    """Test 1: Database initialization."""
    print_test_header("Database Initialization")

    try:
        # Use test database
        db_path = "data/midi_deck_test.db"

        # Remove old test database if it exists
        if os.path.exists(db_path):
            os.remove(db_path)
            print_info(f"Removed old test database: {db_path}")

        # Initialize database
        if init_database(db_path):
            print_success("Database initialized")
        else:
            print_error("Database initialization failed")
            return False

        # Check if default session exists
        current = get_current_session()
        if current:
            print_success(f"Default session exists: '{current.name}' (ID: {current.id})")
        else:
            print_error("No default session found")
            return False

        return True

    except Exception as e:
        print_error(f"Exception during database initialization: {e}")
        return False


def test_audio_manager_initialization():
    """Test 2: AudioManager initialization."""
    print_test_header("AudioManager Initialization")

    try:
        audio_manager = AudioManager()
        print_success("AudioManager initialized")

        # Initialize sinks from database
        if audio_manager.initialize_sinks_from_database():
            print_success("Virtual sinks initialized from database")
        else:
            print_error("Failed to initialize some virtual sinks")

        # Verify sinks exist
        sink_names = get_active_sink_names()
        print_info(f"Active sinks: {', '.join(sink_names)}")

        for sink_name in sink_names:
            if audio_manager.sink_exists(sink_name):
                print_success(f"  Sink verified: {sink_name}")
            else:
                print_error(f"  Sink not found: {sink_name}")

        return audio_manager

    except Exception as e:
        print_error(f"Exception during AudioManager initialization: {e}")
        return None


def test_loopback_manager_initialization(audio_manager):
    """Test 3: LoopbackManager initialization."""
    print_test_header("LoopbackManager Initialization")

    try:
        loopback_manager = LoopbackManager(audio_manager.pulse)
        print_success("LoopbackManager initialized")

        return loopback_manager

    except Exception as e:
        print_error(f"Exception during LoopbackManager initialization: {e}")
        return None


def test_session_manager_initialization(audio_manager, loopback_manager):
    """Test 4: SessionManager initialization."""
    print_test_header("SessionManager Initialization")

    try:
        session_manager = SessionManager(audio_manager, loopback_manager)
        print_success("SessionManager initialized")

        # Check auto-save status
        if session_manager.is_auto_save_enabled():
            print_info("Auto-save is enabled (default)")
        else:
            print_info("Auto-save is disabled")

        return session_manager

    except Exception as e:
        print_error(f"Exception during SessionManager initialization: {e}")
        return None


def test_state_capture(session_manager, audio_manager, loopback_manager):
    """Test 5: State capture."""
    print_test_header("State Capture")

    try:
        # Set some test state
        sink_names = get_active_sink_names()
        output_names = get_active_output_names()

        print_info("Setting test state...")

        # Set volumes
        for i, sink_name in enumerate(sink_names):
            volume = 0.3 + (i * 0.1)  # 0.3, 0.4, 0.5, 0.6
            audio_manager.set_volume(sink_name, volume)
            print_info(f"  Set {sink_name} volume to {volume:.1%}")

        # Set some mutes
        if len(sink_names) >= 2:
            audio_manager.set_mute(sink_names[0], True)
            audio_manager.set_mute(sink_names[1], False)
            print_info(f"  Muted {sink_names[0]}")
            print_info(f"  Unmuted {sink_names[1]}")

        # Create some connections
        if len(sink_names) >= 1 and len(output_names) >= 1:
            loopback_manager.connect(sink_names[0], output_names[0])
            print_info(f"  Connected {sink_names[0]} -> {output_names[0]}")

        # Capture state
        state = session_manager._capture_state()

        print_success("State captured successfully")
        print_info(f"  Volumes: {len(state['volumes'])} sinks")
        print_info(f"  Mutes: {len(state['mutes'])} sinks")
        print_info(
            f"  Connections: {sum(len(c) for c in state['connections'].values())} total"
        )

        return state

    except Exception as e:
        print_error(f"Exception during state capture: {e}")
        return None


def test_session_save(session_manager):
    """Test 6: Session save."""
    print_test_header("Session Save")

    try:
        # Save to current session
        current = get_current_session()
        if not current:
            print_error("No current session found")
            return False

        print_info(f"Saving to current session: '{current.name}' (ID: {current.id})")

        if session_manager.save_current_session():
            print_success("Session saved successfully")
            return True
        else:
            print_error("Session save failed")
            return False

    except Exception as e:
        print_error(f"Exception during session save: {e}")
        return False


def test_state_modification(audio_manager, loopback_manager):
    """Test 7: Modify state (to test restoration)."""
    print_test_header("State Modification")

    try:
        sink_names = get_active_sink_names()
        # output_names = get_active_output_names()

        print_info("Modifying state to different values...")

        # Change volumes
        for sink_name in sink_names:
            audio_manager.set_volume(sink_name, 0.8)
            print_info(f"  Changed {sink_name} volume to 80%")

        # Change mutes
        for sink_name in sink_names:
            audio_manager.set_mute(sink_name, False)
            print_info(f"  Unmuted {sink_name}")

        # Disconnect all
        for sink_name in sink_names:
            count = loopback_manager.disconnect_all(sink_name)
            if count > 0:
                print_info(f"  Disconnected {count} connection(s) from {sink_name}")

        print_success("State modified")
        return True

    except Exception as e:
        print_error(f"Exception during state modification: {e}")
        return False


def test_session_restore(session_manager, audio_manager, original_state):
    """Test 8: Session restore."""
    print_test_header("Session Restore")

    try:
        # Restore from current session
        current = get_current_session()
        if not current:
            print_error("No current session found")
            return False

        print_info(f"Restoring from current session: '{current.name}' (ID: {current.id})")

        if session_manager.load_current_session():
            print_success("Session restored successfully")

            # Verify restoration
            print_info("Verifying restored state...")
            sink_names = get_active_sink_names()

            # Check volumes
            all_volumes_match = True
            for sink_name in sink_names:
                expected_volume = original_state["volumes"].get(sink_name)
                actual_volume = audio_manager.get_volume(sink_name)

                if expected_volume is not None and actual_volume is not None:
                    # Allow small tolerance for floating point comparison
                    if abs(expected_volume - actual_volume) < 0.01:
                        print_success(
                            f"  Volume restored for {sink_name}: {actual_volume:.1%}"
                        )
                    else:
                        print_error(
                            f"  Volume mismatch for {sink_name}: "
                            f"expected {expected_volume:.1%}, got {actual_volume:.1%}"
                        )
                        all_volumes_match = False

            # Check mutes
            all_mutes_match = True
            for sink_name in sink_names:
                expected_mute = original_state["mutes"].get(sink_name)
                actual_mute = audio_manager.is_muted(sink_name)

                if expected_mute is not None and actual_mute is not None:
                    if expected_mute == actual_mute:
                        print_success(
                            f"  Mute state restored for {sink_name}: {actual_mute}"
                        )
                    else:
                        print_error(
                            f"  Mute state mismatch for {sink_name}: "
                            f"expected {expected_mute}, got {actual_mute}"
                        )
                        all_mutes_match = False

            return all_volumes_match and all_mutes_match

        else:
            print_error("Session restore failed")
            return False

    except Exception as e:
        print_error(f"Exception during session restore: {e}")
        return False


def test_session_creation(session_manager):
    """Test 9: Create new session."""
    print_test_header("Session Creation")

    try:
        # Create a new session
        session_id = session_manager.create_session(
            name="Test Session",
            description="Created during Phase 4 testing",
            set_as_current=False,
        )

        if session_id:
            print_success(f"New session created: ID {session_id}")

            # List all sessions
            sessions = session_manager.list_sessions()
            print_info(f"Total sessions: {len(sessions)}")
            for session in sessions:
                current_marker = " [CURRENT]" if session["is_current"] else ""
                print_info(f"  - {session['name']} (ID: {session['id']}){current_marker}")

            return session_id
        else:
            print_error("Session creation failed")
            return None

    except Exception as e:
        print_error(f"Exception during session creation: {e}")
        return None


def test_session_switching(session_manager, new_session_id, audio_manager):
    """Test 10: Switch between sessions."""
    print_test_header("Session Switching")

    try:
        # Get original session
        original_session = get_current_session()
        print_info(
            f"Original session: '{original_session.name}' (ID: {original_session.id})"
        )

        # Set different state for new session
        print_info("Setting different state for new session...")
        sink_names = get_active_sink_names()
        for sink_name in sink_names:
            audio_manager.set_volume(sink_name, 0.9)

        # Switch to new session
        print_info(f"Switching to session ID {new_session_id}...")
        if session_manager.set_current_session(new_session_id):
            print_success("Switched to new session")

            # Verify it's current
            current = get_current_session()
            if current and current.id == new_session_id:
                print_success(
                    f"Current session is now: '{current.name}' (ID: {current.id})"
                )
            else:
                print_error("Current session was not updated correctly")
                return False

            # Switch back to original
            print_info(f"Switching back to session ID {original_session.id}...")
            if session_manager.set_current_session(original_session.id):
                print_success("Switched back to original session")

                # Verify state was restored
                volume = audio_manager.get_volume(sink_names[0])
                if volume and volume < 0.8:  # Should be back to original (~0.3-0.6 range)
                    print_success(f"State was restored (volume: {volume:.1%})")
                else:
                    print_error(
                        f"State may not have been restored (volume: {volume:.1%})"
                    )

                return True
            else:
                print_error("Failed to switch back")
                return False
        else:
            print_error("Session switch failed")
            return False

    except Exception as e:
        print_error(f"Exception during session switching: {e}")
        return False


def test_session_deletion(session_manager, session_id):
    """Test 11: Delete session."""
    print_test_header("Session Deletion")

    try:
        # Try to delete current session (should fail)
        current = get_current_session()
        print_info(f"Attempting to delete current session {current.id} (should fail)...")
        if not session_manager.delete_session(current.id):
            print_success("Correctly prevented deletion of current session")
        else:
            print_error("Should not allow deleting current session")
            return False

        # Delete non-current session
        print_info(f"Deleting non-current session {session_id}...")
        if session_manager.delete_session(session_id):
            print_success(f"Session {session_id} deleted successfully")

            # Verify it's gone
            sessions = session_manager.list_sessions()
            session_ids = [s["id"] for s in sessions]
            if session_id not in session_ids:
                print_success("Session no longer in database")
                return True
            else:
                print_error("Session still exists after deletion")
                return False
        else:
            print_error("Session deletion failed")
            return False

    except Exception as e:
        print_error(f"Exception during session deletion: {e}")
        return False


def cleanup(audio_manager):
    """Cleanup: Remove test sinks."""
    print_test_header("Cleanup")

    try:
        print_info("Cleaning up virtual sinks...")
        if audio_manager.cleanup_virtual_sinks():
            print_success("Virtual sinks cleaned up")
        else:
            print_error("Some virtual sinks failed to clean up")

        # Remove test database
        db_path = "data/midi_deck_test.db"
        if os.path.exists(db_path):
            os.remove(db_path)
            print_success(f"Removed test database: {db_path}")

    except Exception as e:
        print_error(f"Exception during cleanup: {e}")


def main():
    """Run all Phase 4 tests."""
    print_separator("MIDI Deck - Phase 4 Testing: Session Management")

    print("\nThis script tests the complete SessionManager implementation.")
    print(
        "It will create test sinks and sessions, and verify save/restore functionality."
    )

    # Track test results
    results = {}

    # Test 1: Database initialization
    results["Database Init"] = test_database_initialization()
    if not results["Database Init"]:
        print_error("Database initialization failed, aborting tests")
        return

    # Test 2: AudioManager initialization
    audio_manager = test_audio_manager_initialization()
    results["AudioManager Init"] = audio_manager is not None
    if not audio_manager:
        print_error("AudioManager initialization failed, aborting tests")
        return

    # Test 3: LoopbackManager initialization
    loopback_manager = test_loopback_manager_initialization(audio_manager)
    results["LoopbackManager Init"] = loopback_manager is not None
    if not loopback_manager:
        print_error("LoopbackManager initialization failed, aborting tests")
        cleanup(audio_manager)
        return

    # Test 4: SessionManager initialization
    session_manager = test_session_manager_initialization(audio_manager, loopback_manager)
    results["SessionManager Init"] = session_manager is not None
    if not session_manager:
        print_error("SessionManager initialization failed, aborting tests")
        cleanup(audio_manager)
        return

    # Test 5: State capture
    original_state = test_state_capture(session_manager, audio_manager, loopback_manager)
    results["State Capture"] = original_state is not None

    # Test 6: Session save
    results["Session Save"] = test_session_save(session_manager)

    # Test 7: State modification
    results["State Modification"] = test_state_modification(
        audio_manager, loopback_manager
    )

    # Test 8: Session restore
    results["Session Restore"] = test_session_restore(
        session_manager, audio_manager, original_state
    )

    # Test 9: Session creation
    new_session_id = test_session_creation(session_manager)
    results["Session Creation"] = new_session_id is not None

    # Test 10: Session switching
    if new_session_id:
        results["Session Switching"] = test_session_switching(
            session_manager, new_session_id, audio_manager
        )

        # Test 11: Session deletion
        results["Session Deletion"] = test_session_deletion(
            session_manager, new_session_id
        )

    # Cleanup
    cleanup(audio_manager)

    # Print summary
    print_separator("Test Summary")
    passed = sum(1 for result in results.values() if result)
    total = len(results)

    print(f"\nResults: {passed}/{total} tests passed\n")

    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"  {symbol} {test_name}: {status}")

    print_separator()

    if passed == total:
        print("\n🎉 All Phase 4 tests passed! Session management is working correctly.\n")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed. Please review the errors above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
