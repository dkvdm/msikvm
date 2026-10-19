#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["hidapi>=0.14"]
# ///
"""Switch the input source of MSI monitors over USB (the "MSI Gaming Controller" HID device).

Protocol (reverse-engineered by https://github.com/couriersud/msigd):
  64-byte HID report, report id 0x01, followed by an ASCII command terminated by '\\r'.
    get:  "58" + <setting>               -> reply "5b" + <setting> + <3-digit value>
    set:  "5b" + <setting> + <value>     -> reply "5600+" on success
  Setting "00500" is the input source.
"""

import argparse
import sys

import hid

VENDOR_ID = 0x1462
PRODUCT_ID = 0x3FA4
REPORT_SIZE = 64
TIMEOUT_MS = 1000

INPUT_SETTING = "00500"
INPUTS = {"hdmi1": 0, "hdmi2": 1, "dp": 2, "usbc": 3}
INPUT_NAMES = {v: k for k, v in INPUTS.items()}
ALIASES = {"displayport": "dp", "usb-c": "usbc", "typec": "usbc", "type-c": "usbc", "hdmi": "hdmi1"}


class MonitorError(Exception):
    pass


class Monitor:
    def __init__(self, path):
        self.dev = hid.device()
        self.dev.open_path(path)

    def close(self):
        self.dev.close()

    def command(self, cmd):
        # Leading 0x01 is the HID report id; pad to the full report size.
        payload = b"\x01" + cmd.encode("ascii") + b"\r"
        self.dev.write(payload.ljust(REPORT_SIZE + 1, b"\x00"))
        data = bytes(self.dev.read(REPORT_SIZE, TIMEOUT_MS))
        if not data:
            raise MonitorError(f"no reply to {cmd!r}")
        return data[1:].split(b"\r", 1)[0].replace(b"\x00", b"").decode("ascii", "replace")

    def get(self, setting):
        reply = self.command("58" + setting)
        prefix = "5b" + setting
        if not reply.startswith(prefix):
            raise MonitorError(f"unexpected reply {reply!r} for get {setting}")
        return reply[len(prefix):]

    def set(self, setting, value):
        reply = self.command("5b" + setting + value)
        if reply != "5600+":
            raise MonitorError(f"monitor rejected set {setting}={value} (reply {reply!r})")

    def get_input(self):
        raw = self.get(INPUT_SETTING)
        try:
            return INPUT_NAMES.get(int(raw), raw)
        except ValueError:
            return raw

    def set_input(self, name):
        self.set(INPUT_SETTING, f"{INPUTS[name]:03d}")


def find_devices():
    # Some platforms enumerate one entry per HID interface; keep the first per path.
    seen, devices = set(), []
    for d in hid.enumerate(VENDOR_ID, PRODUCT_ID):
        if d["path"] not in seen:
            seen.add(d["path"])
            devices.append(d)
    return devices


def normalize_input(name):
    name = name.lower()
    name = ALIASES.get(name, name)
    if name not in INPUTS:
        raise argparse.ArgumentTypeError(f"unknown input {name!r}; choose from {', '.join(INPUTS)}")
    return name


def open_monitor(index):
    devices = find_devices()
    if not devices:
        raise MonitorError("no MSI monitor found (USB 1462:3fa4). Is the monitor's USB upstream cable connected?")
    if index >= len(devices):
        raise MonitorError(f"monitor index {index} out of range ({len(devices)} found)")
    return Monitor(devices[index]["path"])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Switch MSI monitor input over USB.")
    parser.add_argument("-m", "--monitor", type=int, default=0, help="monitor index from 'list' (default 0)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list attached MSI monitors")
    sub.add_parser("get", help="print current input")
    p_set = sub.add_parser("set", help="switch input")
    p_set.add_argument("input", type=normalize_input, help=", ".join(INPUTS))
    p_toggle = sub.add_parser("toggle", help="toggle between two inputs (default: usbc <-> dp)")
    p_toggle.add_argument("a", nargs="?", type=normalize_input, default="usbc")
    p_toggle.add_argument("b", nargs="?", type=normalize_input, default="dp")
    p_raw = sub.add_parser("raw", help="read a raw setting code, e.g. 00150 (read-only)")
    p_raw.add_argument("setting")
    args = parser.parse_args(argv)

    try:
        if args.cmd == "list":
            for i, d in enumerate(find_devices()):
                print(f"{i}: {d['product_string']} serial={d['serial_number']}")
            return 0

        mon = open_monitor(args.monitor)
        try:
            if args.cmd == "get":
                print(mon.get_input())
            elif args.cmd == "set":
                mon.set_input(args.input)
            elif args.cmd == "toggle":
                target = args.b if mon.get_input() == args.a else args.a
                mon.set_input(target)
                print(target)
            elif args.cmd == "raw":
                print(mon.get(args.setting))
        finally:
            mon.close()
    except (MonitorError, OSError, IOError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
