@echo off

wt ^
new-tab --title "NameServer" powershell.exe -NoExit -Command "python -m Pyro5.nameserver" ^
; new-tab --title "Gateway" -d "%~dp0gateway" powershell.exe -NoExit -Command "python gateway.py" ^
; new-tab --title "Barrel 1" -d "%~dp0barrel" powershell.exe -NoExit -Command "python barrel.py barrel1" ^
; new-tab --title "Barrel 2" -d "%~dp0barrel" powershell.exe -NoExit -Command "python barrel.py barrel2" ^
; new-tab --title "Downloader" -d "%~dp0downloader" powershell.exe -NoExit -Command "python downloader.py" ^
; new-tab --title "Client" -d "%~dp0client" powershell.exe -NoExit -Command "python client.py"