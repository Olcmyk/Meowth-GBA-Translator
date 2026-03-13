# Windows Release Bug Fix - v0.3.3

## Problem

Users downloading the Windows release (v0.3.2) encountered this error when trying to translate ROMs:

```
Translation failed: [WinError 193] %1 is not a valid Win32 application.
```

Additionally, the Windows ZIP package was only 117MB while the macOS DMG was 200MB, indicating missing files.

## Root Cause

The Windows build configuration in `.github/workflows/build-csharp.yml` was using:

```yaml
dotnet publish src/MeowthBridge \
  -c Release \
  -r win-x64 \
  --self-contained true \
  -p:PublishTrimmed=false \
  -o build/windows
```

This creates:
- `MeowthBridge.exe` (the main executable)
- Many separate .NET runtime DLL files (System.*.dll, etc.)

When PyInstaller packaged the GUI application, it included `MeowthBridge.exe` but **not all the required DLL dependencies**. When Python tried to execute `MeowthBridge.exe` via `subprocess.run()`, Windows couldn't load the missing DLLs and returned error 193 ("not a valid Win32 application").

## Solution

Added `PublishSingleFile=true` and `IncludeNativeLibrariesForSelfExtract=true` to bundle everything into a single executable:

```yaml
dotnet publish src/MeowthBridge \
  -c Release \
  -r win-x64 \
  --self-contained true \
  -p:PublishSingleFile=true \
  -p:PublishTrimmed=false \
  -p:IncludeNativeLibrariesForSelfExtract=true \
  -o build/windows
```

This creates a single `MeowthBridge.exe` file that contains:
- The application code
- All .NET runtime libraries
- All native dependencies

## Changes Made

1. **`.github/workflows/build-csharp.yml`**:
   - Added `PublishSingleFile=true` to Windows, macOS, and Linux builds
   - Added `IncludeNativeLibrariesForSelfExtract=true` to all builds

2. **Version bump to 0.3.3**:
   - `pyproject.toml`: Updated version
   - `src/meowth/binaries/loader.py`: Updated fallback version
   - All `README*.md` files: Updated version badges

3. **Created `CHANGELOG.md`**: Documented the fix and version history

## Expected Results

After this fix:
- Windows package size will increase to ~200MB (similar to macOS)
- `MeowthBridge.exe` will be a single, standalone executable
- No more "WinError 193" errors
- Translation will work correctly on Windows

## Testing

To test the fix:
1. Create a new release (v0.3.3)
2. Download the Windows ZIP package
3. Extract and verify `MeowthBridge.exe` is ~200MB (single file)
4. Run translation and verify it works without errors

## Technical Notes

- `PublishSingleFile=true`: Bundles all managed assemblies into the executable
- `IncludeNativeLibrariesForSelfExtract=true`: Includes native libraries (like coreclr.dll) in the bundle
- The executable extracts dependencies to a temp directory at runtime
- This is the recommended approach for distributing .NET applications
