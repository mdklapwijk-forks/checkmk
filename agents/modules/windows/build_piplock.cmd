@rem Makes lock file
@rem be called only from exec_cmd.bat

@echo off
powershell Write-Host "Building piplock" -foreground cyan

if not defined install_dir powershell Write-Host "This script must be called using exec_cmd" -foreground red && exit /b 2
if not defined ready_dir powershell Write-Host "This script must be called using exec_cmd" -foreground red && exit /b 3
if not exist %install_dir% powershell Write-Host "%install_dir% doesnt exist" -foreground red && exit /b 4

mkdir %ready_dir% 2> nul
cd %ready_dir% || powershell Write-Host "Failed enter %ready_dir%" -foreground red && exit /b 5

set PIPENV_VENV_IN_PROJECT=true
%install_dir%\python.exe -m pipenv lock

powershell Write-Host "Pipfile is locked" -foreground green
