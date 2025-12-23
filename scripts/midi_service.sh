#!/usr/bin/env bash
sleep 15s
# ----------------------------
# Configuration
# ----------------------------
TOOLBOX_NAME="midi-deck"   # replace with your toolbox name
SCRIPTS=(
    "/home/rambo/Apps/MidiDeck/midi_deck.py"
)

# ----------------------------
# Run scripts inside toolbox
# ----------------------------
for SCRIPT in "${SCRIPTS[@]}"; do
    # Run each script in background
    toolbox run -c "$TOOLBOX_NAME" python3 "$SCRIPT" &
done
