import os
import sys
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

    print('# csgo_dont_blind_me\n')
    print('-' * 80 + '\n')

    with open(resource_path('INSTALL.txt')) as f:
        print(f.read())

    print('-' * 80 + '\n')

    with App(path=app_path) as app:
        app.settings.write(sys.stdout.buffer)
        print('\n' + '-' * 80 + '\n')
        print("PLEASE CLOSE THE APP WITH CTRL+C!\n")

        app.run()
