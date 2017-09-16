# csgo_dont_blind_me

This app reduces the screen brightness when flashed in CS:GO.

I recommend that you get the [prebuilt binary](https://github.com/dev7355608/csgo_dont_blind_me/releases); then you don't need to install anything else. If don't want you run the prebuilt binary, you would obviously have to have Python 3 and Flask installed in order to get up and running.

Copy *gamestate_integration_dont_blind_me.cfg* into

 - *...\\Steam\\userdata\\\_\_\_\_\_\_\_\_\\730\\local\\cfg*, or
 - *...\\Steam\\steamapps\\common\\Counter-Strike Global Offensive\\csgo\\cfg*.

There are two methods available to reduce the brightness of a flash.

1. **Gamma** (default): This is the preferred method. It makes the flashes fully black as it adjusts the gamma ramp. For this to work, you have to set `mat_monitorgamma` and `mat_monitorgamma_tv_enabled` to your preferred values in *settings.json* and add the launch option *-nogammaramp* to CS:GO.

  - Make sure to disable [f.lux](https://justgetflux.com/)!
  - Make sure to disable Windows Night Light!


2. **DDC/CI** (legacy): Original implementation; it reduces the monitor brightness and contrast via
DDC/CI. But it doesn't get as dark as with the gamma method; also every DDC/CI call takes 50ms, hence the transition from flashed to normal is not very smooth.

Finally, you just have to start the app and launch CS:GO. Done!
