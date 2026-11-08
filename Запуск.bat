@echo off
cd /d "%~dp0"
where pyw >nul 2>&1 && start "" pyw "%~dp0app.py" && exit /b 0
where pythonw >nul 2>&1 && start "" pythonw "%~dp0app.py" && exit /b 0
start "" py "%~dp0app.py"
