# Use Fedora as the base image
FROM fedora:latest

# Install system dependencies
# - python3: Python runtime
# - python3-pip: Python package manager
# - python3-devel: Python development headers (required for building python-rtmidi)
# - gcc-c++: C++ compiler (required for building python-rtmidi)
# - alsa-lib-devel: ALSA development libraries (required for building python-rtmidi)
# - alsa-lib: ALSA sound library for MIDI device access
# - pulseaudio-libs: PulseAudio client libraries
# - pipewire-pulseaudio: PipeWire PulseAudio compatibility layer
# - dbus: D-Bus system for inter-process communication
# - dbus-libs: D-Bus client libraries
RUN dnf install -y \
    python3 \
    python3-pip \
    python3-devel \
    gcc-c++ \
    alsa-lib-devel \
    alsa-lib \
    pulseaudio-libs \
    pipewire-pulseaudio \
    dbus \
    dbus-libs \
    && dnf clean all

# Set the working directory
WORKDIR /app

# Copy requirements.txt first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Make the main script executable
RUN chmod +x midi_deck.py

# Set the entrypoint to run the MIDI deck application
ENTRYPOINT ["python3", "midi_deck.py"]
