"""
MIDI Controller Module

Handles MIDI device connection, message parsing, and action delegation.
Provides jitter filtering and routes MIDI events to appropriate handlers.
"""

import logging
from typing import Dict, Optional

import mido

from app.database.models import get_config_value

logger = logging.getLogger(__name__)


class MidiController:
    """
    Manages MIDI device connection and message processing.

    Handles MIDI input events, filters jitter, and delegates
    actions to audio management components.
    """

    def __init__(self, audio_manager, loopback_manager):
        """
        Initialize MIDI controller with configuration.

        Args:
            audio_manager: AudioManager instance
            loopback_manager: LoopbackManager instance
        """
        self.audio_manager = audio_manager
        self.loopback_manager = loopback_manager

        # Load configuration from database
        self.midi_device_name = get_config_value("midi_device_name", "MIDI Deck")
        self.jitter_threshold = int(get_config_value("jitter_threshold", "2"))

        # State tracking
        self.last_values = {}  # Track last values for jitter filtering
        self.midi_port = None
        self.running = False

        # Load MIDI mappings from database
        self._load_mappings()

        logger.info(
            f"MidiController initialized (device: {self.midi_device_name}, "
            f"jitter threshold: {self.jitter_threshold})"
        )

    def _load_mappings(self):
        """Load MIDI mappings from database."""
        from app.database.models import get_all_midi_mappings, get_all_virtual_sinks

        # Load all MIDI mappings
        mappings = get_all_midi_mappings()

        # Create lookup dictionaries
        # Button mappings: note -> (sink_name, action)
        self.button_mappings: Dict[int, tuple] = {}

        for mapping in mappings:
            sink = mapping.virtual_sink
            self.button_mappings[mapping.midi_note] = (sink.name, mapping.action)

        # Fader mappings: CC# -> sink_name
        # Assuming faders are CC 1, 2, 3, 4 mapped to channels 1-4
        sinks = get_all_virtual_sinks(active_only=True)
        self.fader_mappings: Dict[int, str] = {}

        for sink in sinks:
            # Map CC number to sink name based on channel number
            cc_num = sink.channel_number
            self.fader_mappings[cc_num] = sink.name

        logger.info(
            f"Loaded {len(self.button_mappings)} button mappings and "
            f"{len(self.fader_mappings)} fader mappings"
        )

    def find_midi_port(self, name: str) -> Optional[str]:
        """
        Find MIDI input port by name.

        Args:
            name: MIDI device name to search for

        Returns:
            Full port name if found, None otherwise

        Raises:
            RuntimeError: If device not found
        """
        try:
            ports = mido.get_input_names()
            logger.debug(f"Available MIDI ports: {ports}")

            for port in ports:
                if name.lower() in port.lower():
                    logger.info(f"Found MIDI port: {port}")
                    return port

            logger.error(f"MIDI device '{name}' not found in available ports: {ports}")
            raise RuntimeError(
                f"MIDI device '{name}' not found. Available: {', '.join(ports)}"
            )

        except Exception as e:
            logger.error(f"Error finding MIDI port: {e}")
            raise

    def handle_control_change(self, control: int, value: int):
        """
        Handle MIDI CC messages (fader volume control).

        Args:
            control: MIDI control change number
            value: MIDI value (0-127)
        """
        # Apply jitter filter
        if not self.apply_jitter_filter(control, value):
            logger.debug(f"CC {control}: value {value} filtered (jitter)")
            return

        # Look up which sink this CC controls
        sink_name = self.fader_mappings.get(control)
        if not sink_name:
            logger.debug(f"CC {control}: no mapping found")
            return

        # Convert MIDI value (0-127) to volume (0.0-1.0)
        volume = value / 127.0

        # Set volume via AudioManager
        if self.audio_manager.set_volume(sink_name, volume):
            logger.debug(f"CC {control}: set {sink_name} volume to {volume:.2%}")
        else:
            logger.warning(f"CC {control}: failed to set volume for {sink_name}")

    def handle_note_on(self, note: int):
        """
        Handle MIDI note messages (button presses).

        Args:
            note: MIDI note number
        """
        # Look up the button mapping
        mapping = self.button_mappings.get(note)
        if not mapping:
            logger.debug(f"Note {note}: no mapping found")
            return

        sink_name, action = mapping
        logger.debug(f"Note {note}: {action} for {sink_name}")

        # Execute the action
        if action == "mute":
            # Toggle mute
            new_state = self.audio_manager.toggle_mute(sink_name)
            if new_state is not None:
                logger.info(
                    f"Toggled mute for {sink_name}: {'muted' if new_state else 'unmuted'}"
                )
            else:
                logger.warning(f"Failed to toggle mute for {sink_name}")

        elif action in ["speaker", "headphone"]:
            # Toggle loopback connection
            # Map action to hardware output name
            from app.database.models import get_all_hardware_outputs

            outputs = get_all_hardware_outputs()
            output_map = {
                "speaker": "SpeakerOut",
                "headphone": "HeadphoneOut",
            }

            output_name = output_map.get(action)
            if output_name:
                # Find the actual hardware output
                hardware_output = None
                for output in outputs:
                    if output.name == output_name:
                        hardware_output = output
                        break

                if hardware_output:
                    # Toggle the connection
                    new_state = self.loopback_manager.toggle(
                        sink_name, hardware_output.device_name
                    )
                    logger.info(
                        f"Toggled {output_name} for {sink_name}: "
                        f"{'connected' if new_state else 'disconnected'}"
                    )
                else:
                    logger.warning(f"Hardware output {output_name} not found")
            else:
                logger.warning(f"Unknown action: {action}")

        else:
            logger.warning(f"Unknown action: {action}")

    def apply_jitter_filter(self, control: int, value: int) -> bool:
        """
        Apply jitter filtering to MIDI values.

        Args:
            control: MIDI control number
            value: New value

        Returns:
            True if value should be applied, False if filtered out
        """
        prev = self.last_values.get(control, -1)
        diff = abs(value - prev)

        if diff >= self.jitter_threshold:
            self.last_values[control] = value
            return True
        return False

    def run(self):
        """
        Main MIDI event loop (blocking).

        Connects to MIDI device and processes messages until interrupted.
        """
        try:
            # Find and open MIDI port
            port_name = self.find_midi_port(self.midi_device_name)
            logger.info(f"Opening MIDI port: {port_name}")

            self.running = True

            with mido.open_input(port_name) as port:
                logger.info("MIDI event loop started - listening for messages")

                for msg in port:
                    if not self.running:
                        logger.info("MIDI event loop stopping...")
                        break

                    # Process MIDI messages
                    if msg.type == "control_change":
                        self.handle_control_change(msg.control, msg.value)
                    elif msg.type == "note_on":
                        # Only handle note_on with velocity > 0 (actual press)
                        if msg.velocity > 0:
                            self.handle_note_on(msg.note)

        except RuntimeError as e:
            logger.error(f"MIDI device error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in MIDI event loop: {e}", exc_info=True)
            raise
        finally:
            self.running = False
            logger.info("MIDI event loop terminated")

    def stop(self):
        """Gracefully stop MIDI listener."""
        logger.info("Stopping MIDI controller...")
        self.running = False
