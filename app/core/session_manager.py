"""
Session Manager Module

Handles session save/restore functionality for preserving and
restoring audio state across application restarts.
"""

import logging
import threading
import time
from typing import Dict, List, Optional

from app.database.db import (
    get_active_output_names,
    get_active_sink_names,
    load_session_state,
    save_session_state,
)
from app.database.models import create_session
from app.database.models import delete_session as db_delete_session
from app.database.models import get_all_sessions, get_current_session
from app.database.models import set_current_session as db_set_current_session

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages session save/restore functionality.

    Provides methods to capture current audio state (volumes, connections,
    mutes) and restore it later, enabling persistent configuration.

    This manager acts as the coordinator between the database layer and
    the audio managers (AudioManager and LoopbackManager).
    """

    def __init__(self, audio_manager=None, loopback_manager=None):
        """
        Initialize SessionManager with audio managers.

        Args:
            audio_manager: AudioManager instance for volume/mute control
            loopback_manager: LoopbackManager instance for connection control
        """
        self.audio_manager = audio_manager
        self.loopback_manager = loopback_manager

        # Throttled auto-save configuration
        self._auto_save = True  # Auto-save on changes by default
        self._dirty = False  # Track if state has changed since last save
        self._last_save_time = 0.0  # Timestamp of last save
        self._save_interval = 60.0  # Save at most every 60 seconds
        self._stop_saver = False  # Flag to stop background saver
        self._saver_thread = None  # Background saver thread

        logger.info("SessionManager initialized")

    def set_managers(self, audio_manager, loopback_manager):
        """
        Set or update audio managers (useful for deferred initialization).

        Args:
            audio_manager: AudioManager instance
            loopback_manager: LoopbackManager instance
        """
        self.audio_manager = audio_manager
        self.loopback_manager = loopback_manager
        logger.debug("Audio managers set/updated")

    # =========================================================================
    # Session CRUD Operations
    # =========================================================================

    def create_session(
        self, name: str, description: str = "", set_as_current: bool = False
    ) -> Optional[int]:
        """
        Create new session.

        Args:
            name: Session name
            description: Optional session description
            set_as_current: If True, set as current session

        Returns:
            Session ID if successful, None otherwise
        """
        try:
            session_id = create_session(
                name=name, description=description, set_as_current=set_as_current
            )

            if session_id:
                logger.info(
                    f"Created session '{name}' (ID: {session_id}, current: {set_as_current})"
                )

                # If set as current, capture and save current state
                if set_as_current and self.audio_manager and self.loopback_manager:
                    self.save_session(session_id)

            return session_id

        except Exception as e:
            logger.error(f"Error creating session '{name}': {e}", exc_info=True)
            return None

    def delete_session(self, session_id: int) -> bool:
        """
        Delete a session.

        Args:
            session_id: ID of session to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Don't allow deleting current session
            current = get_current_session()
            if current and current.id == session_id:
                logger.warning(
                    "Cannot delete current session. Switch to another session first."
                )
                return False

            success = db_delete_session(session_id)
            if success:
                logger.info(f"Deleted session ID {session_id}")
            return success

        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
            return False

    def list_sessions(self) -> List[Dict]:
        """
        Get all sessions.

        Returns:
            List of session dictionaries with metadata
        """
        try:
            sessions = get_all_sessions()
            result = [
                {
                    "id": session.id,
                    "name": session.name,
                    "description": session.description,
                    "is_current": session.is_current,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                }
                for session in sessions
            ]
            logger.debug(f"Retrieved {len(result)} sessions")
            return result

        except Exception as e:
            logger.error(f"Error listing sessions: {e}", exc_info=True)
            return []

    def get_current_session_info(self) -> Optional[Dict]:
        """
        Get information about the current active session.

        Returns:
            Dictionary with session info, or None if no current session
        """
        try:
            current = get_current_session()
            if not current:
                return None

            return {
                "id": current.id,
                "name": current.name,
                "description": current.description,
                "is_current": current.is_current,
                "created_at": current.created_at.isoformat(),
                "updated_at": current.updated_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting current session info: {e}", exc_info=True)
            return None

    def set_current_session(self, session_id: int) -> bool:
        """
        Set active session (and load its state).

        Args:
            session_id: ID of session to set as current

        Returns:
            True if successful, False otherwise
        """
        try:
            # Set in database
            if not db_set_current_session(session_id):
                return False

            # Load the session state
            if self.audio_manager and self.loopback_manager:
                return self.load_session(session_id)

            return True

        except Exception as e:
            logger.error(
                f"Error setting current session {session_id}: {e}", exc_info=True
            )
            return False

    # =========================================================================
    # State Capture
    # =========================================================================

    def _capture_state(self) -> Dict:
        """
        Capture current volumes, connections, mutes from audio system.

        Returns:
            Dictionary containing complete audio state
            Format: {
                'volumes': {sink_name: volume, ...},
                'connections': {sink_name: [output_name, ...], ...},
                'mutes': {sink_name: is_muted, ...}
            }
        """
        if not self.audio_manager or not self.loopback_manager:
            logger.warning("Audio managers not set, cannot capture state")
            return {"volumes": {}, "connections": {}, "mutes": {}}

        state = {"volumes": {}, "connections": {}, "mutes": {}}

        try:
            # Get all active sinks from database
            sink_names = get_active_sink_names()

            # Capture volumes and mutes
            for sink_name in sink_names:
                # Get volume (0.0-1.0)
                volume = self.audio_manager.get_volume(sink_name)
                if volume is not None:
                    state["volumes"][sink_name] = volume
                else:
                    logger.warning(
                        f"Could not get volume for '{sink_name}', using default 0.5"
                    )
                    state["volumes"][sink_name] = 0.5

                # Get mute state
                is_muted = self.audio_manager.is_muted(sink_name)
                if is_muted is not None:
                    state["mutes"][sink_name] = is_muted
                else:
                    logger.warning(
                        f"Could not get mute state for '{sink_name}', using default False"
                    )
                    state["mutes"][sink_name] = False

            # Capture connections
            # Build device_name -> output_name mapping
            from app.database.models import get_all_hardware_outputs

            device_to_output = {}
            for output in get_all_hardware_outputs():
                device_to_output[output.device_name] = output.name

            for sink_name in sink_names:
                # get_connections returns device names (e.g., alsa_output.xxx)
                device_names = self.loopback_manager.get_connections(sink_name)

                # Convert device names to output names for database storage
                output_names = []
                for device_name in device_names:
                    if device_name in device_to_output:
                        output_names.append(device_to_output[device_name])
                    else:
                        logger.warning(
                            f"Unknown device '{device_name}' connected to '{sink_name}', skipping"
                        )

                state["connections"][sink_name] = output_names

            logger.debug(
                f"Captured state: {len(state['volumes'])} volumes, "
                f"{sum(len(c) for c in state['connections'].values())} connections, "
                f"{len(state['mutes'])} mutes"
            )

        except Exception as e:
            logger.error(f"Error capturing state: {e}", exc_info=True)

        return state

    # =========================================================================
    # State Restoration
    # =========================================================================

    def _restore_state(self, state: Dict) -> bool:
        """
        Apply saved state to audio system.

        Args:
            state: Dictionary containing audio state to restore
                   Format same as _capture_state() output

        Returns:
            True if restoration was successful, False otherwise
        """
        if not self.audio_manager or not self.loopback_manager:
            logger.warning("Audio managers not set, cannot restore state")
            return False

        try:
            volumes = state.get("volumes", {})
            connections = state.get("connections", {})
            mutes = state.get("mutes", {})

            success = True

            # Restore volumes
            logger.debug(f"Restoring volumes for {len(volumes)} sinks...")
            for sink_name, volume in volumes.items():
                if not self.audio_manager.set_volume(sink_name, volume):
                    logger.warning(f"Failed to restore volume for '{sink_name}'")
                    success = False

            # Restore mute states
            logger.debug(f"Restoring mute states for {len(mutes)} sinks...")
            for sink_name, is_muted in mutes.items():
                if not self.audio_manager.set_mute(sink_name, is_muted):
                    logger.warning(f"Failed to restore mute state for '{sink_name}'")
                    success = False

            # Restore connections
            logger.debug(f"Restoring connections for {len(connections)} sinks...")

            # Build output_name -> device_name mapping
            from app.database.models import get_all_hardware_outputs

            output_to_device = {}
            for output in get_all_hardware_outputs():
                output_to_device[output.name] = output.device_name

            # First, disconnect all existing connections to start fresh
            for sink_name in connections.keys():
                self.loopback_manager.disconnect_all(sink_name)

            # Then reconnect based on saved state
            # connections contains output names (e.g., SpeakerOut)
            # but connect() needs device names (e.g., alsa_output.xxx)
            for sink_name, output_names in connections.items():
                for output_name in output_names:
                    if output_name in output_to_device:
                        device_name = output_to_device[output_name]
                        if not self.loopback_manager.connect(sink_name, device_name):
                            logger.warning(
                                f"Failed to restore connection: {sink_name} -> {output_name} ({device_name})"
                            )
                            success = False
                    else:
                        logger.warning(
                            f"Unknown output '{output_name}' for sink '{sink_name}', skipping"
                        )
                        success = False

            if success:
                logger.info("State restoration complete")
            else:
                logger.warning("State restoration completed with some errors")

            return success

        except Exception as e:
            logger.error(f"Error restoring state: {e}", exc_info=True)
            return False

    # =========================================================================
    # Save/Load Operations
    # =========================================================================

    def save_session(self, session_id: int) -> bool:
        """
        Save current audio state to a specific session.

        Args:
            session_id: ID of session to save to

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Saving current state to session {session_id}...")

            # Capture current state
            state = self._capture_state()

            # Save to database
            success = save_session_state(
                session_id=session_id,
                volumes=state["volumes"],
                connections=state["connections"],
                mutes=state["mutes"],
            )

            if success:
                logger.info(f"Successfully saved state to session {session_id}")
            else:
                logger.error(f"Failed to save state to session {session_id}")

            return success

        except Exception as e:
            logger.error(f"Error saving session {session_id}: {e}", exc_info=True)
            return False

    def load_session(self, session_id: int) -> bool:
        """
        Restore audio state from a specific session.

        Args:
            session_id: ID of session to load

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Loading state from session {session_id}...")

            # Load state from database
            state = load_session_state(session_id)

            if not state:
                logger.error(f"Failed to load state from session {session_id}")
                return False

            # Restore state to audio system
            success = self._restore_state(state)

            if success:
                logger.info(
                    f"Successfully loaded state from session {session_id} ('{state['session_name']}')"
                )
            else:
                logger.warning(f"Loaded session {session_id} with some errors")

            return success

        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}", exc_info=True)
            return False

    def save_current_session(self) -> bool:
        """
        Save current audio state to the currently active session.

        Returns:
            True if successful, False otherwise
        """
        try:
            current = get_current_session()
            if not current:
                logger.warning("No current session found, cannot save")
                return False

            return self.save_session(current.id)

        except Exception as e:
            logger.error(f"Error saving current session: {e}", exc_info=True)
            return False

    def load_current_session(self) -> bool:
        """
        Load the current active session (or create default if none exists).

        Returns:
            True if successful, False otherwise
        """
        try:
            current = get_current_session()

            if not current:
                logger.warning("No current session found, creating default session")

                # Create a default session
                session_id = self.create_session(
                    name="Default",
                    description="Default session created on startup",
                    set_as_current=True,
                )

                if not session_id:
                    logger.error("Failed to create default session")
                    return False

                logger.info(f"Created and loaded default session (ID: {session_id})")
                return True

            # Load the current session
            logger.info(f"Loading current session: '{current.name}' (ID: {current.id})")
            success = self.load_session(current.id)

            # Validate loaded state
            if success:
                state = load_session_state(current.id)
                if state:
                    connections = state.get("connections", {})
                    total_connections = sum(len(conns) for conns in connections.values())
                    if total_connections == 0:
                        logger.warning(
                            f"Session '{current.name}' loaded but has no audio connections. "
                            "You may need to configure connections via web UI."
                        )
                    else:
                        logger.info(f"Loaded {total_connections} audio connections")

            return success

        except Exception as e:
            logger.error(f"Error loading current session: {e}", exc_info=True)
            return False

    # =========================================================================
    # Throttled Auto-Save Functionality
    # =========================================================================

    def mark_dirty(self):
        """
        Mark session state as dirty (changed since last save).

        This should be called after state changes (volume, mute, connection changes).
        The actual save will happen in the background at most once per save_interval.
        """
        if self._auto_save:
            self._dirty = True
            logger.debug("Session marked as dirty")

    def _background_saver(self):
        """
        Background thread that periodically saves session if dirty.

        Wakes up every few seconds to check if save is needed.
        """
        logger.info(
            f"Background session saver started (interval: {self._save_interval}s)"
        )

        while not self._stop_saver:
            # Sleep in small increments to allow quick shutdown
            for _ in range(10):  # Check stop flag every 1 second
                if self._stop_saver:
                    break
                time.sleep(1.0)

            if self._stop_saver:
                break

            # Check if save is needed
            if self._dirty and self._auto_save:
                current_time = time.time()
                time_since_save = current_time - self._last_save_time

                if time_since_save >= self._save_interval:
                    logger.debug("Auto-save triggered (throttled)")
                    try:
                        if self.save_current_session():
                            self._dirty = False
                            self._last_save_time = current_time
                            logger.info("Auto-save completed successfully")
                        else:
                            logger.warning("Auto-save failed")
                    except Exception as e:
                        logger.error(f"Error during auto-save: {e}", exc_info=True)

        logger.info("Background session saver stopped")

    def start_auto_save(self):
        """Start background auto-save thread."""
        if self._saver_thread is None or not self._saver_thread.is_alive():
            self._stop_saver = False
            self._saver_thread = threading.Thread(
                target=self._background_saver, daemon=True, name="SessionSaver"
            )
            self._saver_thread.start()
            logger.info("Auto-save thread started")
        else:
            logger.debug("Auto-save thread already running")

    def stop_auto_save(self):
        """Stop background auto-save thread."""
        if self._saver_thread and self._saver_thread.is_alive():
            logger.info("Stopping auto-save thread...")
            self._stop_saver = True
            self._saver_thread.join(timeout=5.0)
            if self._saver_thread.is_alive():
                logger.warning("Auto-save thread did not stop cleanly")
            else:
                logger.info("Auto-save thread stopped")

    def enable_auto_save(self):
        """Enable auto-save functionality."""
        self._auto_save = True
        logger.info("Auto-save enabled")

    def disable_auto_save(self):
        """Disable auto-save functionality."""
        self._auto_save = False
        logger.info("Auto-save disabled")

    def is_auto_save_enabled(self) -> bool:
        """
        Check if auto-save is enabled.

        Returns:
            True if auto-save is enabled
        """
        return self._auto_save
