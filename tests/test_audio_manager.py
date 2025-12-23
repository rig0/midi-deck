"""
Unit Tests for AudioManager

Tests for audio device management, volume control, and mute functionality.
Note: These tests use mocking to avoid requiring actual PulseAudio/PipeWire.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, call, patch

from app.core.audio_manager import AudioManager


class TestAudioManager(unittest.TestCase):
    """Test cases for AudioManager class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock pulsectl to avoid needing actual PulseAudio
        self.pulsectl_patcher = patch("app.core.audio_manager.pulsectl")
        self.mock_pulsectl = self.pulsectl_patcher.start()

        # Mock subprocess for pactl commands
        self.subprocess_patcher = patch("app.core.audio_manager.subprocess")
        self.mock_subprocess = self.subprocess_patcher.start()

        # Create mock pulse instance that supports context manager
        self.mock_pulse = MagicMock()
        self.mock_pulse.__enter__ = MagicMock(return_value=self.mock_pulse)
        self.mock_pulse.__exit__ = MagicMock(return_value=False)
        self.mock_pulsectl.Pulse.return_value = self.mock_pulse

        # Initialize AudioManager with mocked dependencies
        self.audio_manager = AudioManager()

    def tearDown(self):
        """Clean up after tests."""
        self.pulsectl_patcher.stop()
        self.subprocess_patcher.stop()

    def test_initialization(self):
        """Test AudioManager initialization."""
        self.assertIsNotNone(self.audio_manager)
        self.assertIsNotNone(self.audio_manager._module_cache)

    def test_list_hardware_sinks(self):
        """Test hardware sink enumeration."""
        # Mock sink list
        mock_sink1 = Mock()
        mock_sink1.name = "alsa_output.pci-0000_00_1f.3.analog-stereo"
        mock_sink1.description = "Built-in Audio Analog Stereo"
        mock_sink1.index = 1
        mock_sink1.driver = "alsa"

        mock_sink2 = Mock()
        mock_sink2.name = "alsa_output.usb-device.analog-stereo"
        mock_sink2.description = "USB Audio Device"
        mock_sink2.index = 2
        mock_sink2.driver = "alsa"

        self.mock_pulse.sink_list.return_value = [mock_sink1, mock_sink2]

        # Call method
        sinks = self.audio_manager.list_hardware_sinks()

        # Verify results
        self.assertEqual(len(sinks), 2)
        self.assertEqual(sinks[0]["name"], "alsa_output.pci-0000_00_1f.3.analog-stereo")
        self.assertEqual(sinks[0]["description"], "Built-in Audio Analog Stereo")
        self.assertEqual(sinks[1]["name"], "alsa_output.usb-device.analog-stereo")

    def test_create_virtual_sink(self):
        """Test virtual sink creation."""
        # Mock find_sink_by_name to return None (sink doesn't exist)
        self.mock_pulse.sink_list.return_value = []

        # Mock successful pactl command
        mock_result = Mock()
        mock_result.stdout = "42"
        mock_result.returncode = 0
        self.mock_subprocess.run.return_value = mock_result

        # Create sink
        result = self.audio_manager.create_virtual_sink(
            "TestSink", "Test Sink Description"
        )

        # Verify pactl was called
        self.assertTrue(result)
        self.mock_subprocess.run.assert_called_once()
        call_args = self.mock_subprocess.run.call_args[0][0]
        self.assertIn("pactl", call_args)
        self.assertIn("load-module", call_args)
        self.assertIn("module-null-sink", call_args)
        self.assertIn("sink_name=TestSink", call_args)

    def test_create_virtual_sink_failure(self):
        """Test virtual sink creation failure handling."""
        # Mock find_sink_by_name to return None (sink doesn't exist)
        self.mock_pulse.sink_list.return_value = []

        # Mock failed pactl command - raise CalledProcessError
        import subprocess

        self.mock_subprocess.CalledProcessError = subprocess.CalledProcessError
        self.mock_subprocess.run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="pactl", stderr="Error"
        )

        # Create sink
        result = self.audio_manager.create_virtual_sink(
            "TestSink", "Test Sink Description"
        )

        # Verify failure is handled
        self.assertFalse(result)

    def test_remove_virtual_sink(self):
        """Test virtual sink removal."""
        # Mock sink with module info
        mock_sink = Mock()
        mock_sink.name = "TestSink"
        mock_sink.owner_module = 42

        self.mock_pulse.sink_list.return_value = [mock_sink]

        # Mock successful pactl command
        mock_result = Mock()
        mock_result.returncode = 0
        self.mock_subprocess.run.return_value = mock_result

        # Remove sink
        result = self.audio_manager.remove_virtual_sink("TestSink")

        # Verify pactl was called to unload module
        self.assertTrue(result)
        call_args = self.mock_subprocess.run.call_args[0][0]
        self.assertIn("pactl", call_args)
        self.assertIn("unload-module", call_args)
        self.assertIn("42", call_args)

    def test_find_sink_by_name(self):
        """Test finding sink by exact name."""
        # Mock sink list
        mock_sink = Mock()
        mock_sink.name = "TestSink"
        mock_sink.description = "Test Sink"

        self.mock_pulse.sink_list.return_value = [mock_sink]

        # Find sink
        found_sink = self.audio_manager.find_sink_by_name("TestSink")

        # Verify
        self.assertIsNotNone(found_sink)
        self.assertEqual(found_sink.name, "TestSink")

    def test_find_sink_by_name_not_found(self):
        """Test finding non-existent sink."""
        self.mock_pulse.sink_list.return_value = []

        # Find sink
        found_sink = self.audio_manager.find_sink_by_name("NonExistentSink")

        # Verify
        self.assertIsNone(found_sink)

    def test_set_volume(self):
        """Test volume control."""
        # Mock sink
        mock_sink = Mock()
        mock_sink.name = "TestSink"
        mock_sink.index = 5

        self.mock_pulse.sink_list.return_value = [mock_sink]

        # Set volume to 75%
        result = self.audio_manager.set_volume("TestSink", 0.75)

        # Verify
        self.assertTrue(result)
        self.mock_pulse.volume_set_all_chans.assert_called_once()

    def test_set_volume_invalid_range(self):
        """Test volume control with invalid values."""
        # Mock sink
        mock_sink = Mock()
        mock_sink.name = "TestSink"
        self.mock_pulse.sink_list.return_value = [mock_sink]

        # Try to set volume above 1.0 (should be clamped)
        result = self.audio_manager.set_volume("TestSink", 1.5)

        # Should still succeed but volume should be clamped
        self.assertTrue(result)

        # Try negative volume (should be clamped)
        result = self.audio_manager.set_volume("TestSink", -0.5)
        self.assertTrue(result)

    def test_get_volume(self):
        """Test volume retrieval."""
        # Mock sink with volume
        mock_sink = Mock()
        mock_sink.name = "TestSink"
        mock_volume = Mock()
        mock_volume.values = [0.75, 0.75]  # Stereo at 75%
        mock_volume.value_flat = 0.75  # Average volume
        mock_sink.volume = mock_volume

        self.mock_pulse.sink_list.return_value = [mock_sink]

        # Get volume
        volume = self.audio_manager.get_volume("TestSink")

        # Verify
        self.assertIsNotNone(volume)
        self.assertAlmostEqual(volume, 0.75, places=2)

    def test_get_volume_sink_not_found(self):
        """Test volume retrieval for non-existent sink."""
        self.mock_pulse.sink_list.return_value = []

        # Get volume
        volume = self.audio_manager.get_volume("NonExistentSink")

        # Verify
        self.assertIsNone(volume)

    def test_toggle_mute(self):
        """Test mute toggle."""
        # Mock sink
        mock_sink = Mock()
        mock_sink.name = "TestSink"
        mock_sink.index = 5
        mock_sink.mute = 0  # Not muted

        self.mock_pulse.sink_list.return_value = [mock_sink]

        # Toggle mute (should mute)
        result = self.audio_manager.toggle_mute("TestSink")

        # Verify
        self.assertTrue(result)  # Returns new mute state (True = muted)
        self.mock_pulse.mute.assert_called_once()

    def test_set_mute(self):
        """Test explicit mute control."""
        # Mock sink
        mock_sink = Mock()
        mock_sink.name = "TestSink"
        mock_sink.index = 5

        self.mock_pulse.sink_list.return_value = [mock_sink]

        # Mute
        result = self.audio_manager.set_mute("TestSink", True)
        self.assertTrue(result)
        self.mock_pulse.mute.assert_called()

        # Unmute
        result = self.audio_manager.set_mute("TestSink", False)
        self.assertTrue(result)

    def test_is_muted(self):
        """Test mute state retrieval."""
        # Mock muted sink
        mock_sink = Mock()
        mock_sink.name = "TestSink"
        mock_sink.mute = 1  # Muted

        self.mock_pulse.sink_list.return_value = [mock_sink]

        # Check mute state
        is_muted = self.audio_manager.is_muted("TestSink")

        # Verify
        self.assertTrue(is_muted)

    def test_set_default_sink(self):
        """Test setting default sink."""
        # Mock sink
        mock_sink = Mock()
        mock_sink.name = "TestSink"

        self.mock_pulse.sink_list.return_value = [mock_sink]

        # Set as default
        result = self.audio_manager.set_default_sink("TestSink")

        # Verify
        self.assertTrue(result)
        self.mock_pulse.sink_default_set.assert_called_once_with(mock_sink)

    def test_initialize_sinks_from_database(self):
        """Test sink initialization from database."""
        # Mock database
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")

        with patch("app.database.models.get_all_virtual_sinks") as mock_get_sinks:
            # Mock virtual sinks in database
            mock_sink1 = Mock()
            mock_sink1.name = "MainSink"
            mock_sink1.description = "Main Audio Sink"

            mock_sink2 = Mock()
            mock_sink2.name = "WebSink"
            mock_sink2.description = "Web Browser Sink"

            mock_get_sinks.return_value = [mock_sink1, mock_sink2]

            # Mock pactl to succeed
            mock_result = Mock()
            mock_result.stdout = "42"
            mock_result.returncode = 0
            self.mock_subprocess.run.return_value = mock_result

            # Mock find_sink_by_name to return None (sinks don't exist)
            self.mock_pulse.sink_list.return_value = []

            # Initialize sinks
            self.audio_manager.initialize_sinks_from_database()

            # Verify sinks were created
            self.assertEqual(self.mock_subprocess.run.call_count, 2)

        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)

    def test_error_handling_pulse_exception(self):
        """Test error handling when PulseAudio raises exception."""
        # Mock pulse to raise exception
        self.mock_pulse.sink_list.side_effect = Exception("PulseAudio error")

        # Try to list sinks (should handle gracefully)
        result = self.audio_manager.list_hardware_sinks()

        # Should return empty list on error
        self.assertEqual(result, [])


class TestAudioManagerIntegration(unittest.TestCase):
    """Integration tests for AudioManager (requires actual PulseAudio)."""

    def setUp(self):
        """Set up test fixtures."""
        # These tests are skipped if PulseAudio is not available
        try:
            import pulsectl

            self.pulse_test = pulsectl.Pulse("test")
            self.pulse_test.close()
            self.pulse_available = True
        except Exception as e:
            print(f"Error setting up pulsectl: {e}")
            self.pulse_available = False

    def test_real_pulse_connection(self):
        """Test real PulseAudio connection (integration test)."""
        if not self.pulse_available:
            self.skipTest("PulseAudio not available")

        # Create real AudioManager
        audio_manager = AudioManager()

        # Test basic operations
        sinks = audio_manager.list_hardware_sinks()
        self.assertIsInstance(sinks, list)

        # If there are sinks, test volume operations
        if len(sinks) > 0:
            sink_name = sinks[0]["name"]

            # Get current volume
            volume = audio_manager.get_volume(sink_name)
            self.assertIsNotNone(volume)
            self.assertGreaterEqual(volume, 0.0)
            self.assertLessEqual(volume, 1.0)


if __name__ == "__main__":
    unittest.main()
