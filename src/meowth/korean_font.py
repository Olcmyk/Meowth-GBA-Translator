"""Build a Korean Gen 3 GBA font patch from Galmuri BDF fonts."""

from __future__ import annotations

import json
import os
import re
import shutil
import zipfile
import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .resource_path import get_resource_path

NORMAL_FONT_NAME = "Galmuri11.bdf"
SMALL_FONT_NAME = "Galmuri9.bdf"

NORMAL_GLYPH_SIZE = 16  # 11x11 1bpp, padded to 16 bytes
SMALL_GLYPH_SIZE = 11   # 9x9 1bpp, padded to 11 bytes
NORMAL_SIZE = (11, 11)
SMALL_SIZE = (9, 9)

KOREAN_HIGH_BYTES = (
    list(range(0x01, 0x06))
    + list(range(0x07, 0x1B))
    + list(range(0x1C, 0x1F))
)

# The current renderer's table reaches 0x1E5D, matching the bundled Chinese
# font size of 6,763 glyphs. Full Hangul syllables do not fit, so we subset.
MAX_KOREAN_GLYPHS = 6763

PUNCTUATION_CODES = [0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E]
PUNCTUATION_CHARS = [";", ".", "-", "~", "'", ",", "!", "?", ":"]

COMMON_KOREAN_CHARS = (
    "가나다라마바사아자차카타파하"
    "거너더러머버서어저처커터퍼허"
    "고노도로모보소오조초코토포호"
    "구누두루무부수우주추쿠투푸후"
    "그느드르므브스으즈츠크트프흐"
    "기니디리미비시이지치키티피히"
    "게네데레메베세에제체케테페헤"
    "과와괜관광괜괴괜귀권궐"
    "ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ"
    "ㅏㅑㅓㅕㅗㅛㅜㅠㅡㅣ"
    "획득했다합니다입니다에게으로에서까지부터그리고하지만"
    "포켓몬트레이너박사체육관마을도로시티리그배틀기술아이템"
    "불꽃물풀전기얼음격투독땅비행에스퍼벌레바위고스트드래곤악강철페어리"
)

CONTROL_PATTERN = re.compile(
    r"\\(?:btn[0-9A-Fa-f]{2}|CC[0-9A-Fa-f]{4}|B[0-9A-Fa-f]|[?][0-9A-Fa-f]{2}|[A-Za-z.])"
    r"|\[[A-Za-z_][A-Za-z0-9_]*\]"
    r"|\{[0-9A-Fa-f]{2}\}"
)


@dataclass(frozen=True)
class KoreanFontBuildResult:
    """Paths and statistics for generated Korean font assets."""

    output_dir: Path
    charmap_path: Path
    normal_font_path: Path
    small_font_path: Path
    normal_punctuation_path: Path
    small_punctuation_path: Path
    glyph_count: int
    capacity: int


@dataclass
class BdfGlyph:
    width: int
    height: int
    x_offset: int
    y_offset: int
    rows: list[str]


class BdfFont:
    """Minimal BDF parser for Galmuri bitmap fonts."""

    def __init__(self, text: str):
        self.glyphs: dict[int, BdfGlyph] = {}
        self._parse(text)

    @classmethod
    def from_zip(cls, zip_path: Path, member_name: str) -> "BdfFont":
        with zipfile.ZipFile(zip_path) as zf:
            with zf.open(member_name) as fp:
                return cls(fp.read().decode("utf-8"))

    def _parse(self, text: str) -> None:
        lines = iter(text.splitlines())
        for line in lines:
            if not line.startswith("STARTCHAR"):
                continue

            encoding: int | None = None
            glyph: BdfGlyph | None = None
            bitmap: list[str] = []
            in_bitmap = False

            for line in lines:
                if line.startswith("ENCODING "):
                    encoding = int(line.split()[1])
                elif line.startswith("BBX "):
                    _, w, h, x, y = line.split()
                    glyph = BdfGlyph(int(w), int(h), int(x), int(y), bitmap)
                elif line == "BITMAP":
                    in_bitmap = True
                elif line == "ENDCHAR":
                    if encoding is not None and glyph is not None:
                        self.glyphs[encoding] = glyph
                    break
                elif in_bitmap:
                    bitmap.append(line.strip())

    def render(self, ch: str, width: int, height: int) -> list[list[int]]:
        glyph = self.glyphs.get(ord(ch))
        canvas = [[0 for _ in range(width)] for _ in range(height)]
        if glyph is None or glyph.width <= 0 or glyph.height <= 0:
            return canvas

        top = height - (glyph.y_offset + glyph.height)
        left = glyph.x_offset

        for row_idx, row_hex in enumerate(glyph.rows[: glyph.height]):
            if not row_hex:
                continue
            bit_count = len(row_hex) * 4
            bits = f"{int(row_hex, 16):0{bit_count}b}"[: glyph.width]
            for col_idx, bit in enumerate(bits):
                dst_y = top + row_idx
                dst_x = left + col_idx
                if bit == "1" and 0 <= dst_x < width and 0 <= dst_y < height:
                    canvas[dst_y][dst_x] = 1
        return canvas


def default_korean_font_zip() -> Path | None:
    """Return the configured Korean font zip, if one is available."""
    env_path = os.environ.get("MEOWTH_KOREAN_FONT_ZIP") or os.environ.get("MEOWTH_KO_FONT_ZIP")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path
    return None


def collect_korean_chars(entries: list[dict] | None = None, include_pokeapi: bool = True) -> list[str]:
    """Collect the Korean glyph subset needed for translated ROM text."""
    required = Counter()

    for ch in COMMON_KOREAN_CHARS:
        if _needs_glyph(ch):
            required[ch] += 1

    for entry in entries or []:
        text = entry.get("translated") or ""
        text = CONTROL_PATTERN.sub("", text)
        for ch in text:
            if _needs_glyph(ch):
                required[ch] += 10

    optional = Counter()
    if include_pokeapi:
        for ch in _iter_pokeapi_korean_chars():
            if _needs_glyph(ch):
                optional[ch] += 1

    chars: list[str] = []
    seen: set[str] = set()
    for ch, _ in required.most_common():
        if ch not in seen:
            chars.append(ch)
            seen.add(ch)

    if len(chars) > MAX_KOREAN_GLYPHS:
        raise ValueError(
            f"Korean required glyph set has {len(chars)} chars, "
            f"but capacity is {MAX_KOREAN_GLYPHS}"
        )

    for ch, _ in optional.most_common():
        if ch not in seen:
            chars.append(ch)
            seen.add(ch)
        if len(chars) >= MAX_KOREAN_GLYPHS:
            break

    return chars


def generate_korean_font_assets(
    font_zip_path: Path,
    output_dir: Path,
    entries: list[dict] | None = None,
    include_pokeapi: bool = True,
) -> KoreanFontBuildResult:
    """Generate Korean charmap and GBA 1bpp font binaries from Galmuri BDF."""
    font_zip_path = Path(font_zip_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    chars = collect_korean_chars(entries, include_pokeapi=include_pokeapi)
    if not chars:
        raise ValueError("No Korean glyphs collected")

    normal_font = BdfFont.from_zip(font_zip_path, NORMAL_FONT_NAME)
    small_font = BdfFont.from_zip(font_zip_path, SMALL_FONT_NAME)

    normal_path = output_dir / "gba_chs_font_11x11.bin"
    small_path = output_dir / "gba_chs_font_9x9.bin"
    normal_punct_path = output_dir / "gba_chs_punctuation_11x11.bin"
    small_punct_path = output_dir / "gba_chs_punctuation_9x9.bin"
    charmap_path = output_dir / "PMRSEFRLG_charmap.txt"

    normal_path.write_bytes(_build_font_bin(normal_font, chars, NORMAL_SIZE, NORMAL_GLYPH_SIZE))
    small_path.write_bytes(_build_font_bin(small_font, chars, SMALL_SIZE, SMALL_GLYPH_SIZE))
    normal_punct_path.write_bytes(_build_punctuation_bin(normal_font, NORMAL_SIZE, NORMAL_GLYPH_SIZE))
    small_punct_path.write_bytes(_build_punctuation_bin(small_font, SMALL_SIZE, SMALL_GLYPH_SIZE))
    charmap_path.write_text(_build_charmap(chars), encoding="utf-8")
    _copy_galmuri_license(font_zip_path, output_dir)

    summary = {
        "glyph_count": len(chars),
        "capacity": MAX_KOREAN_GLYPHS,
        "font_zip": str(font_zip_path),
        "normal_font": NORMAL_FONT_NAME,
        "small_font": SMALL_FONT_NAME,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return KoreanFontBuildResult(
        output_dir=output_dir,
        charmap_path=charmap_path,
        normal_font_path=normal_path,
        small_font_path=small_path,
        normal_punctuation_path=normal_punct_path,
        small_punctuation_path=small_punct_path,
        glyph_count=len(chars),
        capacity=MAX_KOREAN_GLYPHS,
    )


def render_font_preview(
    assets_dir: Path,
    output_path: Path,
    max_glyphs: int = 256,
    columns: int = 16,
    scale: int = 4,
) -> Path:
    """Render a PNG preview of generated 11x11 Korean glyphs."""
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError("Pillow is required to render font previews") from exc

    assets_dir = Path(assets_dir)
    output_path = Path(output_path)
    charmap = _read_generated_chars(assets_dir / "PMRSEFRLG_charmap.txt")[:max_glyphs]
    font_data = (assets_dir / "gba_chs_font_11x11.bin").read_bytes()

    cell_w = (NORMAL_SIZE[0] + 6) * scale
    cell_h = (NORMAL_SIZE[1] + 10) * scale
    rows = max(1, (len(charmap) + columns - 1) // columns)
    image = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(image)

    for idx, ch in enumerate(charmap):
        x0 = (idx % columns) * cell_w
        y0 = (idx // columns) * cell_h
        glyph = font_data[idx * NORMAL_GLYPH_SIZE : (idx + 1) * NORMAL_GLYPH_SIZE]
        bitmap = _unpack_bitmap(glyph, *NORMAL_SIZE)
        draw.rectangle([x0, y0, x0 + NORMAL_SIZE[0] * scale + 1, y0 + NORMAL_SIZE[1] * scale + 1], outline=(200, 200, 200))
        for y, row in enumerate(bitmap):
            for x, bit in enumerate(row):
                if bit:
                    draw.rectangle(
                        [
                            x0 + x * scale,
                            y0 + y * scale,
                            x0 + (x + 1) * scale - 1,
                            y0 + (y + 1) * scale - 1,
                        ],
                        fill="black",
                    )
        draw.text((x0, y0 + (NORMAL_SIZE[1] + 1) * scale), f"U+{ord(ch):04X}", fill=(80, 80, 80))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path


def prepare_korean_font_patch(
    font_zip_path: Path,
    work_dir: Path,
    game: str,
    entries: list[dict] | None = None,
    rom_path: Path | None = None,
) -> tuple[Path, Path, KoreanFontBuildResult]:
    """Create a work-tree copy of Pokemon_GBA_Font_Patch with Korean assets."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    source_root = get_resource_path("Pokemon_GBA_Font_Patch")
    patch_root = work_dir / "Pokemon_GBA_Font_Patch_ko"
    assets_dir = work_dir / "korean_font_assets"

    if patch_root.exists():
        shutil.rmtree(patch_root)
    shutil.copytree(source_root, patch_root)

    result = generate_korean_font_assets(Path(font_zip_path), assets_dir, entries=entries)
    install_korean_assets(result.output_dir, patch_root, game)
    if rom_path is not None:
        relocate_korean_font_patch(patch_root, Path(rom_path), game, result)

    subdir = "pokeE" if game == "emerald" else "pokeFRLG"
    return patch_root, patch_root / subdir / "PMRSEFRLG_charmap.txt", result


def relocate_korean_font_patch(
    patch_root: Path,
    rom_path: Path,
    game: str,
    font_result: KoreanFontBuildResult,
) -> tuple[int, int]:
    """Move Korean FRLG font patch symbols into an actually-free ROM block.

    The upstream Chinese patch uses hardcoded addresses near 0x01FD3000.
    Many 32MB ROM hacks already store data there. For Korean builds we can
    place the hook code and generated font assets anywhere in ROM space, so
    choose the end of the largest 0xFF block and keep the earlier bytes free
    for relocated text.
    """
    if game not in {"firered", "leafgreen"}:
        return (0, 0)

    rom = Path(rom_path).read_bytes()
    hook_size = 0x5C4
    total_size = hook_size + _font_payload_size(font_result)
    block_start, block_end = _find_largest_free_block(rom, start=0x01000000, end=0x02000000)
    if block_end - block_start < total_size:
        raise RuntimeError(
            f"Not enough free space for Korean font patch: need {total_size:,} bytes, "
            f"largest block has {block_end - block_start:,} bytes"
        )

    patch_start = (block_end - total_size) & ~3
    font_start = patch_start + hook_size
    symbols_path = Path(patch_root) / "pokeFRLG" / "include" / "hackSymbols_FR.s"
    symbols_path.write_text(
        "; Auto-generated by Meowth Korean font patch builder\n"
        ";HackFunctionAddress\n"
        f"HackFunctionAddresses                   equ 0x{0x08000000 + patch_start:08X}\n"
        f"ChineseFontAndPunctuationAddresses      equ 0x{0x08000000 + font_start:08X}\n",
        encoding="utf-8",
    )
    return patch_start, font_start


def install_korean_assets(assets_dir: Path, patch_root: Path, game: str) -> None:
    """Install generated Korean assets into a copied font patch tree."""
    assets_dir = Path(assets_dir)
    patch_root = Path(patch_root)
    subdir = "pokeE" if game == "emerald" else "pokeFRLG"
    target = patch_root / subdir

    font_dir = target / ("graphics/fonts" if game == "emerald" else "graphic/fonts")
    shutil.copy2(assets_dir / "PMRSEFRLG_charmap.txt", target / "PMRSEFRLG_charmap.txt")
    shutil.copy2(assets_dir / "gba_chs_font_11x11.bin", font_dir / "gba_chs_font_11x11.bin")
    shutil.copy2(assets_dir / "gba_chs_font_9x9.bin", font_dir / "gba_chs_font_9x9.bin")
    shutil.copy2(
        assets_dir / "gba_chs_punctuation_11x11.bin",
        font_dir / "gba_chs_punctuation_11x11.bin",
    )
    shutil.copy2(
        assets_dir / "gba_chs_punctuation_9x9.bin",
        font_dir / "gba_chs_punctuation_9x9.bin",
    )
    license_path = assets_dir / "Galmuri-OFL-LICENSE.txt"
    if license_path.exists():
        shutil.copy2(license_path, patch_root / "Galmuri-OFL-LICENSE.txt")


def _font_payload_size(font_result: KoreanFontBuildResult) -> int:
    return (
        font_result.normal_punctuation_path.stat().st_size
        + font_result.normal_font_path.stat().st_size
        + font_result.small_punctuation_path.stat().st_size
        + font_result.small_font_path.stat().st_size
    )


def _find_largest_free_block(rom: bytes, start: int, end: int) -> tuple[int, int]:
    end = min(end, len(rom))
    pos = min(start, end)
    best_start = end
    best_end = end
    while pos < end:
        if rom[pos] != 0xFF:
            pos += 1
            continue
        block_start = pos
        while pos < end and rom[pos] == 0xFF:
            pos += 1
        if pos - block_start > best_end - best_start:
            best_start = block_start
            best_end = pos
    return best_start, best_end


def _build_font_bin(font: BdfFont, chars: list[str], size: tuple[int, int], glyph_size: int) -> bytes:
    data = bytearray()
    for ch in chars:
        data.extend(_pack_bitmap(font.render(ch, *size), glyph_size))
    empty = b"\x00" * glyph_size
    data.extend(empty * (MAX_KOREAN_GLYPHS - len(chars)))
    return bytes(data)


def _build_punctuation_bin(font: BdfFont, size: tuple[int, int], glyph_size: int) -> bytes:
    data = bytearray()
    for ch in PUNCTUATION_CHARS:
        data.extend(_pack_bitmap(font.render(ch, *size), glyph_size))
    return bytes(data)


def _pack_bitmap(bitmap: list[list[int]], glyph_size: int) -> bytes:
    bits = [bit for row in bitmap for bit in row]
    data = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit in bits[i : i + 8]:
            byte = (byte << 1) | (1 if bit else 0)
        byte <<= max(0, 8 - len(bits[i : i + 8]))
        data.append(byte)
    if len(data) < glyph_size:
        data.extend(b"\x00" * (glyph_size - len(data)))
    return bytes(data[:glyph_size])


def _unpack_bitmap(data: bytes, width: int, height: int) -> list[list[int]]:
    bits: list[int] = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return [bits[i * width : (i + 1) * width] for i in range(height)]


def _build_charmap(chars: list[str]) -> str:
    base_path = get_resource_path("Pokemon_GBA_Font_Patch/pokeFRLG/PMRSEFRLG_charmap.txt")
    lines: list[str] = []
    punctuation = dict(zip(PUNCTUATION_CODES, PUNCTUATION_CHARS))

    for raw in base_path.read_text(encoding="utf-8").splitlines():
        if "=" not in raw:
            continue
        hex_part, char_part = raw.split("=", 1)
        try:
            code = int(hex_part, 16)
        except ValueError:
            continue
        if code in punctuation:
            continue
        if code <= 0xFF or char_part.startswith("{"):
            lines.append(raw)

    for code, ch in punctuation.items():
        lines.append(f"{code:02X}={ch}")

    for code, ch in zip(_korean_codes(), chars):
        lines.append(f"{code:04X}={ch}")

    return "\n".join(lines) + "\n"


def _read_generated_chars(charmap_path: Path) -> list[str]:
    chars: list[str] = []
    for raw in charmap_path.read_text(encoding="utf-8").splitlines():
        if "=" not in raw:
            continue
        hex_part, ch = raw.split("=", 1)
        try:
            code = int(hex_part, 16)
        except ValueError:
            continue
        if code >= 0x0100 and len(ch) == 1:
            chars.append(ch)
    return chars


def _copy_galmuri_license(font_zip_path: Path, output_dir: Path) -> None:
    with zipfile.ZipFile(font_zip_path) as zf:
        try:
            license_text = zf.read("LICENSE.txt").decode("utf-8")
        except KeyError:
            return
    (output_dir / "Galmuri-OFL-LICENSE.txt").write_text(license_text, encoding="utf-8")


def _korean_codes() -> list[int]:
    codes: list[int] = []
    for hi in KOREAN_HIGH_BYTES:
        max_low = 0x5D if hi == 0x1E else 0xF6
        for lo in range(max_low + 1):
            codes.append((hi << 8) | lo)
            if len(codes) >= MAX_KOREAN_GLYPHS:
                return codes
    return codes


def _needs_glyph(ch: str) -> bool:
    if ch.isspace() or ch.isascii():
        return False
    code = ord(ch)
    return (
        0xAC00 <= code <= 0xD7A3
        or 0x3130 <= code <= 0x318F
        or 0x1100 <= code <= 0x11FF
        or 0x3000 <= code <= 0x303F
        or 0xFF00 <= code <= 0xFFEF
    )


def _iter_pokeapi_korean_chars() -> list[str]:
    base = get_resource_path("pokeapi/data/v2/csv")
    files = [
        "pokemon_species_names.csv",
        "move_names.csv",
        "ability_names.csv",
        "item_names.csv",
        "type_names.csv",
        "nature_names.csv",
        "location_names.csv",
        "region_names.csv",
    ]
    chars: list[str] = []
    for filename in files:
        path = base / filename
        if not path.exists():
            continue
        with path.open(encoding="utf-8", newline="") as fp:
            for row in csv.DictReader(fp):
                if row.get("local_language_id") == "3":
                    chars.extend(row.get("name", ""))
    return chars
