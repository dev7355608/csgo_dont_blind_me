# csgo_dont_blind_me

This app reduces the screen brightness when flashed in CS:GO.

If you are running *Windows*, I recommend that you get the [prebuilt binary](https://github.com/dev7355608/csgo_dont_blind_me/releases); then you don't need to install anything else. Otherwise, if you are on *Linux* or *macOS*, you would have to have Python 3.5+ and [aiohttp](http://aiohttp.readthedocs.io) installed in order to get up and running.

After launching the app for the first time, do as follows:

  1. Copy *gamestate_integration_dont_blind_me.cfg* into
      - *...\\Steam\\userdata\\\_\_\_\_\_\_\_\_\\730\\local\\cfg*, or
      - *...\\Steam\\steamapps\\common\\Counter-Strike Global Offensive\\csgo\\cfg*.

  2. Set your preferred *mat_monitorgamma* and *mat_monitorgamma_tv_enabled* in *settings.ini*.

  3. Add the launch option *-nogammaramp* to CS:GO.


- Make sure to disable [f.lux](https://justgetflux.com/)!
- Make sure to disable [Redshift](http://jonls.dk/redshift/)!
- Make sure to disable Windows Night Light!
- Make sure to disable Xbox DVR/Game bar!
