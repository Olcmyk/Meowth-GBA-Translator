#!/bin/bash
set -e

ROM_PATH="testgba/1636 - Pokemon Fire Red (U)(Squirrels).gba"

if [ ! -f "$ROM_PATH" ]; then
    echo "ERROR: Test ROM not found: $ROM_PATH"
    exit 1
fi

echo "=== Testing Build Process Locally ==="

# 1. Check MeowthBridge can find resources
echo ""
echo "1. Testing MeowthBridge resource resolution..."
./src/meowth/binaries/macos/MeowthBridge extract "$ROM_PATH" -o /tmp/test_extract.json || {
    echo "ERROR: MeowthBridge failed to extract"
    exit 1
}
echo "✓ MeowthBridge works"

# 2. Check resources directory exists
echo ""
echo "2. Checking resources directory..."
if [ ! -d "resources" ]; then
    echo "ERROR: resources directory not found"
    exit 1
fi
ls -la resources/*.py resources/*.txt | head -5
echo "✓ Resources directory exists"

# 3. Check PyInstaller structure
echo ""
echo "3. Simulating PyInstaller structure..."
rm -rf /tmp/test_bundle
mkdir -p /tmp/test_bundle/Contents/meowth/binaries
cp -R src/meowth/binaries/macos /tmp/test_bundle/Contents/meowth/binaries/
mkdir -p /tmp/test_bundle/Contents/meowth/binaries/macos/resources
cp -r resources/* /tmp/test_bundle/Contents/meowth/binaries/macos/resources/
chmod +x /tmp/test_bundle/Contents/meowth/binaries/macos/MeowthBridge

echo "Testing from bundle structure..."
cd /tmp/test_bundle/Contents/meowth/binaries/macos
./MeowthBridge extract "/Users/booffaoex/code/Meowth-GBA-Translator/$ROM_PATH" -o /tmp/test_bundle_extract.json || {
    echo "ERROR: MeowthBridge failed in bundle structure"
    cd /Users/booffaoex/code/Meowth-GBA-Translator
    exit 1
}
cd /Users/booffaoex/code/Meowth-GBA-Translator
echo "✓ MeowthBridge works in bundle structure"

# 4. Check all required files
echo ""
echo "4. Checking required files for PyInstaller..."
required_files=(
    "launcher.py"
    "src/meowth/__init__.py"
    "src/meowth/gui/app.py"
    "resources/hma.py"
    "Pokemon_GBA_Font_Patch/pokeFRLG/PMRSEFRLG_charmap.txt"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "ERROR: Missing required file: $file"
        exit 1
    fi
done
echo "✓ All required files present"

# 5. Test Python imports
echo ""
echo "5. Testing Python imports..."
PYTHONPATH=src python3 -c "
from meowth.core.engine import TranslationEngine
from meowth.core.config import TranslationConfig
try:
    from meowth.gui.app import main
    print('✓ GUI imports work')
except ModuleNotFoundError as exc:
    if exc.name == 'customtkinter':
        print('✓ GUI import skipped (optional dependency customtkinter not installed)')
    else:
        raise
print('✓ Core imports work')
"

echo ""
echo "=== All tests passed! ==="
echo ""
echo "The build should work. Key points:"
echo "1. MeowthBridge can find resources in both dev and bundle structure"
echo "2. All required files are present"
echo "3. Python imports work correctly"
