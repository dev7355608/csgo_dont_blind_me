import atexit
import json
import os
import platform
import sys
from aiohttp import web
from gamma import Context as GammaContext


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


def extract(data, *keys, default=None):
    for key in keys:
        if not isinstance(data, dict) or key not in data:
            return default
        data = data[key]
    return data


print('Please read the instructions carefully!\n')

settings_path = os.path.join(application_path, 'settings.json')

if os.path.isfile(settings_path):
    with open(settings_path) as f:
        settings = json.load(f)
else:
    settings = dict(port=54237,
                    mat_monitorgamma=2,
                    mat_monitorgamma_tv_enabled=0)

    with open(settings_path, mode='w') as f:
        json.dump(settings, f, indent=2, sort_keys=True)

port = settings.get('port')

with open(os.path.join(application_path,
                       'gamestate_integration_dont_blind_me.cfg'), 'w') as f:
    f.write('''"csgo_dont_blind_me"
{{
    "uri" "http://127.0.0.1:{}"
    "timeout"   "1.0"
    "buffer"    "0.0"
    "throttle"  "0.0"
    "heartbeat" "300.0"
    "data"
    {{
        "player_id"    "1"
        "player_state" "1"
    }}
}}'''.format(port))

print("Don't forget to copy gamestate_integration_dont_blind_me.cfg into\n"
      "    ...\\Steam\\userdata\\________\\730\\local\\cfg, or\n"
      "    ...\\Steam\\steamapps\\common\\Counter-Strike Global Offensive\\"
      "csgo\\cfg!\n")

mat_monitorgamma = settings.get('mat_monitorgamma')
mat_monitorgamma_tv_enabled = settings.get('mat_monitorgamma_tv_enabled')

if mat_monitorgamma_tv_enabled:
    gamma = mat_monitorgamma / 2.5
    remap = (16, 235)
else:
    gamma = mat_monitorgamma / 2.2
    remap = (0, 255)

print("Don't forget to set your preferred gamma in settings.json! "
      "Currently set to:\n"
      "    mat_monitorgamma\t\t {:3.2f}\n"
      "    mat_monitorgamma_tv_enabled\t {}\n".format(
          mat_monitorgamma, int(mat_monitorgamma_tv_enabled)))


if platform.system() == 'Windows':
    from winreg import (HKEY_LOCAL_MACHINE, OpenKey, CloseKey,
                        QueryValueEx)

    icm = r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\ICM'
    key = None

    try:
        key = OpenKey(HKEY_LOCAL_MACHINE, icm)
        gamma_range = QueryValueEx(key, 'GdiIcmGammaRange')[0]
    except FileNotFoundError:
        gamma_range = None
    finally:
        if key is not None:
            CloseKey(key)

    if gamma_range != 256:
        with open(os.path.join(application_path,
                               'restore_gamma_range.reg'), mode='w') as f:
            f.write('Windows Registry Editor Version 5.00\n\n')
            f.write('[{}]\n'.format(icm))
            f.write('"GdiIcmGammaRange"=')

            if gamma_range is None:
                f.write('-')
            else:
                f.write('dword:{:08x}'.format(gamma_range))

        with open(os.path.join(application_path,
                               'set_max_gamma_range.reg'), mode='w') as f:
            f.write('Windows Registry Editor Version 5.00\n\n')
            f.write('[{}]\n'.format(icm))
            f.write('"GdiIcmGammaRange"=dword:{:08x}'.format(256))

        print('Gamma range is currently limited. To fix that, please\n'
              '    (1) run set_max_gamma_range.reg, then\n'
              '    (2) reboot PC for it to take effect!')
        sys.exit()


print("Don't forget to set the launch option -nogammaramp!\n")

print("Don't forget to disable f.lux!")
print("Don't forget to disable Redshift!")
print("Don't forget to disable Windows Night Light!\n")


def adjust_brightness(flashed):
    def func(x):
        y = x - flashed / 255

        if y <= 0:
            return 0

        return (remap[0] + pow(y, gamma) * (remap[1] + 1 - remap[0])) / 256

    context.set(func)


async def handle(request):
    data = await request.json()
    flashed = extract(data, 'player', 'state', 'flashed', default=0)

    if flashed != extract(data, 'previously', 'player', 'state', 'flashed',
                          default=flashed):
        adjust_brightness(flashed)

    return web.Response()


context = GammaContext()
atexit.register(context.close)
adjust_brightness(flashed=0)

app = web.Application()
app.router.add_post('/', handle)
web.run_app(app, host='127.0.0.1', port=port)
