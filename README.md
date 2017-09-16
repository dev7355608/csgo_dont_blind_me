# csgo_dont_blind_me

This app reduces the screen brightness when flashed in CS:GO.

I recommend that you get the [prebuilt binary](https://github.com/dev7355608/csgo_dont_blind_me/releases); then you don't need to install anything else. If don't want you run the prebuilt binary, you would obviously have to have Python 3 and Flask installed in order to get up and running.

  1. Copy *gamestate_integration_dont_blind_me.cfg* into
      - *...\\Steam\\userdata\\\_\_\_\_\_\_\_\_\\730\\local\\cfg*, or
      - *...\\Steam\\steamapps\\common\\Counter-Strike Global Offensive\\csgo\\cfg*.

  2. Set your preferred *mat_monitorgamma* and *mat_monitorgamma_tv_enabled* in *settings.json*.

  3. Add the launch option *-nogammaramp* to CS:GO.


- Make sure to disable [f.lux](https://justgetflux.com/)!
- Make sure to disable [Redshift](http://jonls.dk/redshift/)
- Make sure to disable Windows Night Light!
