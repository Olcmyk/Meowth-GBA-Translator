"""Smart loader for MeowthBridge executable across platforms."""

import os
import platform
import sys
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

    # Not found anywhere
    raise FileNotFoundError(
        f"MeowthBridge executable not found. Tried:\n"
        f"  1. Environment variable MEOWTH_BRIDGE_PATH: {env_path or '(not set)'}\n"
        f"  2. Bundled binary: {bundled_exe}\n"
        f"  3. Development build: {meowth_bridge_dir / 'bin' / '{Release,Debug}' / 'net8.0' / exe_name}\n"
        f"\n"
        f"To fix this:\n"
        f"  - If developing: Build MeowthBridge with 'dotnet build src/MeowthBridge -c Release'\n"
        f"  - If using pip: This package may be missing the binary. Please report this issue.\n"
        f"  - Set MEOWTH_BRIDGE_PATH environment variable to the executable path"
    )


def get_binary_info() -> dict:
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
