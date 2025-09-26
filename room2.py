import RPi.GPIO as GPIO
import time
import pygame
import os
import threading

class RelayAudioController:
    def __init__(self, relay_pins, audio_files, button_pin):
        self.RELAY_PINS = relay_pins
        self.AUDIO_FILES = audio_files
        self.BUTTON_PIN = button_pin

        # State flags
        self.running = False
        self.paused = False
        self.current_step = 1
        self.restart_step = False

        # Thread
        self.sequence_thread = None

        # GPIO setup
        GPIO.setmode(GPIO.BCM)
        for pin in self.RELAY_PINS:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH)  # relays off
        GPIO.setup(self.BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self.BUTTON_PIN, GPIO.FALLING, callback=self.button_pressed, bouncetime=500)

        # Pygame audio
        pygame.mixer.init()

    def play_audio(self, file_path):
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            if self.paused:
                pygame.mixer.music.stop()
                return
            time.sleep(0.1)

    def run_step(self, step):
        while True:
            if self.paused:
                time.sleep(0.1)
                continue

            if self.restart_step:
                self.restart_step = False
                print(f"Step {step} restarting")

            # Turn on the step's relay, turn off others
            for i, pin in enumerate(self.RELAY_PINS):
                GPIO.output(pin, GPIO.LOW if i == step-1 else GPIO.HIGH)

            print(f"Step {step}: Light {step} + Audio {step}")
            self.play_audio(self.AUDIO_FILES[step-1])
            if self.paused:
                continue
            time.sleep(2)
            break

    def run_sequence(self):
        self.running = True
        for step in range(1, len(self.RELAY_PINS)+1):
            self.restart_step = True
            self.run_step(step)
            if self.paused:
                break

        # Turn off all relays
        for pin in self.RELAY_PINS:
            GPIO.output(pin, GPIO.HIGH)
        print("Sequence complete")
        self.running = False
        self.paused = False
        self.current_step = 1

    def button_pressed(self, channel):
        if not self.running:
            self.sequence_thread = threading.Thread(target=self.run_sequence)
            self.sequence_thread.start()
        else:
            self.paused = not self.paused
            if self.paused:
                print(f"Paused at step {self.current_step}")
                pygame.mixer.music.pause()
                for pin in self.RELAY_PINS:
                    GPIO.output(pin, GPIO.HIGH)
            else:
                print(f"Resuming step {self.current_step}")
                pygame.mixer.music.unpause()
                self.restart_step = True

    def cleanup(self):
        # Turn off all relays
        for pin in self.RELAY_PINS:
            GPIO.output(pin, GPIO.HIGH)

        pygame.mixer.music.stop()
        pygame.mixer.quit()
        GPIO.cleanup()
        print("Cleanup complete. Exiting.")


if __name__ == "__main__":
    RELAY_PINS = [5, 13, 19]
    AUDIO_FILES = [
        os.path.expanduser("~/Desktop/Test.wav"),
        os.path.expanduser("~/Desktop/test2.wav"),
        os.path.expanduser("~/Desktop/test3.wav")
    ]
    BUTTON_PIN = 21

    controller = RelayAudioController(RELAY_PINS, AUDIO_FILES, BUTTON_PIN)

    print("Ready. Press button to start/pause/resume current step.")

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        controller.cleanup()
