import atexit
import json
import os
import platform
import sys
from aiohttp import web
from asyncio import get_event_loop, Future
from gamma import Context as GammaContext


if getattr(sys, 'frozen', False):
    class Excepthook:
        def __init__(self, excepthook):
            self.exception = False
            self.excepthook = excepthook

        def __call__(self, type, value, traceback):
            self.exception = True
            self.excepthook(type, value, traceback)

    excepthook = Excepthook(sys.excepthook)
    sys.excepthook = excepthook

    def exit_handler():
        if excepthook.exception:
            print('\n\nPress CTRL+C to quit...\n')

            try:
                from time import sleep

                while True:
                    sleep(1)
            except KeyboardInterrupt:
                pass

    atexit.register(exit_handler)

    def exit(*args, **kwargs):
        excepthook.exception = True
        sys.exit(*args, **kwargs)
else:
    exit = sys.exit

if platform.system() == 'Windows':
    import win32console, win32gui, win32con

    hwnd = win32console.GetConsoleWindow()

    if hwnd:
        hMenu = win32gui.GetSystemMenu(hwnd, False)

        if hMenu:
            win32gui.EnableMenuItem(hMenu, win32con.SC_CLOSE,
                                    win32con.MF_BYCOMMAND |
                                    win32con.MF_DISABLED |
                                    win32con.MF_GRAYED)

            def restore_close_button():
                win32gui.EnableMenuItem(hMenu, win32con.SC_CLOSE,
                                        win32con.MF_BYCOMMAND |
                                        win32con.MF_ENABLED)

            atexit.register(restore_close_button)


def extract(data, *keys, default=None):
    for key in keys:
        if not isinstance(data, dict) or key not in data:
            return default
        data = data[key]
    return data


if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
elif __file__:
    application_path = os.path.dirname(__file__)

print('PLEASE READ THE INSTRUCTIONS CAREFULLY!\n')

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
            f.write('[HKEY_LOCAL_MACHINE\{}]\n'.format(icm))
            f.write('"GdiIcmGammaRange"=')

            if gamma_range is None:
                f.write('-')
            else:
                f.write('dword:{:08x}'.format(gamma_range))

        with open(os.path.join(application_path,
                               'set_max_gamma_range.reg'), mode='w') as f:
            f.write('Windows Registry Editor Version 5.00\n\n')
            f.write('[HKEY_LOCAL_MACHINE\{}]\n'.format(icm))
            f.write('"GdiIcmGammaRange"=dword:{:08x}'.format(256))

        print('Gamma range is currently limited. To fix that, please\n'
              '    (1) run set_max_gamma_range.reg, then\n'
              '    (2) reboot PC for it to take effect!')
        exit()


print("Don't forget to set the launch option -nogammaramp!\n")

print("Don't forget to disable f.lux!")
print("Don't forget to disable Redshift!")
print("Don't forget to disable Windows Night Light!")
print("Don't forget to disable Xbox DVR/Game bar!\n")

print("In case you get an error:\n"
      "    Did you restart your PC after running set_max_gamma_range.reg?\n")


def adjust_brightness(flashed):
    a = remap[0] / 256
    b = (remap[1] + 1 - remap[0]) / 256

    if flashed == 0:
        def func(x):
            return a + pow(x, gamma) * b
    elif flashed == 255:
        def func(x):
            return a
    else:
        c = flashed / 255
        s = (1 - c) / (1 + c)

        def func(x):
            return a + pow(x * s, gamma) * b

    context.set(func)


future = Future()
future.set_result(None)


async def adjust_brightness_async(flashed):
    global future

    await future
    future = Future()

    async def task():
        adjust_brightness(flashed)
        future.set_result(None)

    get_event_loop().create_task(task())


async def handle(request):
    data = await request.json()

    state = extract(data, 'player', 'state')

    if state is None:
        await adjust_brightness_async(0)
    else:
        flashed = state['flashed']

        if flashed != extract(data, 'previously', 'player', 'state', 'flashed',
                              default=flashed):
            await adjust_brightness_async(flashed)

    return web.Response()


reset_gamma = settings.get('reset_gamma', False)

with open(settings_path, mode='w') as f:
    settings['reset_gamma'] = True
    json.dump(settings, f, indent=2, sort_keys=True)

context = GammaContext()


def restore_gamma():
    if reset_gamma:
        context.set_default()

    context.close(restore=not reset_gamma)

    if os.path.isfile(settings_path):
        with open(settings_path) as f:
            settings = json.load(f)

    with open(settings_path, mode='w') as f:
        settings['reset_gamma'] = False
        json.dump(settings, f, indent=2, sort_keys=True)


atexit.register(restore_gamma)

adjust_brightness(0)

print("Please exit with CTRL+C! "
      "If you don't, the gamma won't reset.\n")

app = web.Application()
app.router.add_post('/', handle)
web.run_app(app, host='127.0.0.1', port=port)
