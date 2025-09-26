import RPi.GPIO as GPIO
import time
import pygame
import threading
import sys
import termios
import tty

try:
    from config_local import RELAY_SCHEDULE, AUDIO_FILE, LIGHTS_ON_DURATION
    print("Loaded local override config.")
except ImportError:
    from config_default import RELAY_SCHEDULE, AUDIO_FILE
    LIGHTS_ON_DURATION = 60  # default 1 minute
    print("Loaded default config.")

def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class TimedRoomController:
    def __init__(self, gpio_schedule, audio_file, lights_on_duration=60):
        self.gpio_schedule = gpio_schedule
        self.audio_file = audio_file
        self.lights_on_duration = lights_on_duration

        self.running = False
        self.thread = None

        # GPIO setup
        GPIO.setmode(GPIO.BCM)
        for step in gpio_schedule:
            GPIO.setup(step["pin"], GPIO.OUT)
            GPIO.output(step["pin"], GPIO.HIGH)

        # Setup audio
        pygame.mixer.init()

    def run_sequence(self):
        self.running = True
        start_time = time.time()
        for step in self.gpio_schedule:
            step["activated"] = False

        pygame.mixer.music.load(self.audio_file)
        pygame.mixer.music.play()

        while self.running and pygame.mixer.music.get_busy():
            elapsed = time.time() - start_time
            for step in self.gpio_schedule:
                pin = step["pin"]
                # Turn ON if within window
                if step["on_time"] <= elapsed < step["off_time"] and not step["activated"]:
                    GPIO.output(pin, GPIO.LOW)
                    step["activated"] = True
                # Turn OFF if past off_time
                if elapsed >= step["off_time"] and step.get("activated", False):
                    GPIO.output(pin, GPIO.HIGH)
                    step["activated"] = False
            time.sleep(0.01)

        # After audio ends, all lights ON for configured duration
        if self.running:
            print(f"All lights ON for {self.lights_on_duration} seconds...")
            for step in self.gpio_schedule:
                GPIO.output(step["pin"], GPIO.LOW)
            for _ in range(self.lights_on_duration):
                if not self.running:
                    break
                time.sleep(1)
            print("Turning all lights OFF")
            for step in self.gpio_schedule:
                GPIO.output(step["pin"], GPIO.HIGH)

        self.running = False

    def start(self):
        if not self.running:
            self.thread = threading.Thread(target=self.run_sequence)
            self.thread.start()
        else:
            print("Sequence already running")

    def stop_sequence(self):
        self.running = False
        pygame.mixer.music.stop()
        for step in self.gpio_schedule:
            GPIO.output(step["pin"], GPIO.HIGH)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)

    def set_all_relays(self, state_on):
        for step in self.gpio_schedule:
            GPIO.output(step["pin"], GPIO.LOW if state_on else GPIO.HIGH)

    def cleanup(self):
        self.stop_sequence()
        pygame.mixer.quit()
        GPIO.cleanup()
        print("Cleanup complete. Exiting.")


if __name__ == "__main__":
    controller = TimedRoomController(RELAY_SCHEDULE, AUDIO_FILE, LIGHTS_ON_DURATION)

    print("Controls: '7' = All lights ON, '8' = All lights OFF, '9'/'1' = Play from start")

    try:
        while True:
            key = getch()
            if key == "7":
                print("Kill sequence + all lights ON")
                controller.stop_sequence()
                controller.set_all_relays(True)
            elif key == "8":
                print("Kill sequence + all lights OFF")
                controller.stop_sequence()
                controller.set_all_relays(False)
            elif key in ["9", "1"]:
                print("Kill everything and restart from start")
                controller.stop_sequence()
                controller.start()
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received. Exiting...")
    finally:
        controller.cleanup()
