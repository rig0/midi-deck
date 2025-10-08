#!/usr/bin/env bash

# Array of sink names and descriptions
declare -A SINKS=(
    [MainSink]="Main"
    [WebSink]="Web"
    [MusicSink]="Music"
    [DiscordSink]="Discord"
)

for sink in "${!SINKS[@]}"; do
    # check if sink already exists
    if ! pactl list short sinks | grep -q "^$sink"; then
        pactl load-module module-null-sink sink_name="$sink" sink_properties=device.description="${SINKS[$sink]}"
        echo "Created sink $sink"
    else
        echo "Sink $sink already exists"
    fi
done
