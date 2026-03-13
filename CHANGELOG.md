# Changelog

All notable changes to this project will be documented in this file.

## [0.3.3] - 2026-03-13

### Fixed
- **Windows Release Bug**: Fixed "WinError 193: %1 is not a valid Win32 application" error
  - Added `PublishSingleFile=true` to bundle all .NET runtime dependencies into single executable
  - Added `IncludeNativeLibrariesForSelfExtract=true` to include native libraries
  - This ensures MeowthBridge.exe can run standalone without missing DLL dependencies
  - Windows package size will increase to match macOS (~200MB) but will work correctly

### Technical Details
The previous build used `--self-contained true` without `PublishSingleFile`, which created MeowthBridge.exe + many separate .NET runtime DLLs. When PyInstaller packaged the GUI app, some DLLs were missing, causing the "not a valid Win32 application" error. The fix bundles everything into a single executable.

## [0.3.2] - 2024-XX-XX

### Fixed
- CLI binary download - use ZIP packages with resources
- Use ZIP packages instead of PublishSingleFile

## [0.3.1] - 2024-XX-XX

### Fixed
- Use PublishSingleFile for standalone binaries

## [0.3.0] - 2024-XX-XX

### Added
- Initial release with GUI and CLI support
- Support for 11+ LLM providers
- Cross-platform support (macOS, Windows, Linux)
- Six language support
