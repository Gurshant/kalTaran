import RPi.GPIO as GPIO
import time
import pygame
import os
import threading
import sys
import termios
import tty

# Function to read single key without Enter
def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

class RelayAudioController:
    def __init__(self, relay_pins, audio_files):
        self.RELAY_PINS = relay_pins
        self.AUDIO_FILES = audio_files

        self.running = False
        self.current_step = 0
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
        while pygame.mixer.music.get_busy() and self.running:
            time.sleep(0.1)
        pygame.mixer.music.stop()

    def run_sequence(self, start_step=1):
        self.running = True
        for step in range(start_step, len(self.RELAY_PINS) + 1):
            if not self.running:
                break

            self.current_step = step

            # Relay control: only current step ON
            for i, pin in enumerate(self.RELAY_PINS):
                GPIO.output(pin, GPIO.LOW if i == step - 1 else GPIO.HIGH)

            print(f"Step {step}: Light {step} + Audio {step}")
            self.play_audio(self.AUDIO_FILES[step - 1])
            time.sleep(0.1)

        self.current_step = 0
        self.running = False
        # Turn all off when sequence ends
        self.set_all_relays(False)

    def start(self, start_step=1):
        if not self.running:
            self.sequence_thread = threading.Thread(
                target=self.run_sequence, args=(start_step,)
            )
            self.sequence_thread.start()
        else:
            print(f"Already running step {self.current_step}")

    def stop_sequence(self):
        """Stop audio + relays + sequence thread."""
        if self.running:
            print("Stopping sequence...")
        self.running = False
        pygame.mixer.music.stop()
        self.set_all_relays(False)
        if self.sequence_thread and self.sequence_thread.is_alive():
            self.sequence_thread.join(timeout=0.5)

    def set_all_relays(self, state_on):
        """Set all relays ON (LOW) or OFF (HIGH)."""
        for pin in self.RELAY_PINS:
            GPIO.output(pin, GPIO.LOW if state_on else GPIO.HIGH)

    def cleanup(self):
        self.stop_sequence()
        pygame.mixer.quit()
        GPIO.cleanup()
        print("Cleanup complete. Exiting.")


if __name__ == "__main__":
    RELAY_PINS = [5, 13, 19]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    AUDIO_FILES = [
        os.path.join(script_dir, "room2", "test.wav"),
        os.path.join(script_dir, "room2", "test2.wav"),
        os.path.join(script_dir, "room2", "test3.wav"),
    ]

    controller = RelayAudioController(RELAY_PINS, AUDIO_FILES)

    print("Controls: '1-3' = Play from that step to end, '7' = All lights ON, "
          "'8' = All lights OFF, '9' = Play from start.")

    try:
        while True:
            key = getch()
            if key in ["1", "2", "3"]:
                controller.stop_sequence()
                controller.start(int(key))
            elif key == "7":
                print("Kill sequence + all lights ON")
                controller.stop_sequence()
                controller.set_all_relays(True)
            elif key == "8":
                print("Kill sequence + all lights OFF")
                controller.stop_sequence()
                controller.set_all_relays(False)
            elif key == "9":
                print("Kill everything and restart from step 1")
                controller.stop_sequence()
                controller.start(1)
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received. Exiting...")
    finally:
        controller.cleanup()
