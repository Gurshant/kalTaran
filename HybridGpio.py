import RPi.GPIO as _local_gpio
import pigpio

BCM = _local_gpio.BCM
BOARD = _local_gpio.BOARD
OUT = _local_gpio.OUT
IN = _local_gpio.IN
HIGH = 1
LOW = 0

MASTER = "master"

_slave_ips = {}       # target name -> ip address
_slave_conns = {}      # target name -> live pigpio.pi() connection (lazy)


def configure(slaves=None):
    """
    Call once, before setmode()/setup().
    slaves: dict mapping a target name (any string you choose, e.g. "slave")
            to that board's IP address, e.g. {"slave": "192.168.1.50"}.
    """
    global _slave_ips
    _slave_ips = dict(slaves or {})


def _resolve(pin):
    """Turn a bare int or (target, num) tuple into a (target, num) pair."""
    if isinstance(pin, tuple):
        target, num = pin
    else:
        target, num = MASTER, pin
    return target, num


def _get_conn(target):
    if target not in _slave_conns:
        if target not in _slave_ips:
            raise RuntimeError(
                f"hybrid_gpio: pin target '{target}' was used but was never "
                f"registered via configure(slaves={{...}})."
            )
        ip = _slave_ips[target]
        pi = pigpio.pi(ip)
        if not pi.connected:
            raise RuntimeError(
                f"hybrid_gpio: could not connect to pigpiod on '{target}' "
                f"({ip}). Check pigpiod is running there and reachable "
                f"on the network (port 8888)."
            )
        _slave_conns[target] = pi
    return _slave_conns[target]


def setmode(mode):
    _local_gpio.setmode(mode)
    # pigpio has no separate "mode" concept - it always uses BCM numbering.


def setup(pin, direction):
    target, num = _resolve(pin)
    if target == MASTER:
        _local_gpio.setup(num, direction)
    else:
        pi = _get_conn(target)
        pi.set_mode(num, pigpio.OUTPUT if direction == OUT else pigpio.INPUT)


def output(pin, value):
    target, num = _resolve(pin)
    if target == MASTER:
        _local_gpio.output(num, value)
    else:
        pi = _get_conn(target)
        pi.write(num, value)


def input(pin):
    target, num = _resolve(pin)
    if target == MASTER:
        return _local_gpio.input(num)
    pi = _get_conn(target)
    return pi.read(num)


def cleanup():
    _local_gpio.cleanup()
    for target, pi in _slave_conns.items():
        try:
            pi.stop()
        except Exception:
            pass
    _slave_conns.clear()