import os

# Relay pin numbers for default setup
RELAY_PINS = [5, 13, 19]

# Audio files relative to this script
script_dir = os.path.dirname(os.path.abspath(__file__))
AUDIO_FILES = [
    os.path.join(script_dir, "room2", "test.wav"),
    os.path.join(script_dir, "room2", "test2.wav"),
    os.path.join(script_dir, "room2", "test3.wav"),
]
