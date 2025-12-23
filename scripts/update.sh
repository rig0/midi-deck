#!/bin/bash

git clone https://github.com/rig0/midi-deck.git temp
cp -R temp/* ../
rm -R -f temp
