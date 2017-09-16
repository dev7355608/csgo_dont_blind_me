import atexit
import json
import logging
import os
import sys
from flask import Flask, request
from monitor import *
from winreg import (HKEY_LOCAL_MACHINE, KEY_READ, KEY_WRITE, REG_DWORD,
                    OpenKey, CloseKey, CreateKeyEx, QueryValueEx, SetValueEx)


if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)

    def press_any_key_to_exit():
        try:
            input('\nPress any key or CTRL+C to exit...\n')
        except KeyboardInterrupt:
            pass

    atexit.register(press_any_key_to_exit)
elif __file__:
    application_path = os.path.dirname(__file__)


def interpolate(value, minimum, maximum):
    return min(int(minimum + value * (maximum + 1 - minimum)), maximum)


def set_brightness(monitors, value):
    changed = False

    for monitor, brightness, contrast in monitors:
        new_brightness = interpolate(value, brightness[0], brightness[2])

        if new_brightness != brightness[1]:
            set_monitor_brightness(monitor, new_brightness)
            brightness[1] = new_brightness
            changed = True

    return changed


def set_contrast(monitors, value):
    changed = False

    for monitor, brightness, contrast in monitors:
        new_contrast = interpolate(value, contrast[0], contrast[2])

        if new_contrast != contrast[1]:
            set_monitor_contrast(monitor, new_contrast)
            contrast[1] = new_contrast
            changed = True

    return changed


def set_gamma_ramp(device, gamma, brightness=1.0, remap=(0, 255)):
    def f(x):
        y = pow(x / 256 * brightness, 1 / gamma)
        return int(256 * (remap[0] + y * (remap[1] + 1 - remap[0])))

    ramp = [[f(c) for c in range(256)] for i in range(3)]
    set_device_gamma_ramp(device, ramp)


def extract(data, *keys, default=None):
    for key in keys:
        if not isinstance(data, dict) or key not in data:
            return default
        data = data[key]
    return data


log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

with open(os.path.join(application_path, 'settings.json')) as f:
    settings = json.load(f)

app = Flask(__name__)

print('''Don't forget to copy gamestate_integration_dont_blind_me.cfg into
    ...\\Steam\\userdata\\________\\730\\local\\cfg, or
    ...\\Steam\\steamapps\\common\\Counter-Strike Global Offensive\\csgo\\cfg!
''')

print('All options are set in settings.json!\n')

port = settings.get('port')
method = settings.get('method').upper()

print('Active method: {}; available are GAMMA and DDC/CI.\n'.format(method))

if method == 'DDC/CI':
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

    def restore_and_destroy_monitors():
        for monitor, brightness, contrast in monitors:
            set_monitor_brightness(monitor, brightness[2])
            set_monitor_contrast(monitor, contrast[2])
            destroy_physical_monitor(monitor)

    atexit.register(restore_and_destroy_monitors)

    set_brightness(monitors, 1.0)
    set_contrast(monitors, 1.0)

    @app.route('/', methods=['POST'])
    def main():
        data = request.json
        f1 = extract(data, 'player', 'state', 'flashed', default=0)
        f0 = extract(data, 'previously', 'player', 'state', 'flashed',
                     default=f1)

        if f0 > 0 or f1 > 0:
            if f0 < f1:
                set_brightness(monitors, 0.0)
                set_contrast(monitors, 0.0)
            if f0 > f1:
                if f1 > 127:
                    set_contrast(monitors, 1.0 - (f1 - 128) / 127)
                elif not set_contrast(monitors, 1.0) or f1 == 0:
                    set_brightness(monitors, 1.0 - f1 / 127)

        return ''
elif method == 'GAMMA':
    device = get_dc()

    def release_device():
        release_dc(device)

    atexit.register(release_device)

    try:
        gamma_ramp = get_device_gamma_ramp(device)
        set_device_gamma_ramp(device, gamma_ramp)
        # device supports gamma ramp
    except Exception as e:
        # device does not support gamma ramp
        print('Error: Device does not support gamma ramp!')
        sys.exit()

    def restore_gamma_ramp():
        set_device_gamma_ramp(device, gamma_ramp)

    atexit.register(restore_gamma_ramp)

    mat_monitorgamma = settings.get('mat_monitorgamma')
    mat_monitorgamma_tv_enabled = settings.get('mat_monitorgamma_tv_enabled')

    if mat_monitorgamma_tv_enabled:
        gamma = 2.5 / mat_monitorgamma
        remap = (16, 235)
    else:
        gamma = 2.2 / mat_monitorgamma
        remap = (0, 255)

    def test_gamma_ramp():
        set_gamma_ramp(device, gamma, 0.0, remap)
        set_gamma_ramp(device, gamma, 1.0, remap)

    try:
        test_gamma_ramp()
    except Exception as e:
        icm = r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\ICM'

        try:
            key = None

            try:
                key = OpenKey(HKEY_LOCAL_MACHINE, icm, access=KEY_READ)
            except FileNotFoundError:
                key = CreateKeyEx(HKEY_LOCAL_MACHINE, icm, access=KEY_READ)

            try:
                gamma_range = QueryValueEx(key, 'GdiIcmGammaRange')[0]
            except FileNotFoundError:
                gamma_range = None
        finally:
            if key is not None:
                CloseKey(key)

        if gamma_range == 256:
            print('Error: Device does not support the full gamma range! '
                  '(or you haven\'t rebooted yet)')
            sys.exit()

        restore_gamma_ramp = os.path.join(application_path,
                                          'restore_gamma_range.reg')

        with open(restore_gamma_ramp, mode='w') as f:
            f.write('Windows Registry Editor Version 5.00\n\n')
            f.write('[{}]\n'.format(icm))
            f.write('"GdiIcmGammaRange"=')

            if gamma_range is None:
                f.write('-')
            else:
                f.write('dword:{:08x}'.format(gamma_range))

        try:
            key = None
            key = OpenKey(HKEY_LOCAL_MACHINE, icm, access=KEY_WRITE)
            SetValueEx(key, 'GdiIcmGammaRange', 0, REG_DWORD, 256)

            print('Gamma range is has been set to maximum. '
                  'Reboot PC for it to take effect!')
            sys.exit()
        except PermissionError:
            print('Gamma range is currently limited. Please restart app as '
                  'administrator in order to set it to maximum range!')
            sys.exit()
        finally:
            if key is not None:
                CloseKey(key)

    set_gamma_ramp(device, gamma, 1.0, remap)

    @app.route('/', methods=['POST'])
    def main():
        data = request.json
        f1 = extract(data, 'player', 'state', 'flashed', default=0)
        f0 = extract(data, 'previously', 'player', 'state', 'flashed',
                     default=f1)

        if f0 < f1:
            set_gamma_ramp(device, gamma, 0.0, remap)
        elif f0 > f1:
            set_gamma_ramp(device, gamma, 1.0 - f1 / 255, remap)

        return ''

    print('''Don't forget to set your preferred gamma! Currently set to:
    mat_monitorgamma\t\t {:3.2f}
    mat_monitorgamma_tv_enabled\t {}
'''.format(mat_monitorgamma, int(mat_monitorgamma_tv_enabled)))

    print('Don\'t forget to set the launch option -nogammaramp!\n')

    print('Don\'t forget to disable f.lux!')
    print('Don\'t forget to disable Redshift!')
    print('Don\'t forget to disable Windows Night Light!\n')
else:
    raise ValueError('invalid method "{}"'.format(method))

print('Running on http://127.0.0.1:{}/ (Press CTRL+C to quit)'.format(port))

app.run(port=port)
