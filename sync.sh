#!/bin/sh

rm -f /tmp/.X99-lock

# Run Xvfb on display 0.
Xvfb :99 -screen 0 1280x720x16 &

export DISPLAY=:99

# Run python script
python sync.py "$1" "$2"