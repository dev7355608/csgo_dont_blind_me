import os
import platform
import sys
import traceback
from aiohttp import web
from configobj import ConfigObj, get_extra_values, flatten_errors
from validate import Validator
from gamma import Context as GammaContext


def extract(data, *keys, default=None):
    for key in keys:
        if not isinstance(data, dict) or key not in data:
            return default
        data = data[key]
    return data


def resource_path(filename=None):
    try:
        base_path = sys._MEIPASS
    except:
        base_path = os.path.dirname(__file__)

    if filename is None:
        return base_path

    return os.path.join(base_path, filename)


class App:
    def __init__(self, path=None):
        if path is None:
            path = os.getcwd()

        res_path = resource_path()

        settings_path = os.path.join(path, 'settings.ini')
        default_settings_path = os.path.join(res_path, 'settings.ini.default')

        settings = ConfigObj(settings_path,
                             configspec=default_settings_path,
                             encoding='utf-8')
        settings.filename = settings_path

        validator = Validator()
        result = settings.validate(validator, preserve_errors=True, copy=True)

        for sections, key in get_extra_values(settings):
            section = settings

            for section_name in sections:
                section = section[section_name]

            del section[key]

        for sections, key, result in flatten_errors(settings, result):
            section = settings

            for section_name in sections:
                section = section[section_name]

            del section[key]

        assert settings.validate(validator, preserve_errors=False, copy=True)

        default_settings = ConfigObj(default_settings_path,
                                     configspec=default_settings_path,
                                     encoding='utf-8')
        default_settings.merge(settings)

        settings = default_settings
        settings.filename = settings_path
        settings.write()

        self.settings = settings

        self.host = settings['Game State Integration']['host']
        self.port = settings['Game State Integration'].as_int('port')

        gamestate_integration_cfg_template_path = os.path.join(
            res_path, 'gamestate_integration_dont_blind_me.cfg.template')

        with open(gamestate_integration_cfg_template_path) as f:
            gamestate_integration_cfg_template = f.read()

        gamestate_integration_cfg_path = os.path.join(
            path, 'gamestate_integration_dont_blind_me.cfg')

        with open(gamestate_integration_cfg_path, mode='w') as f:
            f.write(gamestate_integration_cfg_template.format(host=self.host,
                                                              port=self.port))

        self.mat_monitorgamma = settings['Video Settings'].as_float(
                'mat_monitorgamma')
        self.mat_monitorgamma_tv_enabled = settings['Video Settings'].as_bool(
                'mat_monitorgamma_tv_enabled')

        self.context = GammaContext.open()

    async def handle(self, request):
        data = await request.json()

        state = extract(data, 'player', 'state')

        if state is None:
            self.adjust_brightness(0)
        else:
            flashed = state['flashed']

            if flashed != extract(data, 'previously', 'player', 'state',
                                  'flashed', default=flashed):
                self.adjust_brightness(flashed)

        return web.Response()

    def adjust_brightness(self, flashed):
        if self.mat_monitorgamma_tv_enabled:
            gamma = self.mat_monitorgamma / 2.5
            remap = (16, 235)
        else:
            gamma = self.mat_monitorgamma / 2.2
            remap = (0, 255)

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

        self.context.set_ramp(func)

    def run(self):
        self.adjust_brightness(0)

        self.app = web.Application()
        self.app.router.add_post('/', self.handle)
        web.run_app(self.app, host=self.host, port=self.port)

    def close(self):
        self.context.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        app_path = os.path.dirname(sys.executable)
    elif __file__:
        app_path = os.path.dirname(__file__)

    print('PLEASE READ THE INSTRUCTIONS CAREFULLY!\n')

    print("Don't forget to copy gamestate_integration_dont_blind_me.cfg into\n"
          "    .../Steam/userdata/________/730/local/cfg or\n"
          "    .../Steam/steamapps/common/Counter-Strike Global Offensive"
          "/csgo/cfg!\n")

    print("Don't forget to set the launch option -nogammaramp!\n"
          "    (1) Go to the Steam library,\n"
          "    (2) right click on CS:GO and go to properties.\n"
          "    (3) Click 'Set Launch Options...' and add -nogammaramp.")

    if platform.system() == 'Windows':
        print("    (4) Run unlock_gamma_range.reg and restart PC.\n")
    else:
        print()

    print("To uninstall, \n"
          "    (1) delete gamestate_integration_dont_blind_me.cfg from cfg "
          "folder and\n"
          "    (2) remove the launch option -nogammaramp.")

    if platform.system() == 'Windows':
        print("    (3) Run lock_gamma_range.reg and restart PC.\n")
    else:
        print()

    print("Don't forget to disable f.lux!")
    print("Don't forget to disable Redshift!")
    print("Don't forget to disable Windows Night Light!")
    print("Don't forget to disable Xbox DVR/Game bar!\n")

    print("Don't forget to set your preferred settings in settings.ini!\n")

    try:
        with App(path=app_path) as app:
            print("Current settings:\n"
                  "    mat_monitorgamma\t\t {:3.2f}   (Brightness)\n"
                  "    mat_monitorgamma_tv_enabled\t {:d}      (Color Mode: "
                  "Computer Monitor 0, Television 1)\n".format(
                      app.mat_monitorgamma, app.mat_monitorgamma_tv_enabled))

            print("PLEASE CLOSE THE APP WITH CTRL+C!\n")

            app.run()
    except:
        traceback.print_exc()

        print('\n')

        if platform.system() == 'Windows':
            print("  - Did you run unlock_gamma_range.reg and restart PC?")

        print("  - Make sure your graphics card drivers are up to date.\n"
              "  - Make sure your operating system is up to date.\n"
              "  - Try disabling your integrated graphics card.")

        sys.exit(1)
