"""Generate dynamic font patch configuration for any ROM."""

from pathlib import Path
from .rom_analyzer import analyze_rom
from .resource_path import get_resource_path


def generate_dynamic_patch(rom_path: Path, output_dir: Path) -> Path:
    """
    为任意 ROM 生成适配的字库补丁配置。

    Args:
        rom_path: ROM 文件路径
        output_dir: 输出目录

    Returns:
        生成的 .asm 文件路径
    """
    # 分析 ROM
    config = analyze_rom(rom_path)

    if not config['agb_main']:
        raise RuntimeError("无法找到 AgbMain 函数，ROM 可能已损坏或不支持")

    # 生成 armips 配置文件
    asm_content = f"""; 自动生成的字库补丁配置
; ROM: {rom_path.name}
; 游戏代码: {config['game_code']}
; 是否 Expansion: {config['is_expansion']}

.gba
.open "{rom_path}",0x08000000

; 加载字符映射表
.loadtable "./PMRSEFRLG_charmap.txt"

; ===== 动态检测的函数地址 =====
.definelabel AgbMain, {hex(config['agb_main']) if config['agb_main'] else '0x080003A4'}
.definelabel DecompressGlyphTile, {hex(config['decompress_glyph_tile']) if config['decompress_glyph_tile'] else '0x08004C10'}

; ===== 字库数据存放地址 =====
.definelabel HackFunctionAddresses, {hex(config['free_space']) if config['free_space'] else '0x09FD0000'}

; ===== 注入字库代码 =====
.thumb
.include "./src/HookInOrigin/text.s"

; ===== 字库渲染函数 =====
.org HackFunctionAddresses
.thumb
.include "./src/HackFunction/text.s"

.close
"""

    # 保存配置文件
    output_dir.mkdir(parents=True, exist_ok=True)
    asm_path = output_dir / f"dynamic_patch_{config['game_code']}.asm"

    with open(asm_path, 'w', encoding='utf-8') as f:
        f.write(asm_content)

    return asm_path


def apply_dynamic_font_patch(
    rom_path: Path,
    output_path: Path,
    armips_path: Path,
    work_dir: Path,
) -> Path:
    """
    自动分析 ROM 并应用适配的字库补丁。

    这个函数会：
    1. 分析 ROM 找到关键函数地址
    2. 生成适配的 armips 配置
    3. 应用字库补丁

    Args:
        rom_path: 原始 ROM
        output_path: 输出 ROM
        armips_path: armips 可执行文件
        work_dir: 工作目录

    Returns:
        输出 ROM 路径
    """
    import subprocess
    import shutil

    # 生成动态配置
    asm_path = generate_dynamic_patch(rom_path, work_dir)

    # 复制必要的文件到工作目录
    patch_root = get_resource_path("Pokemon_GBA_Font_Patch")

    # 复制 charmap
    shutil.copy2(
        patch_root / "pokeE" / "PMRSEFRLG_charmap.txt",
        work_dir / "PMRSEFRLG_charmap.txt"
    )

    # 复制源码目录
    for src_dir in ["src", "include"]:
        src_path = patch_root / "pokeE" / src_dir
        dst_path = work_dir / src_dir
        if src_path.exists():
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)

    # 运行 armips
    result = subprocess.run(
        [str(armips_path), str(asm_path)],
        cwd=str(work_dir),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"armips 失败:\n{result.stderr}\n{result.stdout}")

    # 输出文件应该已经被 armips 修改
    # 复制到最终输出位置
    shutil.copy2(rom_path, output_path)

    return output_path
