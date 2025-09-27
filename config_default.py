import os

# Example imports for the StepRoomController
# Relay pin numbers for default setup
RELAY_PINS = [5, 13, 19]

# Audio files relative to this script
script_dir = os.path.dirname(os.path.abspath(__file__))
AUDIO_FILES = [
    os.path.join(script_dir, "room2", "test.wav"),
    os.path.join(script_dir, "room2", "test2.wav"),
    os.path.join(script_dir, "room2", "test3.wav"),
]

RELAY_SCHEDULE = [
    {"pin": 5, "on_time": 0, "off_time": 3},
    {"pin": 6, "on_time": 1, "off_time": 5},
    {"pin": 13, "on_time": 2, "off_time": 6},
]

# Audio file relative to this script
script_dir = os.path.dirname(os.path.abspath(__file__))
AUDIO_FILE = os.path.join(script_dir, "room2", "test.wav")

# How long all lights stay ON at the end (in seconds)
LIGHTS_ON_DURATION = 60
