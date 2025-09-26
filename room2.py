import RPi.GPIO as GPIO
import time
import pygame
import os
import threading

class RelayAudioController:
    def __init__(self, relay_pins, audio_files):
        self.RELAY_PINS = relay_pins
        self.AUDIO_FILES = audio_files

        # State
        self.running = False
        self.paused = False
        self.current_step = 0
        self.restart_step = False

        # Thread
        self.sequence_thread = None

        # GPIO setup
        GPIO.setmode(GPIO.BCM)
        for pin in self.RELAY_PINS:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH)  # relays off

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
        """Run a single step"""
        self.current_step = step
        while True:
            if self.paused:
                time.sleep(0.1)
                continue

            if self.restart_step:
                self.restart_step = False
                print(f"Step {step} restarting")

            # Turn on current relay, turn off others
            for i, pin in enumerate(self.RELAY_PINS):
                GPIO.output(pin, GPIO.LOW if i == step-1 else GPIO.HIGH)

            print(f"Step {step}: Light {step} + Audio {step}")
            self.play_audio(self.AUDIO_FILES[step-1])
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
        self.current_step = 0

    def start_or_resume(self):
        """Start or resume the sequence"""
        if not self.running:
            self.sequence_thread = threading.Thread(target=self.run_sequence)
            self.sequence_thread.start()
        else:
            if self.paused:
                print(f"Resuming step {self.current_step}")
                self.paused = False
                self.restart_step = True
                pygame.mixer.music.unpause()
            else:
                print(f"Already running step {self.current_step}")

    def pause(self):
        if self.running and not self.paused:
            print(f"Pausing at step {self.current_step}")
            self.paused = True
            pygame.mixer.music.pause()
            for pin in self.RELAY_PINS:
                GPIO.output(pin, GPIO.HIGH)

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

    controller = RelayAudioController(RELAY_PINS, AUDIO_FILES)

    print("Controls: '1' = Start/Resume, '2' = Pause, '9' = Exit.")

    try:
        while True:
            key = input("Enter command: ").strip()
            if key == '1':
                controller.start_or_resume()
            elif key == '2':
                controller.pause()
            elif key == '9':
                print("Exiting program...")
                break
            else:
                print("Invalid input. Press '1' to start/resume, '2' to pause, '9' to exit.")
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received. Exiting...")
    finally:
        controller.cleanup()
