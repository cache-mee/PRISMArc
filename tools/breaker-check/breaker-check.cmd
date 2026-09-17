@echo off
REM @author Samson Paul, samson.paul@experionglobal.com
setlocal
REM Windows launcher. Tries the official `py -3` launcher first, then `python`.
REM `python3` is deliberately not tried: on Windows it is usually a Microsoft Store
REM stub that opens the app page instead of running anything.
set "TOOL=%~dp0breaker-check.py"

py -3 -c "import sys" >nul 2>&1 && (py -3 "%TOOL%" %* & exit /b %errorlevel%)
python -c "import sys; sys.exit(0 if sys.version_info[0]==3 else 1)" >nul 2>&1 && (python "%TOOL%" %* & exit /b %errorlevel%)

echo breaker-check: no Python 3 found. >&2
echo   tried: py -3, python >&2
echo   install Python 3 from https://python.org and tick "Add Python to PATH" >&2
exit /b 127
