"""
ROM 字库补丁配置模板系统。

对于不同的 ROM，用户可以创建配置文件来指定函数地址。
"""

import json
from pathlib import Path
from typing import Dict, Any


# 预设配置（已知的 ROM）
PRESET_CONFIGS = {
    # 原版绿宝石
    "BPEE_vanilla": {
        "name": "Pokemon Emerald (US)",
        "game_code": "BPEE",
        "addresses": {
            "AgbMain": 0x080003A4,
            "DecompressGlyphTile": 0x08004C10,
            "gCurGlyph": 0x03002F90,
        },
        "free_space": 0x09FD0000,
    },
    # 原版火红
    "BPRE_vanilla": {
        "name": "Pokemon FireRed (US)",
        "game_code": "BPRE",
        "addresses": {
            "AgbMain": 0x08000290,
            "DecompressGlyphTile": 0x08003C10,
        },
        "free_space": 0x09FD3000,
    },
    # pokeemerald-expansion (示例)
    "BPEE_expansion_v1.9": {
        "name": "pokeemerald-expansion v1.9.x",
        "game_code": "BPEE",
        "addresses": {
            # 这些地址需要用户自己找
            "AgbMain": None,  # 用户需要填写
            "DecompressGlyphTile": None,
        },
        "free_space": 0x09FD0000,
        "notes": "expansion 改版需要手动查找函数地址",
    },
}


class RomConfig:
    """ROM 配置管理"""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}

        if config_path and config_path.exists():
            self.load(config_path)

    def load(self, path: Path):
        """加载配置文件"""
        with open(path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

    def save(self, path: Path):
        """保存配置文件"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get_preset(self, preset_name: str) -> Dict[str, Any]:
        """获取预设配置"""
        if preset_name not in PRESET_CONFIGS:
            raise ValueError(f"未知的预设: {preset_name}")
        return PRESET_CONFIGS[preset_name].copy()

    def create_template(self, rom_name: str, game_code: str) -> Dict[str, Any]:
        """创建配置模板"""
        return {
            "name": rom_name,
            "game_code": game_code,
            "addresses": {
                "AgbMain": None,
                "DecompressGlyphTile": None,
                "gCurGlyph": None,
            },
            "free_space": 0x09FD0000,
            "notes": "请使用 IDA/Ghidra 等工具查找函数地址",
        }

    def validate(self) -> bool:
        """验证配置是否完整"""
        required_fields = ["addresses", "free_space"]

        for field in required_fields:
            if field not in self.config:
                return False

        # 检查关键地址是否已填写
        if not self.config["addresses"].get("AgbMain"):
            return False

        return True


def generate_config_for_rom(rom_path: Path, output_path: Path):
    """
    为 ROM 生成配置模板。

    用户需要手动填写函数地址。
    """
    # 读取游戏代码
    with open(rom_path, 'rb') as f:
        f.seek(0xAC)
        game_code = f.read(4).decode('ascii', errors='ignore')

    # 创建配置
    config = RomConfig()
    template = config.create_template(rom_path.name, game_code)

    # 保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)

    print(f"✅ 配置模板已生成: {output_path}")
    print("\n请按以下步骤操作:")
    print("1. 使用 IDA Pro 或 Ghidra 打开 ROM")
    print("2. 查找以下函数的地址:")
    print("   - AgbMain (主函数)")
    print("   - DecompressGlyphTile (字符渲染)")
    print("3. 将地址填入配置文件")
    print("4. 运行: meowth full rom.gba --config config.json")


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  生成配置模板: python rom_config.py <rom_path>")
        print("  查看预设: python rom_config.py --list-presets")
        sys.exit(1)

    if sys.argv[1] == '--list-presets':
        print("可用的预设配置:")
        for name, cfg in PRESET_CONFIGS.items():
            print(f"\n  {name}:")
            print(f"    名称: {cfg['name']}")
            print(f"    游戏代码: {cfg['game_code']}")
    else:
        rom_path = Path(sys.argv[1])
        output_path = rom_path.with_suffix('.config.json')
        generate_config_for_rom(rom_path, output_path)
