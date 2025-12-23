"""
Application Constants

Default values used for database initialization and fallbacks.
"""

# MIDI Device Configuration
MIDI_DEVICE_NAME = "MIDI Deck"

# Hardware Output Devices (defaults for database seeding)
HARDWARE_OUTPUTS = {
    "SpeakerOut": "alsa_output.pci-0000_00_1f.3.analog-stereo",
    "HeadphoneOut": "alsa_output.usb-3142_fifine_Microphone-00.analog-stereo",
}

# Virtual Sinks/Channels (defaults for database seeding)
VIRTUAL_SINKS = {
    1: "MainSink",
    2: "WebSink",
    3: "MusicSink",
    4: "DiscordSink",
}

# MIDI Button Mappings (defaults for database seeding)
MIDI_BUTTON_MAPPINGS = {
    # MainSink (Channel 1)
    36: ("MainSink", "speaker"),
    37: ("MainSink", "headphone"),
    38: ("MainSink", "mute"),
    # WebSink (Channel 2)
    40: ("WebSink", "speaker"),
    41: ("WebSink", "headphone"),
    42: ("WebSink", "mute"),
    # MusicSink (Channel 3)
    44: ("MusicSink", "speaker"),
    45: ("MusicSink", "headphone"),
    46: ("MusicSink", "mute"),
    # DiscordSink (Channel 4)
    48: ("DiscordSink", "speaker"),
    49: ("DiscordSink", "headphone"),
    50: ("DiscordSink", "mute"),
}

# MIDI Control Change Numbers (for fader volume control)
# Maps CC number to sink channel
MIDI_FADER_MAPPINGS = {
    1: "MainSink",
    2: "WebSink",
    3: "MusicSink",
    4: "DiscordSink",
}

# Jitter filtering threshold for MIDI values
JITTER_THRESHOLD = 2

# Database Configuration
DEFAULT_DB_PATH = "data/midi_deck.db"

# Web Interface Configuration
DEFAULT_WEB_HOST = "127.0.0.1"
DEFAULT_WEB_PORT = 5000

# Logging Configuration
DEFAULT_LOG_LEVEL = "INFO"
