set originalISO=%~1

if NOT "%originalISO%"=="" goto :buildISO
goto eof

:buildISO

cd /d %~dp0
"..\Spyro06 Patcher.exe" -extractmodels "%originalISO%"
pause

:eof