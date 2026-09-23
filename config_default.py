import os

# Example imports for the StepRoomController
# Relay pin numbers for default setup
RELAY_PINS = [5, 13, 19]


# --- Master / Slave GPIO boards -------------------------------------------
# Map a short name for each slave board to its IP address (must be running
# pigpiod - see hybrid_gpio.py header for the one-time setup commands).
# The master needs no entry here - it's always available as "master".
SLAVES = {
    "slave": "192.168.1.50",
}

# --- Pin addressing ---------------------------------------------------------
# Every pin below is either:
#   - a bare int, e.g. 5          -> pin 5 on the MASTER
#   - a ("target", num) tuple     -> pin `num` on that board (must be a key
#                                     in SLAVES above, or "master")
#
# This lets the SAME pin number be used on two different boards without
# colliding, e.g. 5 (master relay board) vs ("slave", 5) (slave relay board).

RELAY_SCHEDULE = [
    {"pin": 5, "on_time": 0, "off_time": 3},   # master, pin 5
    {"pin": 13, "on_time": 1, "off_time": 5},   # master, pin 13
    {"pin": ("slave", 5),  "on_time": 1, "off_time": 4},   # slave, pin 5 (different physical relay)
    {"pin": ("slave", 19), "on_time": 2, "off_time": 6},   # slave, pin 19
]

# --- Actuators ---
# Each actuator needs TWO pins: one that extends it, one that retracts it
# (a standard 2-relay reversing setup). Since these actuators have built-in
# limit switches that self-stop at full travel and stop itself
# ACTUATOR_SCHEDULE = [
#     {
#         "extend_pin": ("slave", 20),
#         "retract_pin": ("slave", 21),
#         "expand_time": 2.0,    # start extending 2s into the sequence
#         "contract_time": 8.0,  # start retracting 8s in (fully out well before this)
#         "expand_duration": 3.0,        # OPTIONAL - see below
#         "contract_duration": 3.0,      # OPTIONAL - see below
#     },
# ]

# Audio file relative to this script
AUDIO_FILE = os.path.join(script_dir, "audio", "room2", "part3.wav")
# How long all lights stay ON at the end (in seconds)
LIGHTS_ON_DURATION = 60

# Pin for the single light that turns on at the end of the sequence.
# If left as None, it falls back to turning on all
FINALE_PIN = 26