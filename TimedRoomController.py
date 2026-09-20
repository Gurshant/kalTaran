import RPi.GPIO as GPIO
import time
import pygame
import threading
import sys
import termios
import tty

try:
    import config_local as _cfg
    print("Loaded local override config.")
except ImportError:
    import config_default as _cfg
    print("Loaded default config.")

RELAY_SCHEDULE = _cfg.RELAY_SCHEDULE
AUDIO_FILE = _cfg.AUDIO_FILE
ACTUATOR_SCHEDULE = getattr(_cfg, "ACTUATOR_SCHEDULE", [])
LIGHTS_ON_DURATION = getattr(_cfg, "LIGHTS_ON_DURATION", 60)
FINALE_PIN = getattr(_cfg, "FINALE_PIN", None)

# Duration (seconds) for the manual extend-all / retract-all key commands.
MANUAL_ACTUATOR_DURATION = 10

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

        expand_end = act.get("expand_duration")
        expand_end = expand_start + expand_end if expand_end is not None else contract_start
        expand_end = min(expand_end, contract_start)  # never overlap with retract

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
    def __init__(self, relay_schedule, actuator_schedule, audio_file, lights_on_duration=60, finale_pin=None):
        light_steps = [dict(step, type="light") for step in relay_schedule]
        actuator_steps = build_actuator_steps(actuator_schedule)

        self.gpio_schedule = light_steps + actuator_steps
        self.actuator_schedule = actuator_schedule  # raw list, used by manual extend/retract-all controls
        self.audio_file = audio_file
        self.lights_on_duration = lights_on_duration
        self.finale_pin = finale_pin

        self.running = False
        self.thread = None

        self.actuator_thread = None
        self._actuator_cancel = threading.Event()

        # GPIO setup
        self.all_pins = {step["pin"] for step in self.gpio_schedule}
        if self.finale_pin is not None:
            self.all_pins.add(self.finale_pin)

        GPIO.setmode(GPIO.BCM)
        for pin in self.all_pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH)

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
            if self.finale_pin is not None:
                finale_pins = [self.finale_pin]
                print(f"Finale light ON for {self.lights_on_duration} seconds...")
            else:
                finale_pins = [s["pin"] for s in self.gpio_schedule if s["type"] == "light"]
                print(f"All lights ON for {self.lights_on_duration} seconds...")

            for pin in finale_pins:
                GPIO.output(pin, GPIO.LOW)
            for _ in range(self.lights_on_duration):
                if not self.running:
                    break
                time.sleep(1)
            print("Turning finale light(s) OFF")
            for pin in finale_pins:
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

    def _run_actuators(self, role, duration, cancel_event):
        pins = [
            act["extend_pin"] if role == "extend" else act["retract_pin"]
            for act in self.actuator_schedule
        ]
        opposite_pins = [
            act["retract_pin"] if role == "extend" else act["extend_pin"]
            for act in self.actuator_schedule
        ]

        for pin in opposite_pins:
            GPIO.output(pin, GPIO.HIGH)

        for pin in pins:
            GPIO.output(pin, GPIO.LOW)

        if not cancel_event.wait(duration):
            for pin in pins:
                GPIO.output(pin, GPIO.HIGH)

    def activate_actuators(self, role, duration=MANUAL_ACTUATOR_DURATION):
        if role not in ("extend", "retract"):
            raise ValueError("role must be 'extend' or 'retract'")
        if not self.actuator_schedule:
            print("No actuators configured.")
            return

        self._actuator_cancel = threading.Event()
        self.actuator_thread = threading.Thread(
            target=self._run_actuators, args=(role, duration, self._actuator_cancel)
        )
        self.actuator_thread.start()

    def stop_sequence(self):
        self.running = False
        self._actuator_cancel.set()  # cancel any in-flight manual actuator pulse
        pygame.mixer.music.stop()
        for pin in self.all_pins:
            GPIO.output(pin, GPIO.HIGH)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)
        if self.actuator_thread and self.actuator_thread.is_alive():
            self.actuator_thread.join(timeout=0.5)

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
    controller = TimedRoomController(
        RELAY_SCHEDULE, ACTUATOR_SCHEDULE, AUDIO_FILE, LIGHTS_ON_DURATION, finale_pin=FINALE_PIN
    )

    print(
        "Controls: '7' = All lights ON, '8' = All lights OFF, '9'/'1' = Play from start, '4' = All actuators EXTEND for {MANUAL_ACTUATOR_DURATION}s, '5' = All actuators RETRACT for {MANUAL_ACTUATOR_DURATION}s"
    )

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
            elif key == "4":
                print(f"Kill sequence + all actuators EXTEND for {MANUAL_ACTUATOR_DURATION}s")
                controller.stop_sequence()
                controller.activate_actuators("extend", MANUAL_ACTUATOR_DURATION)
            elif key == "5":
                print(f"Kill sequence + all actuators RETRACT for {MANUAL_ACTUATOR_DURATION}s")
                controller.stop_sequence()
                controller.activate_actuators("retract", MANUAL_ACTUATOR_DURATION)
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