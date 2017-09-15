import atexit
import json
import logging
from flask import Flask, request
from monitor import *
from winreg import HKEY_LOCAL_MACHINE, KEY_READ, KEY_WRITE, REG_DWORD
from winreg import OpenKey, CloseKey, QueryValueEx, SetValueEx


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

with open('settings.json') as f:
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

    def destroy_monitors():
        for monitor, brightness, contrast in monitors:
            set_monitor_brightness(monitor, brightness[2])
            set_monitor_contrast(monitor, contrast[2])
            destroy_physical_monitor(monitor)

    atexit.register(destroy_monitors)

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

    # test if gamma ramp is supported

    try:
        gamma_ramp = get_device_gamma_ramp(device)
        set_device_gamma_ramp(device, gamma_ramp)
    except Exception as e:
        # device does not support gamma ramp
        gamma_ramp = None
        raise e

    # device supports gamma ramp

    def reset_gamma_ramp():
        if gamma_ramp is not None:
            set_device_gamma_ramp(device, gamma_ramp)

    atexit.register(reset_gamma_ramp)

    mat_monitorgamma = settings.get('mat_monitorgamma')
    mat_monitorgamma_tv_enabled = settings.get('mat_monitorgamma_tv_enabled')

    if mat_monitorgamma_tv_enabled:
        gamma = 2.5 / mat_monitorgamma
        remap = (16, 235)
    else:
        gamma = 2.2 / mat_monitorgamma
        remap = (0, 255)

    # now test if the device supports the full gamma range that is required

    def test_gamma_ramp():
        set_gamma_ramp(device, gamma, 0.0, remap)
        set_gamma_ramp(device, gamma, 1.0, remap)

    try:
        test_gamma_ramp()
    except Exception as e:
        def open_key(access):
            return OpenKey(HKEY_LOCAL_MACHINE,
                           r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\ICM',
                           access=access)

        key = open_key(KEY_READ)
        gamma_range = QueryValueEx(key, 'GdiIcmGammaRange')[0]
        CloseKey(key)

        try:
            if gamma_range == 256:
                # gamma range is already at maximum
                raise e

            # set to gamma range to 256 and repeat test

            try:
                key = open_key(KEY_WRITE)
            except PermissionError:
                print('Gamma range is currently limited. Please restart with '
                      'admin privileges in order to set it to maximum range!')
                exit()

            SetValueEx(key, 'GdiIcmGammaRange', 0, REG_DWORD, 256)
            CloseKey(key)

            def reset_gamma_range():
                key = open_key(KEY_WRITE)
                SetValueEx(key, 'GdiIcmGammaRange', 0, REG_DWORD, gamma_range)
                CloseKey(key)

            atexit.register(reset_gamma_range)

            test_gamma_ramp()
        except:
            raise RuntimeError(
                'Device does not support the full gamma range') from e

    # device supports full range gamma ramp

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
else:
    raise ValueError('invalid method "{}"'.format(method))

print('Running on http://127.0.0.1:{}/ (Press CTRL+C to quit)'.format(port))

app.run(port=port)
