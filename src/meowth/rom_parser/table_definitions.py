"""Table definitions for GBA Pokemon games.

This module contains hardcoded table addresses and structures extracted
from HMA metadata files. These addresses are game-specific and version-specific.

Table structures are defined as:
- address: ROM offset where table starts
- count: Number of entries in the table
- entry_size: Bytes per entry (for inline text tables)
- is_pointer_based: Whether entries are pointers to text (vs inline text)
"""

from typing import NamedTuple


class TableDefinition(NamedTuple):
    """Definition of a ROM table structure."""
    name: str  # HMA anchor name (e.g., "data.pokemon.names")
    category: str  # Category for JSON output (e.g., "pokemon_names")
    address: int  # ROM offset where table starts
    count: int  # Number of entries
    entry_size: int  # Bytes per entry (for fixed-size) or max length (for sequential)
    is_pointer_based: bool  # True if entries are pointers, False if inline text
    is_sequential: bool = False  # True if variable-length strings packed sequentially
    text_length: int | None = None  # Length of PCS segment (if different from entry_size)


# FireRed BPRE0 table definitions
# Extracted from work/firered_texts_en.json analysis
FIRERED_BPRE0_TABLES = [
    # Pokemon data
    TableDefinition(
        name="data.pokemon.names",
        category="pokemon_names",
        address=0x245EE0,
        count=412,
        entry_size=11,
        is_pointer_based=False,
    ),
    TableDefinition(
        name="data.pokemon.type.names",
        category="type_names",
        address=0x24F1A0,
        count=18,
        entry_size=7,
        is_pointer_based=False,
    ),
    TableDefinition(
        name="data.pokemon.moves.names",
        category="move_names",
        address=0x247094,
        count=355,
        entry_size=13,
        is_pointer_based=False,
    ),
    TableDefinition(
        name="data.pokemon.moves.descriptions",
        category="move_descriptions",
        address=0x482834,
        count=354,
        entry_size=100,  # Max length for sequential strings
        is_pointer_based=False,
        is_sequential=True,  # Variable-length strings packed sequentially
    ),
    TableDefinition(
        name="data.pokemon.natures.names",
        category="nature_names",
        address=0x463DBC,
        count=25,
        entry_size=10,  # Max length for sequential strings
        is_pointer_based=False,
        is_sequential=True,  # Variable-length strings packed sequentially
    ),

    # Items
    TableDefinition(
        name="data.items.stats",
        category="item_names",
        address=0x3DB028,
        count=375,
        entry_size=44,  # Full item structure is 44 bytes
        is_pointer_based=False,
        is_sequential=False,
        text_length=13,  # Name field is 13 bytes
    ),

    # Abilities
    TableDefinition(
        name="data.abilities.names",
        category="ability_names",
        address=0x24FC40,
        count=78,
        entry_size=13,
        is_pointer_based=False,
    ),
    TableDefinition(
        name="data.abilities.descriptions",
        category="ability_descriptions",
        address=0x24F3C4,
        count=78,
        entry_size=64,  # Max length for sequential strings
        is_pointer_based=False,
        is_sequential=True,  # Variable-length strings packed sequentially
    ),

    # Trainers
    TableDefinition(
        name="data.trainers.classes.names",
        category="trainer_classes",
        address=0x23E558,
        count=107,
        entry_size=13,
        is_pointer_based=False,
    ),

    # Maps and locations
    TableDefinition(
        name="data.maps.names",
        category="map_names",
        address=0x3EECFC,
        count=109,
        entry_size=20,  # Max length for sequential strings
        is_pointer_based=False,
        is_sequential=True,  # Variable-length strings packed sequentially
    ),
    TableDefinition(
        name="data.pokedex.habitat.names",
        category="habitat_names",
        address=0x415DF7,
        count=9,
        entry_size=25,  # Max length for sequential strings
        is_pointer_based=False,
        is_sequential=True,  # Variable-length strings packed sequentially
    ),

    # Menu text
    TableDefinition(
        name="data.menus.text.options",
        category="menu_options",
        address=0x419DD3,
        count=7,
        entry_size=15,  # Max length
        is_pointer_based=False,
        is_sequential=True,
    ),
    TableDefinition(
        name="data.menus.text.pc",
        category="menu_pc",
        address=0x418208,
        count=31,
        entry_size=30,  # Max length
        is_pointer_based=False,
        is_sequential=True,
    ),
    TableDefinition(
        name="data.menus.text.pcoptions",
        category="menu_pcoptions",
        address=0x4176F1,
        count=3,
        entry_size=20,  # Max length
        is_pointer_based=False,
        is_sequential=True,
    ),
    TableDefinition(
        name="data.menus.text.pokemon",
        category="menu_pokemon",
        address=0x4171DF,
        count=27,
        entry_size=25,  # Max length
        is_pointer_based=False,
        is_sequential=True,
    ),
    TableDefinition(
        name="data.text.menu.itemStorage",
        category="menu_item_storage",
        address=0x417713,
        count=3,
        entry_size=20,  # Max length
        is_pointer_based=False,
        is_sequential=True,
    ),
    TableDefinition(
        name="data.text.menu.pause",
        category="menu_pause",
        address=0x41627D,
        count=9,
        entry_size=15,  # Max length
        is_pointer_based=False,
        is_sequential=True,
    ),
    TableDefinition(
        name="data.text.menu.pokemon.options",
        category="menu_pokemon_options",
        address=0x416994,
        count=18,
        entry_size=15,  # Max length
        is_pointer_based=False,
        is_sequential=True,
    ),
    TableDefinition(
        name="data.text.trade.messages",
        category="trade_messages",
        address=0x41718C,
        count=9,
        entry_size=70,  # Max length
        is_pointer_based=False,
        is_sequential=True,
    ),
]


# Game code to table definitions mapping
GAME_TABLES = {
    "BPRE0": FIRERED_BPRE0_TABLES,
    "BPRE1": FIRERED_BPRE0_TABLES,  # Same as BPRE0
    "BPGE0": FIRERED_BPRE0_TABLES,  # LeafGreen uses same addresses
    "BPGE1": FIRERED_BPRE0_TABLES,
    # TODO: Add Emerald, Ruby, Sapphire table definitions
}


def get_tables_for_game(game_code: str) -> list[TableDefinition]:
    """Get table definitions for a specific game code.

    Args:
        game_code: Game code from ROM header (e.g., "BPRE0")

    Returns:
        List of table definitions for the game

    Raises:
        ValueError: If game code is not supported
    """
    if game_code not in GAME_TABLES:
        raise ValueError(f"Unsupported game code: {game_code}")
    return GAME_TABLES[game_code]
