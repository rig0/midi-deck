#!/usr/bin/env python3
import mido
import pulsectl

# Midi device name
MIDI_NAME = "MIDI Deck"

# Hardware outputs
SpeakerOut   = "alsa_output.pci-0000_00_1f.3.analog-stereo"
HeadphoneOut = "alsa_output.usb-3142_fifine_Microphone-00.analog-stereo"

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
    36: (SINKS[1], "speaker"),
    37: (SINKS[1], "headphone"),
    38: (SINKS[1], "mute"),
    # WebSink
    40: (SINKS[2], "speaker"),
    41: (SINKS[2], "headphone"),
    42: (SINKS[2], "mute"),
    # MusicSink
    44: (SINKS[3], "speaker"),
    45: (SINKS[3], "headphone"),
    46: (SINKS[3], "mute"),
    # DiscordSink
    48: (SINKS[4], "speaker"),
    49: (SINKS[4], "headphone"),
    50: (SINKS[4], "mute"),
}

# Threshold for jitter filtering
THRESHOLD = 2
last_values = {}

# Create pulse controller
pulse = pulsectl.Pulse("midi-deck-interface")


# Find the MIDI input port by name
def find_midi_port(name: str):
    for port_name in mido.get_input_names():
        if name in port_name:
            return port_name
    raise RuntimeError(f"MIDI device '{name}' not found. Available: {mido.get_input_names()}")

# Find sink by name
def find_sink_by_name(name):
    for sink in pulse.sink_list():
        if sink.name == name:
            return sink
    return None

# Set volume with sliders
def set_volume(sink_name, value):
    sink = find_sink_by_name(sink_name)
    if sink:
        # scale MIDI 0–127 → Pulse 0.0–1.0
        vol = float(value) / 127.0
        pulse.volume_set_all_chans(sink, vol)
        percent = int(vol * 100)
        print(f"[VOLUME] {sink_name} -> {percent}%")

# Toggle mute with macropad
def toggle_mute(sink_name):
    sink = find_sink_by_name(sink_name)
    if sink:
        pulse.mute(sink, not sink.mute)
        print(f"[MUTE] {sink_name} -> {sink.mute}")

# Toggle output audio device with macropad
def toggle_output(sink_name, output_device):
    sink = find_sink_by_name(sink_name)
    if not sink:
        return
    print(f"Sink: {sink}")
    print(f"Output Device: {output_device}")
    print(f"Input List: {pulse.sink_list()}")
    for input in pulse.sink_input_list():
        print(f"Input: {input}")
        if input.sink == sink.index:
            output = find_sink_by_name(output_device)
            print(f"Output: {output}")
            if output:
                # FIX THIS
                #pulse.sink_input_move(sink.index, output.index)
                print(f"[MOVE] {sink.name} -> {output.description}")

# Parse the midi messages
def handle_cc(cc_type, cc_number, value):
    # Sliders (volume)
    if cc_type == "control_change" and cc_number in SINKS:
        prev = last_values.get(cc_number, -1)
        diff = abs(value - prev)
        if diff >= THRESHOLD:
            set_volume(SINKS[cc_number], value)
            last_values[cc_number] = value

    # Buttons (mute/output toggle)
    elif cc_type == "note_on" and value in ACTIONS:
        sink_name, action = ACTIONS[value]
        if action == "mute":
            toggle_mute(sink_name)
        elif action == "speaker":
            toggle_output(sink_name, SpeakerOut)
        elif action == "headphone":
            toggle_output(sink_name, HeadphoneOut)

# MIDI listener
print("Listening for MIDI inputs...")
with mido.open_input(find_midi_port(MIDI_NAME)) as port:
    for msg in port:
        #print(msg)
        if msg.type == "control_change":
            handle_cc(msg.type, msg.control, msg.value)
        elif msg.type == "note_on":
            handle_cc(msg.type, 0, msg.note)
