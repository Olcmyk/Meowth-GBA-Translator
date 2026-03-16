@echo off
REM Local build script for Windows GUI
REM Run this to create a distributable Windows package

echo ========================================
echo Meowth Translator - Local Build Script
echo ========================================
echo.

REM Clean previous builds
echo [1/5] Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist resources rmdir /s /q resources
echo Done.
echo.

REM Ensure only Windows armips.exe exists
echo [2/5] Preparing armips...
if exist tools\armips (
    del /q tools\armips
    echo Removed macOS armips binary
)
if not exist tools\armips.exe (
    echo ERROR: tools\armips.exe not found!
    echo Please build armips first or copy it to tools directory.
    pause
    exit /b 1
)
echo Done.
echo.

REM Pre-build glossary JSON files
echo [3/5] Building glossary cache...
mkdir resources 2>nul
python -c "from meowth.glossary import Glossary; from meowth.languages import SUPPORTED_LANGUAGES; import json; from pathlib import Path; [Path('resources').joinpath(f'glossary_en_{target}.json').write_text(json.dumps({'source_to_target': Glossary(source_lang='en', target_lang=target).source_to_target}, ensure_ascii=False, indent=2), encoding='utf-8') or print(f'Generated glossary_en_{target}.json') for target in SUPPORTED_LANGUAGES if target != 'en']"
echo Done.
echo.

REM Build with PyInstaller
echo [4/5] Building with PyInstaller...
pyinstaller ^
  --name "Meowth Translator" ^
  --windowed ^
  --onedir ^
  --add-data "src/meowth;meowth" ^
  --add-data "resources;resources" ^
  --add-data "pokeapi/data/v2/csv;pokeapi/data/v2/csv" ^
  --add-data "Pokemon_GBA_Font_Patch;Pokemon_GBA_Font_Patch" ^
  --add-data "tools;tools" ^
  --hidden-import customtkinter ^
  --hidden-import PIL ^
  --hidden-import click ^
  --hidden-import httpx ^
  --collect-all customtkinter ^
  launcher.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed!
    pause
    exit /b 1
)
echo Done.
echo.

REM Create ZIP
echo [5/5] Creating ZIP archive...
powershell -Command "Compress-Archive -Path 'dist\Meowth Translator' -DestinationPath 'dist\Meowth-Translator-Windows.zip' -Force"
echo Done.
echo.

echo ========================================
echo Build completed successfully!
echo Output: dist\Meowth-Translator-Windows.zip
echo ========================================
echo.
echo You can now upload this ZIP file to GitHub Releases manually.
pause
