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

        # State
        self.running = False
        self.paused = False
        self.current_step = 0
        self.restart_step = False
        self.skip_step = False

        # Thread
        self.sequence_thread = None

        # GPIO setup
        GPIO.setmode(GPIO.BCM)  # use BCM numbering
        for pin in self.RELAY_PINS:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH)  # relays off

        # Pygame audio
        pygame.mixer.init()

    def play_audio(self, file_path):
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            if self.paused or self.skip_step:
                pygame.mixer.music.stop()
                return
            time.sleep(0.1)

    def run_step(self, step):
        self.current_step = step
        while True:
            if self.paused:
                time.sleep(0.1)
                continue
            if self.skip_step:
                self.skip_step = False
                print(f"Skipping step {step}")
                break

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
            if self.paused or self.skip_step:
                continue

        # Turn off all relays
        for pin in self.RELAY_PINS:
            GPIO.output(pin, GPIO.HIGH)

        print("Sequence complete")
        self.running = False
        self.paused = False
        self.current_step = 0

    def start_or_resume(self):
        if not self.running:
            self.sequence_thread = threading.Thread(target=self.run_sequence)
            self.sequence_thread.start()
        elif self.paused:
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

    def skip(self):
        if self.running:
            print(f"Skipping step {self.current_step}")
            self.skip_step = True

    def cleanup(self):
        for pin in self.RELAY_PINS:
            GPIO.output(pin, GPIO.HIGH)
        pygame.mixer.music.stop()
        pygame.mixer.quit()
        GPIO.cleanup()
        print("Cleanup complete. Exiting.")
    
    def stop_sequence(self):
        """Stops the current sequence thread safely."""
        if self.sequence_thread and self.sequence_thread.is_alive():
            self.running = False
            self.paused = False
            self.restart_step = False
            self.skip_step = False
            self.sequence_thread.join(timeout=0.5)  # wait briefly for thread to finish

    def set_all_relays(self, state):
        """Set all relays ON (LOW) or OFF (HIGH)."""
        for pin in self.RELAY_PINS:
            GPIO.output(pin, GPIO.LOW if state else GPIO.HIGH)

    def play_from_step(self, start_step):
        """Play from a given step to the last step."""
        if start_step < 1 or start_step > len(self.RELAY_PINS):
            print(f"Invalid start step {start_step}")
            return

        self.running = True
        for step in range(start_step, len(self.RELAY_PINS)+1):
            self.current_step = step
            for i, pin in enumerate(self.RELAY_PINS):
                GPIO.output(pin, GPIO.LOW if i == step-1 else GPIO.HIGH)

            print(f"Step {step}: Light {step} + Audio {step}")
            self.play_audio(self.AUDIO_FILES[step-1])
            time.sleep(2)

        self.current_step = 0
        self.running = False


if __name__ == "__main__":
    RELAY_PINS = [5, 13, 19]
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    AUDIO_FILES = [
        os.path.join(script_dir, "room2", "test.wav"),
        os.path.join(script_dir, "room2", "test2.wav"),
        os.path.join(script_dir, "room2", "test3.wav")
    ]

    controller = RelayAudioController(RELAY_PINS, AUDIO_FILES)

    print("Controls: '1-3' = Play from that step to end, '7' = All lights ON, '8' = All lights OFF, '9' = Play from start.")

    try:
        while True:
            key = getch()
            if key in ['1', '2', '3']:
                step = int(key)
                controller.stop_sequence()
                controller.play_from_step(step)
            elif key == '7':
                print("Killing sequence and turning all lights ON")
                controller.stop_sequence()
                controller.set_all_relays(True)
            elif key == '8':
                print("Killing sequence and turning all lights OFF")
                controller.stop_sequence()
                controller.set_all_relays(False)
            elif key == '9':
                print("Killing everything and starting sequence from step 1")
                controller.stop_sequence()
                controller.start_or_resume()
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received. Exiting...")
    finally:
        controller.cleanup()
