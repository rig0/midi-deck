<div align="center">

<img src="https://i.imgur.com/e6tMcvS.png" alt="Desktop-Agent" width="200"/>

# Midi Deck

![Python Version](https://img.shields.io/badge/Python%203.11+-3978b5?logo=python&logoColor=white)
![Flake8](https://img.shields.io/badge/Flake8-f6d844?logo=)
![Black](https://img.shields.io/badge/Black-000?logo=black)

![Latest Tag](https://img.shields.io/github/v/tag/rig0/midi-deck?labelColor=222&color=80ff63&label=latest)
[![Code Factor](https://img.shields.io/codefactor/grade/github/rig0/midi-deck?color=80ff63&labelColor=222)](https://www.codefactor.io/repository/github/rig0/midi-deck/overview/main)
![Maintained](https://img.shields.io/badge/maintained-yes-80ff63?labelColor=222)
![GitHub last commit](https://img.shields.io/github/last-commit/rig0/midi-deck?labelColor=222&color=80ff63)

**Audio control software for MIDI Deck hardware interfacing with Linux desktop audio (PipeWire/PulseAudio).**

</div>

> [!NOTE]
> Currently in early development with a lot of moving parts.
> This software is intended to be used with proprietary hardware that is still under production.


## Features

- **MIDI Hardware Control**: Full integration with proprietary MIDI Deck hardware
- **Virtual Audio Channels**: Create and manage up to 4 independent virtual audio channels
- **Flexible Routing**: Route any audio channel to any hardware output (speakers, headphones, etc.)
- **Volume Control**: Per-channel volume control via MIDI faders
- **Quick Mute**: One-button mute toggle for each channel
- **Session Management**: Save and restore complete audio configurations
- **Web Interface**: Modern, responsive web UI for configuration and real-time control
- **Database Persistence**: SQLite-based configuration storage
- **Auto-restore**: Automatically restores your audio configuration on startup

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [MIDI Controller](#midi-controller)
  - [Web Interface](#web-interface)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)


## Installation

### System Requirements

- **Operating System**: Linux
- **Python**: 3.11 or higher
- **Audio Server**: PulseAudio or PipeWire
- **MIDI Device**: MIDI Deck hardware
- **Dependencies**: gcc-c++, python3-devel, alsa-lib-devel

### Install Dependencies

#### Debian/Ubuntu
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv python3-dev gcc alsa-utils pulseaudio
```

#### Fedora/RHEL
```bash
sudo dnf install python3 python3-pip python3-devel gcc alsa-lib-devel pulseaudio
```

### Install MIDI Deck

1. **Clone the repository**
```bash
git clone https://github.com/rig0/midi-deck.git
cd midi-deck
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

4. **Initialize database**
```bash
# The database will be created automatically on first run
python3 main.py --help
```

## Quick Start

### Run with MIDI Controller and Web Interface (Recommended)

```bash
# Activate virtual environment
source venv/bin/activate

# Start MIDI Deck with web interface
python3 main.py
```

Access the web interface at: **http://127.0.0.1:5000**

### Run Web Interface Only (Configuration Mode)

```bash
# Start web interface without MIDI controller
python3 main.py --web-only
```

### Run MIDI Controller Only (Headless Mode)

```bash
# Start MIDI controller without web interface
python3 main.py --no-web
```

## Usage

### MIDI Controller

The MIDI Deck hardware has:
- **4 Faders**: Control volume for each of the 4 audio channels
- **12 Buttons**: 3 buttons per channel (Speaker, Headphone, Mute)

**Default Channel Layout:**
- **Channel 1 (Fader 1)**: MainSink - Main desktop audio
- **Channel 2 (Fader 2)**: WebSink - Web browser audio
- **Channel 3 (Fader 3)**: MusicSink - Music player audio
- **Channel 4 (Fader 4)**: DiscordSink - VoIP/Discord audio

**Button Functions:**
- **Button 1**: Toggle speaker output for the channel
- **Button 2**: Toggle headphone output for the channel
- **Button 3**: Mute/unmute the channel

### Web Interface

The web interface provides five main pages:

#### 1. Dashboard (/)
- Overview of current audio state
- Quick session save/load
- System status display
- Real-time volume and mute indicators

#### 2. Configuration (/config)
- Manage hardware outputs (speakers, headphones, etc.)
- Configure virtual sinks (audio channels)
- Adjust application settings
- Hardware device discovery tool

#### 3. Sessions (/sessions)
- Create new audio sessions
- Load existing sessions
- Edit session metadata
- Delete sessions

#### 4. Real-Time Control (/control)
- Live volume sliders for each channel
- Mute toggle buttons
- Output routing matrix
- Real-time status updates

#### 5. MIDI Mappings (/midi)
- View MIDI button to function mappings
- Edit button assignments
- Configure fader mappings
- Adjust MIDI device settings

## Configuration

### Database Location

Default database path: `data/midi_deck.db`

To use a custom database path:
```bash
python3 main.py --config /path/to/custom.db
```

### Configuration Values

All configuration is stored in the SQLite database and can be modified via the web interface or directly in the database.

**Key Configuration Options:**
- `midi_device_name`: Name of MIDI device to connect to (default: "MIDI Deck")
- `jitter_threshold`: MIDI jitter filtering threshold (default: 2)
- `web_host`: Web interface host address (default: 127.0.0.1)
- `web_port`: Web interface port (default: 5000)
- `auto_save_session`: Auto-save session on changes (default: true)
- `log_level`: Logging verbosity (default: INFO)

### Hardware Outputs

Configure your hardware audio outputs in the web interface:
1. Go to Configuration page
2. Click "Hardware Discovery" to scan for available devices
3. Add outputs with friendly names (e.g., "SpeakerOut", "HeadphoneOut")

### Virtual Sinks (Audio Channels)

Each virtual sink represents an independent audio channel:
1. Go to Configuration page
2. Manage virtual sinks (add, edit, delete)
3. Assign channel numbers (1-4) for fader mapping

## Command-Line Options

```
usage: main.py [-h] [--web-only] [--no-web] [--config CONFIG] [--debug]

MIDI Deck Audio Controller

optional arguments:
  -h, --help       show this help message and exit
  --web-only       Run web interface only (no MIDI controller)
  --no-web         Run MIDI controller only (no web interface)
  --config CONFIG  Path to database file (default: data/midi_deck.db)
  --debug          Enable debug logging
```

## Architecture

MIDI Deck uses a modular, layered architecture:

```
midi-deck/
├── main.py                    # Application entry point
├── app/
│   ├── core/                  # Core business logic
│   │   ├── audio_manager.py   # PulseAudio/PipeWire interface
│   │   ├── midi_controller.py # MIDI device interface
│   │   ├── loopback_manager.py# Audio routing management
│   │   └── session_manager.py # Session save/restore
│   ├── database/              # Data persistence layer
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   ├── db.py              # Database access layer
│   │   └── migrations.py      # Database migration utilities
│   ├── web/                   # Web interface
│   │   ├── app.py             # Flask application factory
│   │   ├── routes.py          # REST API endpoints
│   │   ├── static/            # CSS, JavaScript
│   │   └── templates/         # HTML templates
│   ├── config/                # Configuration management
│   └── utils/                 # Utility functions
├── tests/                     # Test suite
├── data/                      # Database storage
└── logs/                      # Log files
```

**Key Components:**
- **AudioManager**: Manages PulseAudio/PipeWire sinks, volumes, and mute states
- **LoopbackManager**: Manages audio routing between virtual sinks and hardware outputs
- **MidiController**: Handles MIDI device communication and message parsing
- **SessionManager**: Handles session save/restore functionality
- **Web Server**: Flask-based REST API and web interface

## Testing

### Run Test Suite

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/test_database.py -v

# Run with coverage report
python3 -m pytest tests/ --cov=app --cov-report=html
```

### Test Categories

- **Unit Tests**: Fast, isolated tests with mocking
- **Integration Tests**: Tests requiring external resources (database, PulseAudio)
- **Web Tests**: Flask application and API endpoint tests


## Troubleshooting

### MIDI Device Not Found

**Issue**: Application cannot find MIDI device

**Solutions**:
1. Check device is connected: `aconnect -l`
2. Verify device name in configuration matches actual device name
3. Check permissions: user must be in `audio` group
```bash
sudo usermod -a -G audio $USER
# Log out and back in for changes to take effect
```

### PulseAudio Connection Failed

**Issue**: Cannot connect to PulseAudio server

**Solutions**:
1. Check PulseAudio is running: `pactl info`
2. Start PulseAudio if needed: `pulseaudio --start`
3. For PipeWire users, ensure PulseAudio compatibility layer is active

### Virtual Sinks Not Created

**Issue**: Virtual sinks don't appear after startup

**Solutions**:
1. Check logs for errors: `tail -f logs/midi_deck.log`
2. Verify PulseAudio modules are available: `pactl list modules short`
3. Manually test sink creation: `pactl load-module module-null-sink sink_name=TestSink`

### Web Interface Not Accessible

**Issue**: Cannot access web interface at http://127.0.0.1:5000

**Solutions**:
1. Check application started with web interface enabled (not `--no-web`)
2. Verify port 5000 is not in use: `lsof -i :5000`
3. Check firewall settings
4. Try different host/port in configuration

### Session Not Restoring

**Issue**: Saved session doesn't restore correctly

**Solutions**:
1. Verify session exists in database: Open web interface -> Sessions page
2. Check session is marked as current
3. Review logs for restoration errors
4. Ensure all virtual sinks referenced in session still exist
