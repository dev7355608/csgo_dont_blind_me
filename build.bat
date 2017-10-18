@echo off
setlocal
set _CD=%CD%
cd /D %~dp0
rmdir /S /Q dist\csgo_dont_blind_me
pyinstaller --console --onefile -y --exclude-module=hook --runtime-hook=frozen.py --add-data=VERSION;. --add-data=settings.ini.default;. --add-data=gamestate_integration_dont_blind_me.cfg.template;. --add-data=INSTALL.txt;. app.py
mkdir dist\csgo_dont_blind_me
move /Y dist\app.exe dist\csgo_dont_blind_me
copy INSTALL.txt dist\csgo_dont_blind_me
copy lock_gamma_range.reg dist\csgo_dont_blind_me
copy unlock_gamma_range.reg dist\csgo_dont_blind_me
mkdir dist\csgo_dont_blind_me\hook
copy hook\hook.exe dist\csgo_dont_blind_me\hook
copy hook\hook32.dll dist\csgo_dont_blind_me\hook
copy hook\hook64.dll dist\csgo_dont_blind_me\hook
cd /D %_CD%
