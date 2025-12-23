"""
Loopback Manager Module

Manages PulseAudio loopback modules for routing audio between
virtual sinks and hardware outputs.

Phase 3 Implementation: Complete loopback management with module
loading/unloading via pactl commands.
"""

import logging
import subprocess
from typing import Dict, List, Optional, Tuple

import pulsectl

logger = logging.getLogger(__name__)


class LoopbackManager:
    """
    Manages loopback connections between virtual sinks and hardware outputs.

    Tracks active loopback modules and provides methods to toggle,
    connect, and disconnect audio routes. Uses pactl for module loading
    and pulsectl for querying module state.
    """

    def __init__(self, pulse: pulsectl.Pulse):
        """
        Initialize LoopbackManager.

        Args:
            pulse: pulsectl.Pulse instance
        """
        self.pulse = pulse
        self.active: Dict[Tuple[str, str], int] = {}  # (source, sink) -> module_id
        logger.info("LoopbackManager initialized")

    def _find_existing(self, source_sink: str, target_sink: str) -> Optional[int]:
        """
        Check if a loopback module already exists for this connection.

        Args:
            source_sink: Source sink name (virtual sink)
            target_sink: Target sink name (hardware output)

        Returns:
            Module ID if found, None otherwise
        """
        try:
            # Check our cache first
            key = (source_sink, target_sink)
            if key in self.active:
                # Verify the module still exists
                try:
                    module = self.pulse.module_info(self.active[key])
                    if module:
                        return self.active[key]
                    else:
                        # Module no longer exists, remove from cache
                        del self.active[key]
                except pulsectl.PulseOperationFailed:
                    # Module doesn't exist, remove from cache
                    del self.active[key]

            # Search through all loopback modules
            for module in self.pulse.module_list():
                if module.name == "module-loopback":
                    # Parse module arguments to find source and sink
                    args = module.argument or ""

                    # Look for source= and sink= in arguments
                    source_match = None
                    sink_match = None

                    for arg in args.split():
                        if arg.startswith("source="):
                            source_match = arg.split("=", 1)[1]
                        elif arg.startswith("sink="):
                            sink_match = arg.split("=", 1)[1]

                    # Check if this matches our connection
                    # Source should be the monitor of the source_sink
                    expected_source = f"{source_sink}.monitor"
                    if source_match == expected_source and sink_match == target_sink:
                        # Found it! Cache and return
                        self.active[key] = module.index
                        logger.debug(
                            f"Found existing loopback: {source_sink} -> {target_sink} (module {module.index})"
                        )
                        return module.index

            return None

        except Exception as e:
            logger.error(f"Error finding existing loopback: {e}")
            return None

    def toggle(self, custom_sink_name: str, hardware_sink_name: str) -> bool:
        """
        Toggle loopback connection.

        Args:
            custom_sink_name: Name of the virtual sink
            hardware_sink_name: Name of the hardware output

        Returns:
            True if connected after toggle, False if disconnected
        """
        if self.is_connected(custom_sink_name, hardware_sink_name):
            success = self.disconnect(custom_sink_name, hardware_sink_name)
            return not success  # Return False if disconnect succeeded
        else:
            return self.connect(custom_sink_name, hardware_sink_name)

    def is_connected(self, custom_sink_name: str, hardware_sink_name: str) -> bool:
        """
        Check if connection exists.

        Args:
            custom_sink_name: Name of the virtual sink
            hardware_sink_name: Name of the hardware output

        Returns:
            True if connected, False otherwise
        """
        module_id = self._find_existing(custom_sink_name, hardware_sink_name)
        return module_id is not None

    def disconnect(self, custom_sink_name: str, hardware_sink_name: str) -> bool:
        """
        Explicitly disconnect a loopback.

        Args:
            custom_sink_name: Name of the virtual sink
            hardware_sink_name: Name of the hardware output

        Returns:
            True if successful, False otherwise
        """
        try:
            module_id = self._find_existing(custom_sink_name, hardware_sink_name)

            if module_id is None:
                logger.debug(
                    f"No loopback to disconnect: {custom_sink_name} -> {hardware_sink_name}"
                )
                return True  # Already disconnected

            # Unload the module using pactl
            cmd = ["pactl", "unload-module", str(module_id)]

            subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Remove from cache
            key = (custom_sink_name, hardware_sink_name)
            if key in self.active:
                del self.active[key]

            logger.info(
                f"Disconnected loopback: {custom_sink_name} -> {hardware_sink_name}"
            )
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to disconnect loopback: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error disconnecting loopback: {e}")
            return False

    def connect(self, custom_sink_name: str, hardware_sink_name: str) -> bool:
        """
        Explicitly connect a loopback.

        Creates a loopback module from the virtual sink's monitor to
        the hardware output.

        Args:
            custom_sink_name: Name of the virtual sink
            hardware_sink_name: Name of the hardware output

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if already connected
            if self.is_connected(custom_sink_name, hardware_sink_name):
                logger.debug(
                    f"Loopback already connected: {custom_sink_name} -> {hardware_sink_name}"
                )
                return True

            # Load loopback module using pactl
            # Source is the monitor of the custom sink
            source = f"{custom_sink_name}.monitor"

            cmd = [
                "pactl",
                "load-module",
                "module-loopback",
                f"source={source}",
                f"sink={hardware_sink_name}",
                # "latency_msec=1",  # Low latency for immediate audio
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Parse module ID from output
            module_id_str = result.stdout.strip()
            if module_id_str.isdigit():
                module_id = int(module_id_str)
                key = (custom_sink_name, hardware_sink_name)
                self.active[key] = module_id
                logger.info(
                    f"Connected loopback: {custom_sink_name} -> {hardware_sink_name} (module {module_id})"
                )
                return True
            else:
                logger.warning(
                    f"Connected loopback but could not parse module ID: {module_id_str}"
                )
                return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to connect loopback: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error connecting loopback: {e}")
            return False

    def disconnect_all(self, custom_sink_name: str) -> int:
        """
        Disconnect all outputs for a sink.

        Args:
            custom_sink_name: Name of the virtual sink

        Returns:
            Number of connections disconnected
        """
        count = 0

        # Get all connections for this sink
        connections = self.get_connections(custom_sink_name)

        for hardware_sink_name in connections:
            if self.disconnect(custom_sink_name, hardware_sink_name):
                count += 1

        logger.info(f"Disconnected {count} loopback(s) for {custom_sink_name}")
        return count

    def get_connections(self, custom_sink_name: str) -> List[str]:
        """
        Get list of connected outputs for a sink.

        Args:
            custom_sink_name: Name of the virtual sink

        Returns:
            List of hardware sink names that are connected
        """
        connections = []

        try:
            # Search through all loopback modules
            expected_source = f"{custom_sink_name}.monitor"

            for module in self.pulse.module_list():
                if module.name == "module-loopback":
                    # Parse module arguments
                    args = module.argument or ""

                    source_match = None
                    sink_match = None

                    for arg in args.split():
                        if arg.startswith("source="):
                            source_match = arg.split("=", 1)[1]
                        elif arg.startswith("sink="):
                            sink_match = arg.split("=", 1)[1]

                    # If source matches our sink's monitor, add the target to list
                    if source_match == expected_source and sink_match:
                        connections.append(sink_match)
                        # Update cache
                        key = (custom_sink_name, sink_match)
                        self.active[key] = module.index

        except Exception as e:
            logger.error(f"Error getting connections for {custom_sink_name}: {e}")

        return connections

    def initialize_connections_from_database(self, session_id: int = None) -> bool:
        """
        Initialize loopback connections from database session.

        Args:
            session_id: Session ID to load connections from (None = current session)

        Returns:
            True if successful, False otherwise
        """
        try:
            from app.database.db import load_session_state
            from app.database.models import get_current_session

            # Get session state
            if session_id is None:
                current = get_current_session()
                if current:
                    session_id = current.id
                else:
                    logger.warning("No current session found")
                    return False

            state = load_session_state(session_id)
            if not state:
                logger.error(f"Failed to load session state for session {session_id}")
                return False

            connections = state.get("connections", {})

            logger.info(
                f"Initializing {sum(len(outputs) for outputs in connections.values())} connections from database..."
            )

            for sink_name, output_names in connections.items():
                for output_name in output_names:
                    if not self.connect(sink_name, output_name):
                        logger.warning(f"Failed to connect: {sink_name} -> {output_name}")

            logger.info("Connection initialization complete")
            return True

        except Exception as e:
            logger.error(f"Error initializing connections from database: {e}")
            return False

    def cleanup_all_loopbacks(self) -> int:
        """
        Remove all loopback modules managed by this application.

        Returns:
            Number of loopbacks removed
        """
        count = 0

        try:
            # Get all custom sinks from database
            from app.database.models import get_all_virtual_sinks

            sinks = get_all_virtual_sinks()

            for sink in sinks:
                count += self.disconnect_all(sink.name)

            logger.info(f"Cleaned up {count} loopback connection(s)")

        except Exception as e:
            logger.error(f"Error cleaning up loopbacks: {e}")

        return count
