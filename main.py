# Button + 2 LED + Audio + Play/Pause
# 2 leds hooked up to relay 
# Controlled by physical button
# Audio 1 turns on with light 1; audio 2 with light 2
# Pause - turn off led and audio
# Play restarts current audio (step)

import RPi.GPIO as GPIO
import time
import pygame
import os
import threading

# GPIO pins
RELAY1_PIN = 5
RELAY2_PIN = 6
BUTTON_PIN = 21

# Audio files
AUDIO_FILE1 = os.path.expanduser("~/Desktop/Test.wav")
AUDIO_FILE2 = os.path.expanduser("~/Desktop/test2.wav")

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY1_PIN, GPIO.OUT)
GPIO.setup(RELAY2_PIN, GPIO.OUT)
GPIO.output(RELAY1_PIN, GPIO.HIGH)
GPIO.output(RELAY2_PIN, GPIO.HIGH)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Pygame audio
pygame.mixer.init()

# Global flags
running = False
paused = False
current_step = 1
sequence_thread = None
restart_step = False
step_done = {1: False, 2: False}

def play_audio(file_path):
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        if paused:
            pygame.mixer.music.stop()
            return  # stop immediately on pause
        time.sleep(0.1)

def run_step(step):
    """Run a single step, restarting it if requested."""
    global paused, restart_step

    while True:
        if paused:
            time.sleep(0.1)
            continue
        if restart_step:
            restart_step = False
            print(f"Step {step} restarting")
        # Execute step
        if step == 1:
            GPIO.output(RELAY1_PIN, GPIO.LOW)   # ON
            GPIO.output(RELAY2_PIN, GPIO.HIGH)  # OFF
            print("Step 1: Light 1 + Audio 1")
            play_audio(AUDIO_FILE1)
            if paused:
                continue
            time.sleep(2)
        elif step == 2:
            GPIO.output(RELAY1_PIN, GPIO.HIGH)  # OFF
            GPIO.output(RELAY2_PIN, GPIO.LOW)   # ON
            print("Step 2: Light 2 + Audio 2")
            play_audio(AUDIO_FILE2)
            if paused:
                continue
            time.sleep(2)
        break  # step fully done

def run_sequence():
    global running, current_step, paused, step_done, restart_step

    running = True
    while current_step <= 2:
        if not step_done[current_step]:
            restart_step = True
            run_step(current_step)
            if not paused:
                step_done[current_step] = True
                current_step += 1
        else:
            current_step += 1

    # Turn off lights at the end
    GPIO.output(RELAY1_PIN, GPIO.HIGH)
    GPIO.output(RELAY2_PIN, GPIO.HIGH)
    print("Sequence complete")
    running = False
    paused = False
    current_step = 1
    step_done[1] = False
    step_done[2] = False

def button_pressed():
    global running, paused, restart_step, sequence_thread

    if not running:
        # Start sequence
        sequence_thread = threading.Thread(target=run_sequence)
        sequence_thread.start()
    else:
        if not paused:
            # Pause sequence
            print(f"Paused at step {current_step}")
            paused = True
            GPIO.output(RELAY1_PIN, GPIO.HIGH)
            GPIO.output(RELAY2_PIN, GPIO.HIGH)
            pygame.mixer.music.stop()
        else:
            # Resume current step
            print(f"Resuming step {current_step}")
            paused = False
            restart_step = True  # restart only current step

GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=button_pressed, bouncetime=500)

print("Ready. Press button to start/pause/resume current step.")

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("Exiting...")
finally:
    GPIO.cleanup()
    pygame.mixer.quit()


