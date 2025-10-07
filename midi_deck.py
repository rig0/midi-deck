#!/usr/bin/env python3
import mido
import pulsectl

# Midi device name
MIDI_NAME = "MIDI Deck"

# Hardware outputs
SpeakerOut   = "alsa_output.pci-0000_00_1f.3.analog-stereo"
HeadphoneOut = "alsa_output.usb-3142_fifine_Microphone-00.analog-stereotypical"

# Virtual inputs/sinks
SINKS = {
    1: "MainSink",
    2: "WebSink",
    3: "MusicSink",
    4: "DiscordSink",
}

# Define Macros/Note Keys
ACTIONS = {
    # MainSink
    5: (SINKS[1], "speaker"),
    6: (SINKS[1], "headphone"),
    7: (SINKS[1], "mute"),
    # WebSink
    8: (SINKS[2], "speaker"),
    9: (SINKS[2], "headphone"),
    10: (SINKS[2], "mute"),
    # MusicSink
    11: (SINKS[3], "speaker"),
    12: (SINKS[3], "headphone"),
    13: (SINKS[3], "mute"),
    # DiscordSink
    14: (SINKS[4], "speaker"),
    15: (SINKS[4], "headphone"),
    16: (SINKS[4], "mute"),
}


# Previous values for jitter filtering
prev_val = {cc: -1 for cc in SINKS}
THRESHOLD = 1


# Find the MIDI input port by name.
def find_midi_port(name: str):
    for port_name in mido.get_input_names():
        if name in port_name:
            return port_name
    raise RuntimeError(f"MIDI device '{name}' not found. Available: {mido.get_input_names()}")


# Use faders to change volume
def set_volume(pulse: pulsectl.Pulse, sink_name: str, value: int):
    # Set sink volume (0–127 mapped to 0–1.0 scale).
    volume = value / 127.0
    sinks = pulse.sink_list()
    for sink in sinks:
        if sink_name in sink.name or sink.description == sink_name:
            vol = pulsectl.PulseVolumeInfo([volume] * len(sink.volume.values))
            pulse.volume_set(sink, vol)
            print(f"Set {sink.description or sink.name} to {int(volume * 100)}%")
            return
    print(f"Sink {sink_name} not found")


def main():
    midi_port = find_midi_port(MIDI_NAME)
    print(f"Using MIDI port: {midi_port}")

    with pulsectl.Pulse("midi-volume-control") as pulse:
        with mido.open_input(midi_port) as inport:
            print("Listening for MIDI CC messages...")
            for msg in inport:
                if msg.type == "control_change":
                    cc = msg.control
                    val = msg.value
                    if cc in SINKS:
                        prev = prev_val[cc]
                        if abs(val - prev) >= THRESHOLD:
                            set_volume(pulse, SINKS[cc], val)
                            prev_val[cc] = val


if __name__ == "__main__":
    main()
