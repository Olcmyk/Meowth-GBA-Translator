#!/bin/bash
# Build MeowthBridge for all platforms locally
# This is useful for testing the packaging before pushing to GitHub

set -e

echo "=== Building MeowthBridge for all platforms ==="
echo ""

# Check if dotnet is installed
if ! command -v dotnet &> /dev/null; then
    echo "Error: dotnet CLI not found. Please install .NET 8.0 SDK."
    exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSHARP_PROJECT="$PROJECT_ROOT/src/MeowthBridge"
OUTPUT_DIR="$PROJECT_ROOT/src/meowth/binaries"

# Build for Linux
echo "Building for Linux (x64)..."
dotnet publish "$CSHARP_PROJECT" \
    -c Release \
    -r linux-x64 \
    --self-contained true \
    -p:PublishSingleFile=true \
    -p:PublishTrimmed=true \
    -p:IncludeNativeLibrariesForSelfExtract=true \
    -o "$OUTPUT_DIR/linux"

chmod +x "$OUTPUT_DIR/linux/MeowthBridge"
echo "✓ Linux binary built: $(du -h "$OUTPUT_DIR/linux/MeowthBridge" | cut -f1)"
echo ""

# Build for Windows
echo "Building for Windows (x64)..."
dotnet publish "$CSHARP_PROJECT" \
    -c Release \
    -r win-x64 \
    --self-contained true \
    -p:PublishSingleFile=true \
    -p:PublishTrimmed=true \
    -p:IncludeNativeLibrariesForSelfExtract=true \
    -o "$OUTPUT_DIR/windows"

echo "✓ Windows binary built: $(du -h "$OUTPUT_DIR/windows/MeowthBridge.exe" | cut -f1)"
echo ""

# Build for macOS (requires macOS host for universal binary)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Building for macOS (universal binary)..."

    # Build x64
    dotnet publish "$CSHARP_PROJECT" \
        -c Release \
        -r osx-x64 \
        --self-contained true \
        -p:PublishSingleFile=true \
        -p:PublishTrimmed=true \
        -p:IncludeNativeLibrariesForSelfExtract=true \
        -o "$PROJECT_ROOT/build/macos-x64"

    # Build arm64
    dotnet publish "$CSHARP_PROJECT" \
        -c Release \
        -r osx-arm64 \
        --self-contained true \
        -p:PublishSingleFile=true \
        -p:PublishTrimmed=true \
        -p:IncludeNativeLibrariesForSelfExtract=true \
        -o "$PROJECT_ROOT/build/macos-arm64"

    # Create universal binary
    mkdir -p "$OUTPUT_DIR/macos"
    lipo -create \
        "$PROJECT_ROOT/build/macos-x64/MeowthBridge" \
        "$PROJECT_ROOT/build/macos-arm64/MeowthBridge" \
        -output "$OUTPUT_DIR/macos/MeowthBridge"

    chmod +x "$OUTPUT_DIR/macos/MeowthBridge"
    echo "✓ macOS universal binary built: $(du -h "$OUTPUT_DIR/macos/MeowthBridge" | cut -f1)"

    # Clean up temp builds
    rm -rf "$PROJECT_ROOT/build/macos-x64" "$PROJECT_ROOT/build/macos-arm64"
else
    echo "⚠ Skipping macOS build (requires macOS host for universal binary)"
    echo "  Building x64-only binary instead..."
    dotnet publish "$CSHARP_PROJECT" \
        -c Release \
        -r osx-x64 \
        --self-contained true \
        -p:PublishSingleFile=true \
        -p:PublishTrimmed=true \
        -p:IncludeNativeLibrariesForSelfExtract=true \
        -o "$OUTPUT_DIR/macos"

    chmod +x "$OUTPUT_DIR/macos/MeowthBridge"
    echo "✓ macOS x64 binary built: $(du -h "$OUTPUT_DIR/macos/MeowthBridge" | cut -f1)"
fi

echo ""
echo "=== Build complete ==="
echo "Binaries are in: $OUTPUT_DIR"
echo ""
echo "Total size:"
du -sh "$OUTPUT_DIR"
echo ""
echo "Individual sizes:"
du -h "$OUTPUT_DIR"/*/* 2>/dev/null || true
