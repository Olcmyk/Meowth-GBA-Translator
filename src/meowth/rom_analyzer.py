"""Analyze GBA ROM to find function addresses for font patch."""

from pathlib import Path
import struct


class RomAnalyzer:
    """Analyze GBA ROM to locate key functions for font patching."""

    def __init__(self, rom_path: Path):
        self.rom_path = rom_path
        with open(rom_path, 'rb') as f:
            self.rom_data = f.read()

    def find_agb_main(self) -> int | None:
        """
        查找 AgbMain 函数地址。

        特征：
        - 位于 ROM 开头附近（通常 0x080003A0 - 0x08000500）
        - ARM 代码段
        - 包含初始化序列
        """
        # 搜索范围：0x300 - 0x600
        for offset in range(0x300, 0x600, 4):
            # 读取 4 字节指令
            if offset + 4 > len(self.rom_data):
                break

            instr = struct.unpack('<I', self.rom_data[offset:offset+4])[0]

            # 查找特征指令序列（AgbMain 的开头通常是 push {r4-r7,lr}）
            # ARM: 0xE92D4xxx 或 THUMB: 0xB5xx
            if (instr & 0xFFFF0000) == 0xB500_0000:  # THUMB push
                # 验证后续指令是否合理
                if self._validate_function_start(offset):
                    return 0x08000000 + offset

        return None

    def find_decompress_glyph_tile(self) -> int | None:
        """
        查找 DecompressGlyphTile 函数。

        特征：
        - 处理字符渲染
        - 通常在 0x08004000 - 0x08006000 范围
        """
        # 搜索字符串 "DecompressGlyphTile" 的引用
        # 或搜索特征字节序列
        for offset in range(0x4000, 0x6000, 2):
            if offset + 20 > len(self.rom_data):
                break

            # 查找 THUMB 函数特征
            chunk = self.rom_data[offset:offset+20]
            if self._is_glyph_function(chunk):
                return 0x08000000 + offset

        return None

    def find_free_space(self, size: int, start: int = 0x01000000) -> int | None:
        """
        查找 ROM 中的空闲空间。

        Args:
            size: 需要的字节数
            start: 开始搜索的地址（默认 16MB 处）

        Returns:
            空闲空间的地址，如果找不到返回 None
        """
        # 转换为 ROM 偏移
        offset = start - 0x08000000

        # 搜索连续的 0xFF 字节
        consecutive_ff = 0
        start_offset = None

        for i in range(offset, len(self.rom_data)):
            if self.rom_data[i] == 0xFF:
                if consecutive_ff == 0:
                    start_offset = i
                consecutive_ff += 1

                if consecutive_ff >= size:
                    return 0x08000000 + start_offset
            else:
                consecutive_ff = 0
                start_offset = None

        return None

    def is_expansion_rom(self) -> bool:
        """
        检测 ROM 是否为 pokeemerald-expansion 编译的。

        特征：
        - 包含 expansion 特有的字符串
        - 特定的编译器签名
        """
        # 搜索特征字符串
        expansion_markers = [
            b'pokeemerald-expansion',
            b'RHH_EXPANSION',
            b'BATTLE_ENGINE',
            b'P_UPDATED_',
        ]

        for marker in expansion_markers:
            if marker in self.rom_data:
                return True

        return False

    def get_game_code(self) -> str:
        """获取游戏代码（BPEE/BPRE/BPGE 等）"""
        # ROM 头部 0xAC-0xAF 是游戏代码
        if len(self.rom_data) < 0xB0:
            return "UNKNOWN"

        game_code = self.rom_data[0xAC:0xB0].decode('ascii', errors='ignore')
        return game_code

    def generate_font_patch_config(self) -> dict:
        """
        生成字库补丁配置。

        Returns:
            包含函数地址和空闲空间的配置字典
        """
        config = {
            'game_code': self.get_game_code(),
            'is_expansion': self.is_expansion_rom(),
            'agb_main': self.find_agb_main(),
            'decompress_glyph_tile': self.find_decompress_glyph_tile(),
            'free_space': self.find_free_space(0x100000),  # 1MB 空闲空间
        }

        return config

    def _validate_function_start(self, offset: int) -> bool:
        """验证是否为有效的函数开头"""
        # 简单验证：检查后续 16 字节是否为合理的代码
        if offset + 16 > len(self.rom_data):
            return False

        chunk = self.rom_data[offset:offset+16]

        # 不应该全是 0x00 或 0xFF
        if chunk == b'\x00' * 16 or chunk == b'\xFF' * 16:
            return False

        return True

    def _is_glyph_function(self, chunk: bytes) -> bool:
        """检测是否为字符渲染函数"""
        # 这里需要根据实际的字符渲染函数特征来实现
        # 简化版本：检查是否包含特定的指令模式
        return False  # TODO: 实现实际的检测逻辑


def analyze_rom(rom_path: Path) -> dict:
    """分析 ROM 并返回配置"""
    analyzer = RomAnalyzer(rom_path)
    return analyzer.generate_font_patch_config()


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python rom_analyzer.py <rom_path>")
        sys.exit(1)

    rom_path = Path(sys.argv[1])
    config = analyze_rom(rom_path)

    print("ROM 分析结果:")
    print(f"  游戏代码: {config['game_code']}")
    print(f"  是否 Expansion: {config['is_expansion']}")
    print(f"  AgbMain 地址: {hex(config['agb_main']) if config['agb_main'] else 'Not found'}")
    print(f"  DecompressGlyphTile: {hex(config['decompress_glyph_tile']) if config['decompress_glyph_tile'] else 'Not found'}")
    print(f"  空闲空间: {hex(config['free_space']) if config['free_space'] else 'Not found'}")
