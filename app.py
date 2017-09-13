import atexit
import json
import logging
import os
import sys
from flask import Flask, request
from monitor import *


monitors = []

for monitor, primary in enum_display_monitors():
    if not primary:
        continue

    for monitor in get_physical_monitors(monitor):
        brightness = get_monitor_brightness(monitor)
        brightness = [brightness[0], brightness[1], brightness[1]]
        contrast = get_monitor_contrast(monitor)
        contrast = [contrast[0], contrast[1], contrast[1]]
        monitors.append((monitor, brightness, contrast))


def destroy_monitors():
    for monitor, brightness, contrast in monitors:
        set_monitor_brightness(monitor, brightness[2])
        set_monitor_contrast(monitor, contrast[2])
        destroy_physical_monitor(monitor)


atexit.register(destroy_monitors)


def interpolate(value, minimum, maximum):
    return min(int(minimum + value * (maximum - minimum) +
                   0.25 + 0.5 * value), maximum)


def set_brightness(value):
    changed = False

    for monitor, brightness, contrast in monitors:
        new_brightness = interpolate(value, brightness[0], brightness[2])

        if new_brightness != brightness[1]:
            set_monitor_brightness(monitor, new_brightness)
            brightness[1] = new_brightness
            changed = True

    return changed


def set_contrast(value):
    changed = False

    for monitor, brightness, contrast in monitors:
        new_contrast = interpolate(value, contrast[0], contrast[2])

        if new_contrast != contrast[1]:
            set_monitor_contrast(monitor, new_contrast)
            contrast[1] = new_contrast
            changed = True

    return changed


def resource_path(path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.getcwd()

    return os.path.realpath(os.path.join(base_path, path))


def extract(data, *keys, default=None):
    for key in keys:
        if not isinstance(data, dict) or key not in data:
            return default
        data = data[key]
    return data


log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

try:
    with open('settings.json') as f:
        settings = json.load(f)
except:
    try:
        with open(os.path.join(sys._MEIPASS, 'settings.json')) as f:
            settings = json.load(f)
    except:
        pass

port = settings.get('port')

app = Flask(__name__)


@app.route('/', methods=['POST'])
def main():
    data = request.json
    f1 = extract(data, 'player', 'state', 'flashed', default=0)
    f0 = extract(data, 'previously', 'player', 'state', 'flashed', default=f1)

    if f0 > 0 or f1 > 0:
        if f0 < f1:
            set_brightness(0)
            set_contrast(0)
        if f0 > f1:
            if f1 > 127:
                set_contrast((127 - (f1 - 128)) / 127)
            elif not set_contrast(1):
                set_brightness((127 - f1) / 127)

    return ''


print(' * Running on http://127.0.0.1:{}/ (Press CTRL+C to quit)'.format(port))

app.run(port=port)
