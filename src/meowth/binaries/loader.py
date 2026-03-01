"""Smart loader for MeowthBridge executable across platforms."""

import os
import platform
import sys
import urllib.request
import urllib.error
import shutil
import tempfile
from pathlib import Path


def get_platform_name() -> str:
    """Get the normalized platform name for binary selection.

    Returns:
        One of: "windows", "macos", "linux"
    """
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    else:
        # Fallback for unknown platforms
        return "linux"


def get_executable_name() -> str:
    """Get the executable name for the current platform.

    Returns:
        "MeowthBridge.exe" on Windows, "MeowthBridge" on Unix
    """
    return "MeowthBridge.exe" if platform.system() == "Windows" else "MeowthBridge"


def find_meowth_bridge() -> Path:
    """Locate the MeowthBridge executable using multiple search strategies.

    Search order:
    1. Environment variable MEOWTH_BRIDGE_PATH (if set)
    2. Bundled binary in package (src/meowth/binaries/{platform}/)
    3. Development build (src/MeowthBridge/bin/Release or Debug)

    Returns:
        Path to the MeowthBridge executable

    Raises:
        FileNotFoundError: If MeowthBridge cannot be found
    """
    exe_name = get_executable_name()

    # Strategy 1: Check environment variable
    env_path = os.environ.get("MEOWTH_BRIDGE_PATH")
    if env_path:
        env_exe = Path(env_path)
        if env_exe.exists() and env_exe.is_file():
            return env_exe
        # If MEOWTH_BRIDGE_PATH is a directory, look for executable inside
        if env_exe.is_dir():
            env_exe = env_exe / exe_name
            if env_exe.exists():
                return env_exe

    # Strategy 2: Check bundled binary in package
    # This is where the binary will be when installed via pip
    package_dir = Path(__file__).parent
    platform_name = get_platform_name()
    bundled_exe = package_dir / platform_name / exe_name

    if bundled_exe.exists():
        # Make sure it's executable on Unix systems
        if platform.system() != "Windows":
            bundled_exe.chmod(0o755)
        return bundled_exe

    # Strategy 3: Check development build
    # This is for developers working on the project
    # Look for src/MeowthBridge/bin/{Release,Debug}/net8.0/MeowthBridge
    project_root = Path(__file__).parent.parent.parent.parent
    meowth_bridge_dir = project_root / "src" / "MeowthBridge"

    # Try Release first, then Debug
    for build_config in ("Release", "Debug"):
        dev_exe = meowth_bridge_dir / "bin" / build_config / "net8.0" / exe_name
        if dev_exe.exists():
            return dev_exe

    # Strategy 4: Check if it's in the old location (backward compatibility)
    old_location = project_root / "MeowthBridge" / "bin"
    for build_config in ("Release", "Debug"):
        old_exe = old_location / build_config / "net8.0" / exe_name
        if old_exe.exists():
            return old_exe

    # Not found in standard locations, try downloading from GitHub
    try:
        return _download_meowth_bridge()
    except Exception as download_error:
        # If download fails, raise the original error
        raise FileNotFoundError(
            f"MeowthBridge executable not found. Tried:\n"
            f"  1. Environment variable MEOWTH_BRIDGE_PATH: {env_path or '(not set)'}\n"
            f"  2. Bundled binary: {bundled_exe}\n"
            f"  3. Development build: {meowth_bridge_dir / 'bin' / '{Release,Debug}' / 'net8.0' / exe_name}\n"
            f"  4. Download from GitHub: {download_error}\n"
            f"\n"
            f"To fix this:\n"
            f"  - If developing: Build MeowthBridge with 'dotnet build src/MeowthBridge -c Release'\n"
            f"  - If using pip: Check your internet connection or set MEOWTH_BRIDGE_PATH\n"
            f"  - Set MEOWTH_BRIDGE_PATH environment variable to the executable path"
        ) from download_error




def _download_meowth_bridge() -> Path:
    """Download MeowthBridge binary from GitHub release if not found locally.

    Returns:
        Path to the downloaded executable

    Raises:
        FileNotFoundError: If download fails
    """
    import json

    exe_name = get_executable_name()
    platform_name = get_platform_name()

    # Determine the binary URL based on platform
    # Using latest release from GitHub
    version = "v0.3.0"  # Can be updated to fetch latest
    asset_name_map = {
        "macos": "MeowthBridge-macos",
        "windows": "MeowthBridge.exe",
        "linux": "MeowthBridge-linux",
    }
    asset_name = asset_name_map.get(platform_name, exe_name)

    # URL to the GitHub release
    download_url = f"https://github.com/Olcmyk/Meowth-GBA-Translator/releases/download/{version}/{asset_name}"

    # Create cache directory
    cache_dir = Path.home() / ".meowth" / "binaries" / platform_name
    cache_dir.mkdir(parents=True, exist_ok=True)

    exe_path = cache_dir / exe_name

    # If already cached, return it
    if exe_path.exists():
        if platform.system() != "Windows":
            exe_path.chmod(0o755)
        return exe_path

    # Download the binary
    print(f"Downloading MeowthBridge from GitHub... ({download_url})")

    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)

            # Download with progress
            urllib.request.urlretrieve(download_url, tmp_path)

            # Move to cache
            shutil.move(str(tmp_path), str(exe_path))

            # Make executable on Unix
            if platform.system() != "Windows":
                exe_path.chmod(0o755)

            print(f"Downloaded to {exe_path}")
            return exe_path

    except urllib.error.URLError as e:
        raise FileNotFoundError(f"Failed to download MeowthBridge from {download_url}: {e}")
    except Exception as e:
        raise FileNotFoundError(f"Error downloading MeowthBridge: {e}")
    """Get information about the MeowthBridge binary.

    Returns:
        Dictionary with binary information:
        - path: Path to the executable
        - platform: Platform name (windows/macos/linux)
        - source: Where the binary was found (env/bundled/dev)
        - exists: Whether the binary exists
    """
    try:
        exe_path = find_meowth_bridge()

        # Determine source
        if os.environ.get("MEOWTH_BRIDGE_PATH"):
            source = "environment"
        elif "binaries" in str(exe_path):
            source = "bundled"
        else:
            source = "development"

        return {
            "path": str(exe_path),
            "platform": get_platform_name(),
            "source": source,
            "exists": True,
        }
    except FileNotFoundError:
        return {
            "path": None,
            "platform": get_platform_name(),
            "source": None,
            "exists": False,
        }
