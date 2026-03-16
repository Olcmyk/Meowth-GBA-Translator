@echo off
REM Quick translation script
REM Usage: translate.bat <input.gba>

if "%~1"=="" (
    echo Usage: translate.bat ^<input.gba^>
    echo Example: translate.bat firered_en.gba
    pause
    exit /b 1
)

set INPUT=%~1
set BASENAME=%~n1
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set OUTPUT=outputs\%BASENAME%_zh_%TIMESTAMP%.gba

echo Translating: %INPUT%
echo Output: %OUTPUT%
echo.

python -m meowth full "%INPUT%" --output-dir outputs

echo.
echo Done! Check outputs folder.
pause
