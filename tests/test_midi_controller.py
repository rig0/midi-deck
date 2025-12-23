"""
Unit Tests for MidiController

Tests for MIDI message parsing, jitter filtering, and action delegation.
"""

import unittest
from unittest.mock import MagicMock, Mock, patch

from app.core.midi_controller import MidiController


class TestMidiController(unittest.TestCase):
    """Test cases for MidiController class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock mido and database
        self.mido_patcher = patch("app.core.midi_controller.mido")
        self.config_patcher = patch("app.core.midi_controller.get_config_value")
        self.mappings_patcher = patch("app.database.models.get_all_midi_mappings")
        self.sinks_patcher = patch("app.database.models.get_all_virtual_sinks")

        self.mock_mido = self.mido_patcher.start()
        self.mock_get_config = self.config_patcher.start()
        self.mock_get_mappings = self.mappings_patcher.start()
        self.mock_get_sinks = self.sinks_patcher.start()

        # Mock AudioManager and LoopbackManager
        self.mock_audio = Mock()
        self.mock_loopback = Mock()

        # Mock MIDI port
        self.mock_port = MagicMock()
        self.mock_mido.open_input.return_value = self.mock_port

        # Mock database config
        self.mock_get_config.side_effect = lambda key, default=None: {
            "midi_device_name": "TestMIDI",
            "jitter_threshold": "2",
        }.get(key, default)

        # Mock MIDI mappings - create test mapping for note 36 (mute action)
        self.mock_get_mappings.return_value = [
            {"midi_note": 36, "sink_name": "TestSink", "action": "mute"}
        ]

        # Mock virtual sinks - create test sink for fader mapping
        mock_virtual_sink = Mock()
        mock_virtual_sink.name = "TestSink"
        mock_virtual_sink.channel_number = 1  # CC1 -> TestSink
        self.mock_get_sinks.return_value = [mock_virtual_sink]

        # Initialize MidiController
        self.midi_controller = MidiController(
            audio_manager=self.mock_audio, loopback_manager=self.mock_loopback
        )

    def tearDown(self):
        """Clean up after tests."""
        self.mido_patcher.stop()
        self.config_patcher.stop()
        self.mappings_patcher.stop()
        self.sinks_patcher.stop()

    def test_initialization(self):
        """Test MidiController initialization."""
        self.assertIsNotNone(self.midi_controller)
        self.assertEqual(self.midi_controller.audio_manager, self.mock_audio)
        self.assertEqual(self.midi_controller.loopback_manager, self.mock_loopback)

    def test_find_midi_port(self):
        """Test MIDI port discovery."""
        # Mock available MIDI ports
        self.mock_mido.get_input_names.return_value = [
            "TestMIDI 0",
            "Other Device 1",
            "TestMIDI 1",
        ]

        # Find port
        port_name = self.midi_controller.find_midi_port("TestMIDI")

        # Verify
        self.assertIsNotNone(port_name)
        self.assertIn("TestMIDI", port_name)

        """Test jitter filter allows significant changes."""
        # First value
        result = self.midi_controller.apply_jitter_filter(0, 50)
        self.assertTrue(result)  # First value always passes

        # Significant change (above threshold)
        result = self.midi_controller.apply_jitter_filter(0, 55)
        self.assertTrue(result)  # Change of 5 > threshold of 2

    def test_jitter_filter_block(self):
        """Test jitter filter blocks small changes."""
        # First value
        self.midi_controller.apply_jitter_filter(0, 50)

        # Small change (below threshold)
        result = self.midi_controller.apply_jitter_filter(0, 51)
        self.assertFalse(result)  # Change of 1 < threshold of 2

    def test_handle_control_change_fader(self):
        """Test handling MIDI CC messages (fader volume)."""
        # Mock message
        mock_message = Mock()
        mock_message.control = 1  # Fader 1 (Channel 1)
        mock_message.value = 64  # 50% volume (64/127)

        # Handle message
        self.midi_controller.handle_control_change(
            mock_message.control, mock_message.value
        )

        # Verify volume was set
        self.mock_audio.set_volume.assert_called_once()
        args = self.mock_audio.set_volume.call_args[0]
        self.assertEqual(args[0], "TestSink")  # Sink name
        self.assertAlmostEqual(args[1], 64 / 127, places=2)  # Volume

    def test_handle_note_on_mute(self):
        """Test handling MIDI note messages (mute button)."""
        # Handle mute button press
        self.midi_controller.handle_note_on(36)

        # Verify mute was toggled
        self.mock_audio.toggle_mute.assert_called_once_with("TestSink")


if __name__ == "__main__":
    unittest.main()
