import RPi.GPIO as GPIO
import time
import pygame
import threading
import sys
import termios
import tty

try:
    from config_local import RELAY_SCHEDULE, ACTUATOR_SCHEDULE, AUDIO_FILE, LIGHTS_ON_DURATION
    print("Loaded local override config.")
except ImportError:
    from config_default import RELAY_SCHEDULE, AUDIO_FILE
    ACTUATOR_SCHEDULE = []
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

def build_actuator_steps(actuator_schedule):
    if not actuator_schedule:
        return []

    steps = []
    for act in actuator_schedule:
        name = act.get("name", f"actuator_{act['extend_pin']}_{act['retract_pin']}")
        expand_start = act["expand_time"]
        contract_start = act["contract_time"]

        if contract_start <= expand_start:
            raise ValueError(
                f"Actuator '{name}': contract_time ({contract_start}s) must be "
                f"after expand_time ({expand_start}s)."
            )

        # Default: extend relay runs until it's time to retract (self-stops
        # at full travel via the limit switch well before that, if it gets there first).
        expand_end = act.get("expand_duration")
        expand_end = expand_start + expand_end if expand_end is not None else contract_start

        if expand_end > contract_start:
            raise ValueError(
                f"Actuator '{name}': expand window ends at {expand_end}s, which is "
                f"after contract_time ({contract_start}s). Extend and retract relays "
                "must never be active at the same time."
            )

        # Default: retract relay runs until the end of the sequence (self-stops
        # at full travel via the limit switch); cleanup/stop_sequence will cut
        # power to it regardless.
        contract_duration = act.get("contract_duration")
        contract_end = contract_start + contract_duration if contract_duration is not None else float("inf")

        steps.append({
            "type": "actuator",
            "role": "extend",
            "name": name,
            "pin": act["extend_pin"],
            "on_time": expand_start,
            "off_time": expand_end,
        })
        steps.append({
            "type": "actuator",
            "role": "retract",
            "name": name,
            "pin": act["retract_pin"],
            "on_time": contract_start,
            "off_time": contract_end,
        })
    return steps


class TimedRoomController:
    def __init__(self, relay_schedule, actuator_schedule, audio_file, lights_on_duration=60):
        # Tag light steps explicitly so we can tell them apart from actuator steps later.
        light_steps = [dict(step, type="light") for step in relay_schedule]
        actuator_steps = build_actuator_steps(actuator_schedule)

        self.gpio_schedule = light_steps + actuator_steps
        self.audio_file = audio_file
        self.lights_on_duration = lights_on_duration

        self.running = False
        self.thread = None

        # GPIO setup
        GPIO.setmode(GPIO.BCM)
        for step in self.gpio_schedule:
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

        # After audio ends, only the LIGHT pins go on
        if self.running:
            light_pins = [s["pin"] for s in self.gpio_schedule if s["type"] == "light"]
            print(f"All lights ON for {self.lights_on_duration} seconds...")
            for pin in light_pins:
                GPIO.output(pin, GPIO.LOW)
            for _ in range(self.lights_on_duration):
                if not self.running:
                    break
                time.sleep(1)
            print("Turning all lights OFF")
            for pin in light_pins:
                GPIO.output(pin, GPIO.HIGH)
        for step in self.gpio_schedule:
            if step["type"] == "actuator":
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
            if step["type"] != "light":
                continue
            GPIO.output(step["pin"], GPIO.LOW if state_on else GPIO.HIGH)

    def cleanup(self):
        self.stop_sequence()
        pygame.mixer.quit()
        GPIO.cleanup()
        print("Cleanup complete. Exiting.")


if __name__ == "__main__":
    controller = TimedRoomController(RELAY_SCHEDULE, ACTUATOR_SCHEDULE, AUDIO_FILE, LIGHTS_ON_DURATION)

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
            elif key.lower() == "q":
                print("Quit key pressed. Exiting...")
                break
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received. Exiting...")
    finally:
        controller.cleanup()
