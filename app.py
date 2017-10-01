import atexit
import json
import os
import platform
import sys
from aiohttp import web
from asyncio import get_event_loop, Future
from gamma import Context as GammaContext


class Excepthook:
    def __init__(self, excepthook, handler):
        self.excepthook = excepthook
        self.handler = handler

    def __call__(self, type, value, traceback):
        self.handler.exception = True
        self.excepthook(type, value, traceback)


class ExitHandler:
    def __init__(self, excepthook):
        self.excepthook = Excepthook(excepthook, self)
        self.exception = False
        self.confirm_exit = False
        self.confirm_exit_on_exception = False

    def __call__(self):
        if self.exception:
            print("\n\n"
                  " (1) Did you restart your PC after running "
                  "set_max_gamma_range.reg?\n"
                  " (2) Make sure your graphics card drivers are up to date.\n"
                  " (3) Make sure your operating system is up to date.\n"
                  " (4) Try disabling your integrated graphics card.")

        if self.confirm_exit or \
           self.exception and self.confirm_exit_on_exception:
            print('\n\nPress CTRL+C to quit...')

            try:
                from time import sleep

                while True:
                    sleep(1)
            except KeyboardInterrupt:
                pass


exit_handler = ExitHandler(sys.excepthook)
exit_handler.confirm_exit_on_exception = getattr(sys, 'frozen', False)
sys.excepthook = exit_handler.excepthook
atexit.register(exit_handler)


def exit(*args, **kwargs):
    if getattr(sys, 'frozen', False):
        exit_handler.confirm_exit = True

    sys.exit(*args, **kwargs)


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

print("Don't forget to copy gamestate_integration_dont_blind_me.cfg into "
      "either\n    ...\\Steam\\userdata\\________\\730\\local\\cfg or\n"
      "    ...\\Steam\\steamapps\\common\\Counter-Strike Global Offensive\\"
      "csgo\\cfg!\n")

print("Don't forget to set the launch option -nogammaramp!\n"
      "    (1) Go to the Steam library,\n"
      "    (2) right click on CS:GO and go to properties and\n"
      "    (3) click 'Set Launch Options...' and add -nogammaramp.\n")

print("To uninstall, \n"
      "    (1) remove gamestate_integration_dont_blind_me.cfg from the "
      "cfg folder and\n"
      "    (2) remove the launch option -nogammaramp and\n"
      "    (3) run restore_gamma_range.reg and restart PC if it exists.\n")

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
      "    mat_monitorgamma\t\t {:3.2f}    (Brightness)\n"
      "    mat_monitorgamma_tv_enabled\t {}       (Color Mode: "
      "Computer Monitor 0, Television 1)\n".format(
          mat_monitorgamma, int(mat_monitorgamma_tv_enabled)))

print("Don't forget to disable f.lux!")
print("Don't forget to disable Redshift!")
print("Don't forget to disable Windows Night Light!")
print("Don't forget to disable Xbox DVR/Game bar!\n")

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

    context.set_ramp(func)


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


print("Please close the app with CTRL+C! "
      "If you don't, the gamma won't reset.\n")

with GammaContext() as context:
    adjust_brightness(0)

    app = web.Application()
    app.router.add_post('/', handle)
    web.run_app(app, host='127.0.0.1', port=port)
