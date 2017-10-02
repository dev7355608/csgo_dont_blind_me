@echo off
setlocal
set _CD=%CD%
cd /D %~dp0
rmdir /S /Q dist\csgo_dont_blind_me
pyinstaller --console --onefile -y --runtime-hook=hook.py app.py
mkdir dist\csgo_dont_blind_me
move /Y dist\app.exe dist\csgo_dont_blind_me
copy lock_gamma_range.reg dist\csgo_dont_blind_me
copy unlock_gamma_range.reg dist\csgo_dont_blind_me
cd %_CD%
