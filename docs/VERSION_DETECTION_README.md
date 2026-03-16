# 版本支持和 Decomp ROM 检测功能

## 概述

Meowth GBA Translator 现在支持第三代宝可梦的所有版本，并能自动检测和处理 decomp ROM。

## 支持的版本

| 游戏 | 游戏代码 | 状态 |
|------|---------|------|
| 火红 (FireRed) | BPRE | ✅ 完全支持 |
| 叶绿 (LeafGreen) | BPGE | ✅ 完全支持 |
| 绿宝石 (Emerald) | BPEE | ✅ 完全支持 |
| 红宝石 (Ruby) | AXVE | ✅ 完全支持 |
| 蓝宝石 (Sapphire) | AXPE | ✅ 完全支持 |

## 自动版本检测

工具会自动检测 ROM 版本，无需手动指定：

```bash
# 自动检测版本并翻译
meowth full pokemon.gba --target zh-Hans
```

## Decomp ROM 检测

### 什么是 Decomp ROM？

Decomp ROM 是从源代码编译的 ROM（如 pokeemerald、pokefirered），与原版 binary ROM 结构不同。

### 智能检测

工具会自动检测 decomp ROM，并在需要时报错：

```bash
# Binary ROM 翻译到中文 - ✅ 正常工作
meowth full pokemon_firered.gba --target zh-Hans

# Decomp ROM 翻译到中文 - ❌ 自动检测并报错
meowth full pokeemerald.gba --target zh-Hans
# 输出: 错误：检测到这是一个 decomp ROM...

# Decomp ROM 翻译到其他拉丁语言 - ✅ 正常工作
meowth full pokeemerald.gba --source en --target es
```

### 为什么要检测？

- **CJK 语言**（中文、日文、韩文）需要注入字库
- **Decomp ROM** 无法使用字库注入
- **提前检测**避免浪费翻译 API 调用

### 检测逻辑

| 目标语言 | ROM 类型 | 结果 |
|---------|---------|------|
| 中文/日文/韩文 | Binary ROM | ✅ 可以翻译 |
| 中文/日文/韩文 | Decomp ROM | ❌ 报错终止 |
| 其他拉丁语言 | Binary ROM | ✅ 可以翻译 |
| 其他拉丁语言 | Decomp ROM | ✅ 可以翻译 |

## 测试工具

### 检测 ROM 类型

```bash
python test_version_detection.py pokemon.gba
```

输出示例：
```
=== Testing ROM: pokemon_emerald.gba ===

Detected game: emerald
Is decomp ROM: False

✅ This is a binary ROM
Can be translated to any language
```

### 完整示例

```bash
python example_version_detection.py pokemon.gba zh-Hans
```

## API 使用

### Python API

```python
from pathlib import Path
from meowth.core.engine import detect_game, is_decomp_rom
from meowth.languages import is_cjk_language

# 检测游戏版本
game = detect_game(Path("pokemon.gba"))
print(f"Game: {game}")  # 输出: Game: firered

# 检测是否为 decomp ROM
is_decomp = is_decomp_rom(Path("pokemon.gba"))
print(f"Is decomp: {is_decomp}")  # 输出: Is decomp: False

# 检查兼容性
target_lang = "zh-Hans"
if is_cjk_language(target_lang) and is_decomp:
    print("Error: Cannot translate decomp ROM to CJK languages")
else:
    print("Compatible!")
```

### 完整翻译流程

```python
from pathlib import Path
from meowth.core import TranslationConfig, TranslationEngine, TranslationCallbacks

# 配置
config = TranslationConfig(
    source_lang="en",
    target_lang="zh-Hans",
    rom_path=Path("pokemon_firered.gba"),
    output_dir=Path("outputs"),
    work_dir=Path("work"),
)

# 创建引擎（会自动检测版本和 decomp ROM）
engine = TranslationEngine(config, TranslationCallbacks())

# 运行翻译（如果是 decomp ROM 且目标是中文，会自动报错）
try:
    output = engine.run_full()
    print(f"Success: {output}")
except RuntimeError as e:
    print(f"Error: {e}")
```

## 常见问题

### Q: 我的改版 ROM 被误判为 decomp ROM 怎么办？

A: 如果你的 binary 改版包含了 decomp 相关字符串，可能会被误判。请报告这个问题。

### Q: 我想翻译 decomp ROM 到中文，有什么办法？

A: 你需要在 decomp 源码中添加中文字库支持，然后修改源码文本并重新编译。

### Q: 为什么拉丁语言之间的翻译不检查 decomp ROM？

A: 因为拉丁语言使用相同的字符集，不需要注入新字库，只需要替换文本内容。

## 技术文档

详细技术文档请参考：
- [VERSION_SUPPORT.md](docs/VERSION_SUPPORT.md) - 版本支持和检测详解
- [CHANGELOG_VERSION_SUPPORT.md](CHANGELOG_VERSION_SUPPORT.md) - 更新日志

## 贡献

如果你发现检测逻辑有问题，或者有新的 decomp ROM 特征需要添加，欢迎提交 Issue 或 PR。
