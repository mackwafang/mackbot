@echo off

SETLOCAL
set WoWS_path=E:\Games\World_of_Warships
set mb_dir=D:\mackbot
set mb_gameparams_dir=%mb_dir%\WoWS-GameParams

echo Grabbing global.mo
FOR /F %%A in ('dir E:\Games\World_of_Warships\bin /O:-D /B') DO (
    set latest=%%A
    goto :loop_end
)
:loop_end


xcopy /Y %WoWS_path%\bin\%latest%\res\texts\en\LC_MESSAGES\global.mo %mb_dir%\mackbot\language\en\LC_MESSAGES\global.mo

echo Grabbing GameParams.data
%WoWS_path%\wowsunpack.exe -x %WoWS_path%\bin\%latest%\idx -p %WoWS_path%\res_packages -I content/GameParams.data -o %WoWS_path%\res_unpack
move /Y %WoWS_path%\res_unpack\content\GameParams.data %mb_gameparams_dir%\GameParams.data

echo Done

