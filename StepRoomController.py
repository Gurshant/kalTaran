import RPi.GPIO as GPIO
import time
import pygame
import threading
import sys
import termios
import tty

try:
    from config_local import RELAY_PINS, AUDIO_FILES, ALL_LIGHTS_ON_DURATION 
    print("Loaded local override config.")
except ImportError:
    from config_default import RELAY_PINS, AUDIO_FILES
    ALL_LIGHTS_ON_DURATION = 60  # default 1 minute

    print("Loaded default config.")

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

class StepRoomController:
    def __init__(self, relay_pins, audio_files, lights_on_duration=60):
        self.RELAY_PINS = relay_pins
        self.AUDIO_FILES = audio_files
        self.lights_on_duration = lights_on_duration

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
            time.sleep(0.2)
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
            time.sleep(0.2)

        self.current_step = 0

        # After last step: keep lights ON for 1 minute
        if self.running:  # only if not stopped manually
            print(f"All lights ON for {self.lights_on_duration} seconds...")
            self.set_all_relays(True)
            for _ in range(self.lights_on_duration):
                if not self.running:  # allow stop_sequence() to break
                    break
                time.sleep(1)
            print("Turning all lights OFF")
            self.set_all_relays(False)

        self.running = False

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

    controller = StepRoomController(RELAY_PINS, AUDIO_FILES, lights_on_duration=ALL_LIGHTS_ON_DURATION)

    print("Controls: '1-3' = Play from that step to end, '7' = All lights ON, '8' = All lights OFF, '9' = Play from start.")

    try:
        while True:
            key = getch()
            valid_keys = [str(i) for i in range(1, len(RELAY_PINS) + 1)]
            if key in valid_keys:
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
            elif key.lower() == "q":
                print("Quit key pressed. Exiting...")
                break
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received. Exiting...")
    finally:
        controller.cleanup()
