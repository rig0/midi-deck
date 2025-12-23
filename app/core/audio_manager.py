"""
Audio Manager Module

Handles all PulseAudio/PipeWire interactions including:
- Sink discovery and management
- Volume control
- Mute control
- Hardware device enumeration
- Virtual sink creation/removal

Phase 3 Implementation: Complete sink management with Python-based
PulseAudio/PipeWire integration replacing bash scripts.
"""

import logging
import subprocess
from typing import Dict, List, Optional

import pulsectl

logger = logging.getLogger(__name__)


class AudioManager:
    """
    Manages audio device interactions via PulseAudio/PipeWire.

    Provides high-level interface for audio operations including
    volume control, mute management, and device discovery.

    This implementation uses both pulsectl (for queries and control)
    and pactl commands (for module loading/unloading) to manage
    PulseAudio/PipeWire audio routing.
    """

    def __init__(self):
        """Initialize AudioManager."""
        try:
            self.pulse = pulsectl.Pulse("midi-deck-audio-manager")
            self._module_cache = {}  # Track loaded module IDs by sink name
            logger.info("AudioManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PulseAudio connection: {e}")
            raise

    def _get_pulse(self):
        """
        Create a new Pulse connection for thread-safe operations.

        Returns:
            New pulsectl.Pulse connection
        """
        return pulsectl.Pulse("midi-deck-audio-manager")

    # =========================================================================
    # Hardware Device Discovery
    # =========================================================================

    def list_hardware_sinks(self) -> List[Dict]:
        """
        Get all available hardware sinks for configuration UI.

        Returns hardware (non-null) sinks that can be used as outputs.
        Filters out virtual/null sinks and monitors.

        Returns:
            List of dictionaries containing sink information
            Format: [{'name': str, 'description': str, 'device_name': str}, ...]
        """
        try:
            with self._get_pulse() as pulse:
                sinks = []
                for sink in pulse.sink_list():
                    # Filter out null sinks and monitors
                    driver = getattr(sink, "driver", "")
                    if "null" not in driver.lower() and not sink.name.endswith(
                        ".monitor"
                    ):
                        sinks.append(
                            {
                                "name": sink.name,
                                "description": sink.description,
                                "device_name": sink.name,
                            }
                        )

                logger.debug(f"Found {len(sinks)} hardware sinks")
                return sinks

        except Exception as e:
            logger.error(f"Error listing hardware sinks: {e}")
            return []

    def list_sink_inputs(self) -> List[Dict]:
        """
        Get all sink inputs (audio streams playing to sinks).

        Returns:
            List of dictionaries containing sink input information
        """
        try:
            with self._get_pulse() as pulse:
                inputs = []
                for si in pulse.sink_input_list():
                    inputs.append(
                        {
                            "index": si.index,
                            "name": si.name,
                            "sink": si.sink,
                            "volume": si.volume.value_flat,
                            "mute": si.mute,
                        }
                    )

                logger.debug(f"Found {len(inputs)} sink inputs")
                return inputs

        except Exception as e:
            logger.error(f"Error listing sink inputs: {e}")
            return []

    # =========================================================================
    # Virtual Sink Management (using pactl for module loading)
    # =========================================================================

    def create_virtual_sink(self, name: str, description: str) -> bool:
        """
        Create a null sink using PulseAudio module-null-sink.

        Args:
            name: Sink name (e.g., 'MainSink')
            description: User-friendly description

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if sink already exists
            if self.find_sink_by_name(name):
                logger.info(f"Sink '{name}' already exists, skipping creation")
                return True

            # Use pactl to load the module
            cmd = [
                "pactl",
                "load-module",
                "module-null-sink",
                f"sink_name={name}",
                f'sink_properties=device.description="{description}"',
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Parse module ID from output
            module_id = result.stdout.strip()
            if module_id.isdigit():
                self._module_cache[name] = int(module_id)
                logger.info(f"Created virtual sink '{name}' (module {module_id})")
                return True
            else:
                logger.warning(
                    f"Created sink '{name}' but could not parse module ID: {module_id}"
                )
                return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create sink '{name}': {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error creating sink '{name}': {e}")
            return False

    def remove_virtual_sink(self, name: str) -> bool:
        """
        Remove a virtual sink by unloading its module.

        Args:
            name: Sink name to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            # Try to get module ID from cache
            module_id = self._module_cache.get(name)

            # If not in cache, try to find the sink and get its module
            if module_id is None:
                sink = self.find_sink_by_name(name)
                if sink:
                    module_id = sink.owner_module

            if module_id is None:
                logger.warning(f"Cannot remove sink '{name}': module ID not found")
                return False

            # Unload the module using pactl
            cmd = ["pactl", "unload-module", str(module_id)]

            subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Remove from cache
            if name in self._module_cache:
                del self._module_cache[name]

            logger.info(f"Removed virtual sink '{name}' (module {module_id})")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to remove sink '{name}': {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error removing sink '{name}': {e}")
            return False

    def verify_virtual_sink(self, name: str, description: str) -> bool:
        """
        Verify that a virtual sink exists, create it if missing.

        Args:
            name: Sink name
            description: User-friendly description

        Returns:
            True if sink exists or was created successfully
        """
        if self.find_sink_by_name(name):
            logger.debug(f"Sink '{name}' verified")
            return True

        logger.warning(f"Sink '{name}' missing, attempting to create...")
        return self.create_virtual_sink(name, description)

    # =========================================================================
    # Sink Discovery and Queries
    # =========================================================================

    def find_sink_by_name(self, name: str) -> Optional[pulsectl.PulseSinkInfo]:
        """
        Find sink by exact name.

        Note: This creates a new pulse connection each time for thread safety.
        The returned object is only valid within this connection context.

        Args:
            name: Sink name to search for

        Returns:
            PulseSinkInfo object if found, None otherwise
        """
        try:
            # Note: This is a helper that's not directly called from threads
            # Methods that need thread-safety create their own connections
            with self._get_pulse() as pulse:
                for sink in pulse.sink_list():
                    if sink.name == name:
                        # Return a copy of just the data we need
                        # since the object becomes invalid when context exits
                        return sink
                return None
        except Exception as e:
            logger.error(f"Error finding sink '{name}': {e}")
            return None

    def sink_exists(self, name: str) -> bool:
        """
        Check if a sink exists.

        Args:
            name: Sink name to check

        Returns:
            True if sink exists, False otherwise
        """
        return self.find_sink_by_name(name) is not None

    # =========================================================================
    # Volume Control
    # =========================================================================

    def set_volume(self, sink_name: str, volume: float) -> bool:
        """
        Set volume (0.0-1.0) for a sink.

        Args:
            sink_name: Name of the sink
            volume: Volume level (0.0 = silent, 1.0 = 100%)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Clamp volume to valid range
            volume = max(0.0, min(1.0, volume))

            with self._get_pulse() as pulse:
                sink = None
                for s in pulse.sink_list():
                    if s.name == sink_name:
                        sink = s
                        break

                if not sink:
                    logger.warning(f"Cannot set volume: sink '{sink_name}' not found")
                    return False

                # Set volume using pulsectl
                pulse.volume_set_all_chans(sink, volume)
                logger.debug(f"Set volume for '{sink_name}' to {volume:.2%}")
                return True

        except Exception as e:
            logger.error(f"Error setting volume for '{sink_name}': {e}")
            return False

    def get_volume(self, sink_name: str) -> Optional[float]:
        """
        Get current volume for a sink.

        Args:
            sink_name: Name of the sink

        Returns:
            Volume level (0.0-1.0) or None if not found
        """
        try:
            with self._get_pulse() as pulse:
                for sink in pulse.sink_list():
                    if sink.name == sink_name:
                        # Get average volume across all channels
                        return sink.volume.value_flat

                logger.warning(f"Cannot get volume: sink '{sink_name}' not found")
                return None

        except Exception as e:
            logger.error(f"Error getting volume for '{sink_name}': {e}")
            return None

    # =========================================================================
    # Mute Control
    # =========================================================================

    def toggle_mute(self, sink_name: str) -> Optional[bool]:
        """
        Toggle mute state and return new state.

        Args:
            sink_name: Name of the sink

        Returns:
            True if now muted, False if now unmuted, None if error
        """
        try:
            with self._get_pulse() as pulse:
                sink = None
                for s in pulse.sink_list():
                    if s.name == sink_name:
                        sink = s
                        break

                if not sink:
                    logger.warning(f"Cannot toggle mute: sink '{sink_name}' not found")
                    return None

                # Toggle mute
                new_mute_state = not sink.mute
                pulse.mute(sink, new_mute_state)

                logger.debug(f"Toggled mute for '{sink_name}' to {new_mute_state}")
                return new_mute_state

        except Exception as e:
            logger.error(f"Error toggling mute for '{sink_name}': {e}")
            return None

    def set_mute(self, sink_name: str, muted: bool) -> bool:
        """
        Set mute state explicitly.

        Args:
            sink_name: Name of the sink
            muted: True to mute, False to unmute

        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_pulse() as pulse:
                sink = None
                for s in pulse.sink_list():
                    if s.name == sink_name:
                        sink = s
                        break

                if not sink:
                    logger.warning(f"Cannot set mute: sink '{sink_name}' not found")
                    return False

                pulse.mute(sink, muted)
                logger.debug(f"Set mute for '{sink_name}' to {muted}")
                return True

        except Exception as e:
            logger.error(f"Error setting mute for '{sink_name}': {e}")
            return False

    def is_muted(self, sink_name: str) -> Optional[bool]:
        """
        Get current mute state.

        Args:
            sink_name: Name of the sink

        Returns:
            True if muted, False if unmuted, None if not found
        """
        try:
            with self._get_pulse() as pulse:
                for sink in pulse.sink_list():
                    if sink.name == sink_name:
                        return sink.mute

                logger.warning(f"Cannot get mute state: sink '{sink_name}' not found")
                return None

        except Exception as e:
            logger.error(f"Error getting mute state for '{sink_name}': {e}")
            return None

    # =========================================================================
    # System Configuration
    # =========================================================================

    def set_default_sink(self, sink_name: str) -> bool:
        """
        Set system default output sink.

        Args:
            sink_name: Name of the sink to set as default

        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_pulse() as pulse:
                sink = None
                for s in pulse.sink_list():
                    if s.name == sink_name:
                        sink = s
                        break

                if not sink:
                    logger.warning(f"Cannot set default: sink '{sink_name}' not found")
                    return False

                pulse.sink_default_set(sink)
                logger.info(f"Set default sink to '{sink_name}'")
                return True

        except Exception as e:
            logger.error(f"Error setting default sink to '{sink_name}': {e}")
            return False

    # =========================================================================
    # Database-Driven Initialization
    # =========================================================================

    def initialize_sinks_from_database(self) -> bool:
        """
        Initialize all virtual sinks defined in the database.

        Reads VirtualSink entries from the database and creates any
        missing sinks. This replaces the functionality of setup_sinks.sh.

        Returns:
            True if all sinks initialized successfully
        """
        try:
            from app.database.models import get_all_virtual_sinks

            sinks = get_all_virtual_sinks(active_only=True)

            if not sinks:
                logger.warning("No active virtual sinks found in database")
                return True

            logger.info(f"Initializing {len(sinks)} virtual sinks from database...")

            success_count = 0
            for sink in sinks:
                if self.create_virtual_sink(sink.name, sink.description):
                    success_count += 1
                else:
                    logger.error(f"Failed to create sink: {sink.name}")

            if success_count == len(sinks):
                logger.info(f"Successfully initialized all {len(sinks)} virtual sinks")
                return True
            else:
                logger.warning(f"Initialized {success_count}/{len(sinks)} virtual sinks")
                return False

        except Exception as e:
            logger.error(f"Error initializing sinks from database: {e}")
            return False

    def cleanup_virtual_sinks(self) -> bool:
        """
        Remove all virtual sinks created by this application.

        Useful for cleanup during shutdown or for testing.

        Returns:
            True if all sinks removed successfully
        """
        try:
            from app.database.models import get_all_virtual_sinks

            sinks = get_all_virtual_sinks()

            if not sinks:
                logger.debug("No virtual sinks to clean up")
                return True

            logger.info(f"Cleaning up {len(sinks)} virtual sinks...")

            success_count = 0
            for sink in sinks:
                if self.remove_virtual_sink(sink.name):
                    success_count += 1

            logger.info(f"Cleaned up {success_count}/{len(sinks)} virtual sinks")
            return success_count == len(sinks)

        except Exception as e:
            logger.error(f"Error cleaning up virtual sinks: {e}")
            return False
