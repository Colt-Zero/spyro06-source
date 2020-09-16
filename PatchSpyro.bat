set originalISO=%~1

if NOT "%originalISO%"=="" goto :buildISO
goto eof

:buildISO

cd /d %~dp0
py -3.6 spyro_patcher.py "%originalISO%"
pause

:eof