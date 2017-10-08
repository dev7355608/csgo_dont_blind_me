import os
import sys
import urllib.request
from aiohttp import web
from configobj import ConfigObj, get_extra_values, flatten_errors
from validate import Validator
from gamma import Context, generate_ramp


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

        self.temperature = [None, 6500]

        self.round_phase = None
        self.player_alive = None
        self.player_flashed = [None, 0]

        self.context = Context.open()

    async def handle(self, request):
        if request.method == 'GET':
            ct = request.query.get('ct')

            try:
                r, g, b = ct.split(',')
                r = float(r)
                g = float(g)
                b = float(b)
                ct = (r, g, b)
                assert r >= 0 and r <= 1.0
                assert g >= 0 and g <= 1.0
                assert b >= 0 and b <= 1.0
            except:
                try:
                    ct = int(ct)
                    assert ct >= 1000 and ct <= 25000
                except:
                    ct = self.temperature[1]

            self.temperature[1] = ct
        else:
            data = await request.json()
            provider_id = extract(data, 'provider', 'steamid')
            round_phase = extract(data, 'round', 'phase')
            player_id = extract(data, 'player', 'steamid')
            player_flashed = extract(data, 'player', 'state', 'flashes',
                                     default=0)

            self.round_phase = round_phase
            self.player_alive = player_id == provider_id
            self.player_flashed[1] = player_flashed

        self.update_brightness()
        return web.Response()

    def update_brightness(self):
        update = False

        if not self.player_alive or self.round_phase not in ('live', 'over'):
            update = self.temperature[0] != self.temperature[1]
            self.temperature[0] = self.temperature[1]

        if self.player_flashed[0] != self.player_flashed[1]:
            update = True
            self.player_flashed[0] = self.player_flashed[1]

        if not update:
            return

        if self.mat_monitorgamma_tv_enabled:
            gamma = self.mat_monitorgamma / 2.5
            minimum = 16 / 255
            maximum = 235 / 255
        else:
            gamma = self.mat_monitorgamma / 2.2
            minimum = 0.0
            maximum = 1.0

        flashed = self.player_flashed[0] / 255
        contrast = (1 - flashed) / (1 + flashed)

        ramp = generate_ramp(size=self.context.ramp_size, gamma=gamma,
                             contrast=contrast, minimum=minimum,
                             maximum=maximum, temperature=self.temperature[0])

        self.context.set_ramp(ramp)

    def run(self):
        self.update_brightness()

        self.app = web.Application()
        self.app.router.add_get('/', self.handle)
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

        with open(resource_path('VERSION'), encoding='utf-8') as f:
            current_version = f.readline().strip()

        try:
            latest_version = ''
            latest_version = urllib.request.urlopen(
                'https://raw.githubusercontent.com/dev7355608/'
                'csgo_dont_blind_me/master/VERSION', timeout=3).readline()
            latest_version = latest_version.decode('utf-8').strip()
        except:
            pass

        print('Current version:  {}'.format(current_version))
        print('Latest version:   {}\n'.format(latest_version))

        if latest_version and current_version != latest_version:
            print('UPDATE AVAILABLE at '
                  'github.com/dev7355608/csgo_dont_blind_me/releases!\n')

        print("PLEASE CLOSE THE APP WITH CTRL+C!\n")

        app.run()
