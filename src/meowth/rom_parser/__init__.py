"""Pure Python ROM parser for GBA Pokemon games.

This package replaces the C# MeowthBridge dependency with pure Python
implementations that produce byte-identical output.
"""

from .extractor import extract_texts
from .gba_rom import GbaRom
from .pcs_decoder import PcsDecoder
from .script_extractor import ScriptExtractor
from .table_extractor import TableExtractor

__all__ = [
    "extract_texts",
    "GbaRom",
    "PcsDecoder",
    "TableExtractor",
    "ScriptExtractor",
]
