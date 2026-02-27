"""English messages for all user-facing output."""


class Messages:
    """Centralized English messages for CLI and GUI output."""

    # Progress messages
    EXTRACTING_TEXTS = "Extracting texts from ROM..."
    TRANSLATING_TEXTS = "Translating texts..."
    BUILDING_ROM = "Building ROM..."
    BATCH_PROGRESS = "Total {total} batches, using {workers} parallel threads"
    BATCH_COMPLETE = "[{current}/{total}] Batch {batch_id} completed"

    # Pipeline stages
    STAGE_EXTRACT = "[1/3] Extracting texts from ROM..."
    STAGE_TRANSLATE = "[2/3] Translating texts..."
    STAGE_BUILD = "[3/3] Building ROM..."
    COMPLETE = "Complete: {output}"

    # ROM operations
    LOADING_ROM = "Loading ROM..."
    ROM_EXPANDED = "ROM expanded to {size}MB"
    APPLYING_FONT_PATCH = "Applying font patch..."
    FONT_PATCH_APPLIED = "Font patch applied"
    SKIPPING_FONT_PATCH = "Skipping font patch for Latin language ({lang})"
    INJECTING_TEXTS = "Injecting {count} translated texts..."
    INJECTION_STATS = "Done: {in_place} in-place, {relocated} relocated, {skipped} skipped, {partial_ptr} partial-ptr skipped, {unsafe_ptr} unsafe ptrs filtered"
    SAVED_ROM = "Saved: {path}"
    DETECTED_GAME = "Detected game: {game}"
    GAME_DETECTION_FAILED = "Warning: could not detect game from ROM header, using: {game}"
    ADDED_MANUAL_ENTRIES = "Added {count} manual entries"

    # Cache and translation
    CACHE_MISMATCH = "[Cache split mismatch ({parts} vs {texts}), retranslating]"
    PARTIAL_UNTRANSLATED = "[Partial untranslated, not caching this batch]"
    BATCH_SPLIT_MISMATCH = "[Batch split mismatch ({parts} vs {texts}), translating individually]"
    API_REQUEST_FAILED = "[API request failed: {error}, retrying in {wait}s ({attempt}/{max_retries})]"

    # Errors
    MEOWTH_BRIDGE_NOT_FOUND = "MeowthBridge executable not found. Build it first: dotnet build src/MeowthBridge -c Release"
    MEOWTH_BRIDGE_FAILED = "MeowthBridge failed (exit {code}):\n{stderr}"
    MEOWTH_BRIDGE_NO_OUTPUT = "MeowthBridge did not produce {path}"

    # File operations
    EXTRACTED_FILE = "Extracted: {path}"
    TRANSLATED_FILE = "Translated: {path}"
