# Copyright (C) 2023  Stavros Korokithakis
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import argparse
import re
import statistics
import subprocess
import sys
import time
from typing import List
from typing import Optional

import evdev
from evdev import ecodes

# I, Steven, am adding the following
# ADD TO EXISTING IMPORTS
import numpy as np
import sys
import tty
import termios
from datetime import datetime
import os
import json

# ====== NEW CONSTANTS for weiibal ======
KG_TO_LBS = 2.20462
SENSOR_ORDER = ["TL", "TR", "BL", "BR"]  # For clarity

TERSE = False

def wait_for_space():
    """Wait for SPACE key press without root privileges"""
    print("\n\aPress SPACE to begin measurement...", file=sys.stderr, end='', flush=True)

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch == ' ':
                break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    print()  # Newline after input


def debug(message: str, force: bool = False) -> None:
    if force or not TERSE:
        print(message)


def get_board_device() -> Optional[evdev.InputDevice]:
    """Return the Wii Balance Board device."""
    devices = [
        path
        for path in evdev.list_devices()
        if evdev.InputDevice(path).name == "Nintendo Wii Remote Balance Board"
    ]
    if not devices:
        return None

    board = evdev.InputDevice(
        devices[0],
    )
    return board

def get_raw_measurement(device: evdev.InputDevice) -> tuple:
    """Return raw sensor values (TL, TR, BL, BR) in kg"""
    data = [None] * 4
    while True:
        event = device.read_one()
        if event is None:
            continue

        if event.code == ecodes.ABS_HAT1X:  # TL
            data[0] = event.value / 100
        elif event.code == ecodes.ABS_HAT0X:  # TR
            data[1] = event.value / 100
        elif event.code == ecodes.ABS_HAT1Y:  # BL
            data[2] = event.value / 100
        elif event.code == ecodes.ABS_HAT0Y:  # BR
            data[3] = event.value / 100
        elif event.code == ecodes.SYN_REPORT and event.value == 0:
            if None not in data:
                return tuple(data)
            data = [None] * 4
        # Keep existing error handling
        elif event.code == ecodes.BTN_A:
            sys.exit("ERROR: User pressed board button while measuring, aborting.")
        elif event.code == ecodes.SYN_DROPPED:
            pass

def read_data(device: evdev.InputDevice, samples: int, threshold: float) -> list:
    """Collect raw sensor data with keyboard trigger"""
    #print("\n\aPress SPACE when ready to measure...", file=sys.stderr)
    wait_for_space()  # <-- Changed from keyboard.wait() 

    sensor_readings = []
    while len(sensor_readings) < samples:
        measurement = get_raw_measurement(device)
        if measurement is None:
            continue
            
        current_weight = sum(measurement)
        if len(sensor_readings) > 0 and current_weight < threshold:
            break
            
        sensor_readings.append(measurement)
        
    device.close()
    return sensor_readings

# ====== NEW ANALYSIS FUNCTIONS ======
def calculate_metrics(sensor_readings: list) -> dict:
    """Calculate weight distribution metrics with difference percentages"""
    tl, tr, bl, br = np.array(sensor_readings).T
    totals = tl + tr + bl + br
    total_weight = np.median(totals)  # Median total weight

    # Left/Right calculation
    left = tl + bl
    right = tr + br
    lr_diff = np.median(left - right)
    lr_side = "Left" if lr_diff > 0 else "Right"
    lr_diff_abs = abs(lr_diff)
    lr_diff_percent = (lr_diff_abs / total_weight) * 100  # New percentage calculation

    # Front/Back calculation
    front = tl + tr
    back = bl + br
    fb_diff = np.median(front - back)
    fb_side = "Front" if fb_diff > 0 else "Back"
    fb_diff_abs = abs(fb_diff)
    fb_diff_percent = (fb_diff_abs / total_weight) * 100  # New percentage calculation

    return {
        'weight_kg': total_weight,
        'left_right_diff': lr_diff_abs,
        'front_back_diff': fb_diff_abs,
        'lr_diff_percent': lr_diff_percent,
        'fb_diff_percent': fb_diff_percent,
        'lr_side': lr_side,
        'fb_side': fb_side
    }

def format_output(metrics: dict, use_lbs: bool = False) -> dict:
    """Format output with difference percentages"""
    conversions = {}
    if use_lbs:
        conversions = {
            'weight': metrics['weight_kg'] * KG_TO_LBS,
            'lr_diff': metrics['left_right_diff'] * KG_TO_LBS,
            'fb_diff': metrics['front_back_diff'] * KG_TO_LBS,
            'unit': 'lbs'
        }
    else:
        conversions = {
            'weight': metrics['weight_kg'],
            'lr_diff': metrics['left_right_diff'],
            'fb_diff': metrics['front_back_diff'],
            'unit': 'kg'
        }

    return {
            "timestamp": datetime.now().isoformat(timespec='seconds'),
            "units": conversions['unit'],
            "total_weight": round(conversions['weight'], 2),
            "planes": {
                "coronal": {
                    "increased_weight": metrics["lr_side"],
                    "value": round(conversions["lr_diff"], 2),
                    "percentage": round(metrics['lr_diff_percent'],1),
                    },
                "saggital": {
                    "increased_weight": metrics['fb_side'],
                    "value": round(conversions['fb_diff'], 2),
                    "percentage": round(metrics['fb_diff_percent'],1)
                    }
                }
            }

def measure_weight(args) -> float:
    """Perform one weight measurement."""

    if args.disconnect_when_done and not re.match(
        r"^([0-9a-f]{2}[:]){5}([0-9a-f]{2})$", args.disconnect_when_done, re.IGNORECASE
    ):
        sys.exit("ERROR: Invalid device address to disconnect specified.")

    debug("Waiting for balance board...")
    while not args.fake:
        board = get_board_device()
        if board:
            break
        time.sleep(0.5)

    debug("\aBalance board found, please step on.")

    if args.fake:
        weight_data = [85.2] * args.samples
    else:
        weight_data = read_data(board, args.samples, threshold=args.minlimit)

    sensor_readings = weight_data
    metrics = calculate_metrics(sensor_readings)
    metrics['weight_kg'] += args.adjust

    if args.weight_only:
        debug(f"{metrics['weight_kg']:.1f}", force=True)
        return metrics['weight_kg']

    data = format_output(metrics, use_lbs=(args.units == "lbs"))

    if args.json:
        print(json.dumps(data, indent=4))
        if args.save:
            visit_path = os.environ.get("VISIT_PATH")
            if not visit_path:
                sys.exit("❌ VISIT_PATH not set. Cannot save.")

            weiibal_dir = os.path.join(visit_path, "weiibal")
            os.makedirs(weiibal_dir, exist_ok=True)

            timestamp = data['timestamp'].replace(":", "-")
            outfile = os.path.join(weiibal_dir, f"{timestamp}.json")
            with open(outfile, "w") as f:
                json.dump(data, f, indent=4)

            if args.print:
                print(json.dumps(data, indent=4))
    else:
        print("This will eventually be human readable output")

    if args.disconnect_when_done:
        debug("Disconnecting...")
        subprocess.run(
            ["/usr/bin/env", "bluetoothctl", "disconnect", args.disconnect_when_done],
            capture_output=True,
        )

    if args.command:
        subprocess.run(
            args.command.replace("{weight}", f"{metrics['weight_kg']:.1f}"),
            shell=True,
        )

    return metrics["weight_kg"]



def cli():
    parser = argparse.ArgumentParser(
        description="Advanced Wii Balance Board Analyzer"
    )
    parser.add_argument(
        "-a",
        "--adjust",
        help="adjust the final weight by some value (e.g. to match some other scale,"
        " or to account for clothing)",
        type=float,
        default=0,
    )
    parser.add_argument(
    "--minlimit",
    type=float,
    default=20.0,  # Your original value
    help="Minimum weight threshold to start measurement (kg)"
    )
    parser.add_argument(
        "-c",
        "--command",
        help="the command to run when done (use `{weight}` to pass the weight "
        "to the command",
        type=str,
        metavar="COMMAND",
        default="",
    )
    parser.add_argument(
        "-d",
        "--disconnect-when-done",
        help="disconnect the board when done, so it turns off",
        type=str,
        metavar="ADDRESS",
        default="",
    )
    parser.add_argument(
        "-w",
        "--weight-only",
        action="store_true",
        help="only print the final weight",
    )
    parser.add_argument(
        '--units',
        choices=['kg', 'lbs'],
        default='kg',
        help='Measurement units (default: kg)'
    )
    parser.add_argument(
        '--samples',
        type=int,
        default=200,
        help='Number of samples to collect (default: 200)'
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output measurement as json to stdout"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save measurement to visit folder (Requires $VISIT_PATH to be set!)"
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Also print json when using --save"
    )
    parser.add_argument("--fake", action="store_true", help="Use simulated input data")



    args = parser.parse_args()

    if args.weight_only:
        global TERSE
        TERSE = True

    measure_weight(args)


if __name__ == "__main__":
    cli()
