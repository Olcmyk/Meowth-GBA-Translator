#!/bin/bash
set -e

echo "=== Testing Build Process Locally ==="

# 1. Check MeowthBridge can find resources
echo ""
echo "1. Testing MeowthBridge resource resolution..."
./src/meowth/binaries/macos/MeowthBridge extract testgba/firered_en.gba -o /tmp/test_extract.json || {
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
mkdir -p /tmp/test_bundle/Contents/meowth/binaries/macos
mkdir -p /tmp/test_bundle/Contents/resources
cp src/meowth/binaries/macos/MeowthBridge /tmp/test_bundle/Contents/meowth/binaries/macos/
cp -r resources/* /tmp/test_bundle/Contents/resources/
chmod +x /tmp/test_bundle/Contents/meowth/binaries/macos/MeowthBridge

echo "Testing from bundle structure..."
cd /tmp/test_bundle/Contents/meowth/binaries/macos
./MeowthBridge extract /Users/booffaoex/code/Meowth-GBA-Translator/testgba/firered_en.gba -o /tmp/test_bundle_extract.json || {
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
PYTHONPATH=src python -c "
from meowth.gui.app import main
from meowth.core.engine import TranslationEngine
from meowth.core.config import TranslationConfig
print('✓ All imports work')
"

echo ""
echo "=== All tests passed! ==="
echo ""
echo "The build should work. Key points:"
echo "1. MeowthBridge can find resources in both dev and bundle structure"
echo "2. All required files are present"
echo "3. Python imports work correctly"
