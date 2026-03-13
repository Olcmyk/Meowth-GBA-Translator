"""Smart loader for MeowthBridge executable across platforms."""

import os
import platform
import sys
import urllib.request
import urllib.error
import shutil
import tempfile
import time
import zipfile
from pathlib import Path


def get_meowth_version() -> str:
    """Get the current meowth package version."""
    try:
        import importlib.metadata
        return importlib.metadata.version("meowth")
    except Exception:
        return "0.3.3"


def get_platform_name() -> str:
    """Get the normalized platform name for binary selection."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    else:
        return "linux"


def get_executable_name() -> str:
    """Get the executable name for the current platform."""
    return "MeowthBridge.exe" if platform.system() == "Windows" else "MeowthBridge"


def find_meowth_bridge() -> Path:
    """Locate the MeowthBridge executable using multiple search strategies.

    Search order:
    1. Environment variable MEOWTH_BRIDGE_PATH (if set)
    2. Bundled binary in package (src/meowth/binaries/{platform}/)
    3. Development build (src/MeowthBridge/bin/Release or Debug)
    4. Cached download (~/.meowth/binaries/{platform}/)
    5. Download from GitHub releases
    """
    exe_name = get_executable_name()

    # Strategy 1: Check environment variable
    env_path = os.environ.get("MEOWTH_BRIDGE_PATH")
    if env_path:
        env_exe = Path(env_path)
        if env_exe.exists() and env_exe.is_file():
            return env_exe
        if env_exe.is_dir():
            env_exe = env_exe / exe_name
            if env_exe.exists():
                return env_exe

    # Strategy 2: Check bundled binary in package
    package_dir = Path(__file__).parent
    platform_name = get_platform_name()
    bundled_exe = package_dir / platform_name / exe_name

    if bundled_exe.exists():
        if platform.system() != "Windows":
            bundled_exe.chmod(0o755)
        return bundled_exe

    # Strategy 3: Check development build
    project_root = Path(__file__).parent.parent.parent.parent
    meowth_bridge_dir = project_root / "src" / "MeowthBridge"

    for build_config in ("Release", "Debug"):
        dev_exe = meowth_bridge_dir / "bin" / build_config / "net8.0" / exe_name
        if dev_exe.exists():
            return dev_exe

    # Strategy 4: Check old location (backward compatibility)
    old_location = project_root / "MeowthBridge" / "bin"
    for build_config in ("Release", "Debug"):
        old_exe = old_location / build_config / "net8.0" / exe_name
        if old_exe.exists():
            return old_exe

    # Strategy 5: Download from GitHub
    try:
        return _download_meowth_bridge()
    except Exception as download_error:
        raise FileNotFoundError(
            f"MeowthBridge executable not found. Tried:\n"
            f"  1. Environment variable MEOWTH_BRIDGE_PATH: {env_path or '(not set)'}\n"
            f"  2. Bundled binary: {bundled_exe}\n"
            f"  3. Development build: {meowth_bridge_dir / 'bin'}\n"
            f"  4. Download from GitHub: {download_error}\n"
            f"\n"
            f"To fix this:\n"
            f"  - Set MEOWTH_BRIDGE_PATH environment variable to the executable path\n"
            f"  - Or check your internet connection for auto-download"
        ) from download_error


def _download_meowth_bridge() -> Path:
    """Download MeowthBridge ZIP from GitHub release and extract it."""
    exe_name = get_executable_name()
    platform_name = get_platform_name()
    version = get_meowth_version()

    asset_name = f"MeowthBridge-{platform_name}.zip"
    download_url = f"https://github.com/Olcmyk/Meowth-GBA-Translator/releases/download/v{version}/{asset_name}"

    # Cache directory
    cache_dir = Path.home() / ".meowth" / "binaries" / platform_name
    cache_dir.mkdir(parents=True, exist_ok=True)

    exe_path = cache_dir / exe_name

    # If already cached, return it
    if exe_path.exists():
        if platform.system() != "Windows":
            exe_path.chmod(0o755)
        return exe_path

    # Download the ZIP file
    print(f"🔽 First-time setup: Downloading MeowthBridge for {platform_name}...")
    print(f"   Source: {download_url}")

    tmp_zip_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            tmp_zip_path = Path(tmp_file.name)

        _download_with_progress_and_retry(download_url, tmp_zip_path)

        # Extract ZIP to cache directory
        print(f"📦 Extracting files...")
        with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(cache_dir)

        # Clean up temporary ZIP file
        tmp_zip_path.unlink()

        # Make executable on Unix
        if platform.system() != "Windows":
            exe_path.chmod(0o755)

        print(f"✅ Downloaded and cached to {cache_dir}")
        print(f"   (Subsequent runs will use the cached version)")
        return exe_path

    except urllib.error.HTTPError as e:
        if tmp_zip_path and tmp_zip_path.exists():
            tmp_zip_path.unlink()
        if e.code == 404:
            raise FileNotFoundError(
                f"MeowthBridge binary not found in release v{version}.\n"
                f"URL: {download_url}\n\n"
                f"This usually means:\n"
                f"  1. The release hasn't been published yet\n"
                f"  2. The binary wasn't uploaded to the release\n\n"
                f"Workaround:\n"
                f"  export MEOWTH_BRIDGE_PATH=/path/to/MeowthBridge"
            )
        else:
            raise FileNotFoundError(f"HTTP error {e.code} downloading from {download_url}: {e}")
    except Exception as e:
        if tmp_zip_path and tmp_zip_path.exists():
            tmp_zip_path.unlink()
        raise FileNotFoundError(f"Failed to download MeowthBridge: {e}")


def _download_with_progress_and_retry(url: str, dest: Path, max_retries: int = 3):
    """Download file with progress display and retry logic."""
    for attempt in range(1, max_retries + 1):
        try:
            _download_with_progress(url, dest)
            return
        except Exception as e:
            if attempt < max_retries:
                print(f"   ⚠️  Download failed (attempt {attempt}/{max_retries}): {e}")
                print(f"   🔄 Retrying in 2 seconds...")
                time.sleep(2)
            else:
                raise


def _download_with_progress(url: str, dest: Path):
    """Download file with progress display."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)

        response = urllib.request.urlopen(url, timeout=60)
        total_size = int(response.headers.get('content-length', 0))

        downloaded = 0
        chunk_size = 65536
        last_percent = -1

        with open(tmp_path, 'wb') as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                if total_size > 0:
                    percent = int((downloaded / total_size) * 100)
                    if percent != last_percent and percent % 10 == 0:
                        mb_downloaded = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        print(f"   [{percent:3d}%] {mb_downloaded:.1f} MB / {mb_total:.1f} MB")
                        last_percent = percent

        shutil.move(str(tmp_path), str(dest))

    except Exception:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
        raise


def get_binary_info() -> dict:
    """Get information about the MeowthBridge binary."""
    try:
        exe_path = find_meowth_bridge()
        if os.environ.get("MEOWTH_BRIDGE_PATH"):
            source = "environment"
        elif ".meowth" in str(exe_path):
            source = "downloaded"
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
