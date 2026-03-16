# 版本支持和 Decomp ROM 检测

## 支持的游戏版本

Meowth GBA Translator 现在支持第三代宝可梦的所有版本：

### 火红/叶绿 (FireRed/LeafGreen)
- **游戏代码**: BPRE (火红), BPGE (叶绿)
- **字库补丁**: pokeFRLG
- **支持状态**: ✅ 完全支持

### 绿宝石 (Emerald)
- **游戏代码**: BPEE
- **字库补丁**: pokeE
- **支持状态**: ✅ 完全支持

### 红宝石/蓝宝石 (Ruby/Sapphire)
- **游戏代码**: AXVE (红宝石), AXPE (蓝宝石)
- **字库补丁**: pokeRS
- **支持状态**: ✅ 完全支持

## 自动版本检测

工具会自动检测 ROM 的版本：

```python
from meowth.core.engine import detect_game

game = detect_game("pokemon.gba")
print(f"检测到的游戏: {game}")
```

检测基于 ROM 头部的游戏代码（偏移 0xAC-0xAF）。

## Decomp ROM 检测

### 什么是 Decomp ROM？

Decomp ROM 是从源代码编译的 ROM，例如：
- pokeemerald
- pokefirered
- pokeemerald-expansion

这些 ROM 与原版 binary ROM 的内部结构不同。

### 为什么要检测 Decomp ROM？

当翻译目标语言是中文（或其他 CJK 语言）时，需要注入字库。但是：

- **Binary ROM**: 可以通过字库补丁注入中文字库 ✅
- **Decomp ROM**: 无法使用字库注入，必须在源码中添加字库支持 ❌

### 自动检测和错误提示

当检测到 decomp ROM 且目标语言是中文时，工具会自动报错并终止：

```
错误：检测到这是一个 decomp ROM（源码编译版本），而非 binary ROM。
Decomp ROM 无法使用字库注入功能，因此无法翻译成中文。

如果您想翻译 decomp ROM，请：
1. 直接修改源代码中的文本
2. 在源码中添加中文字库支持
3. 重新编译 ROM

本工具仅支持 binary ROM（原版或基于原版的二进制改版）。
```

### 检测方法

工具通过以下方式检测 decomp ROM：

1. **检查 decomp 标识字符串**:
   - `pokeemerald`
   - `pokefirered`
   - `pokeleafgreen`
   - `pokeruby`
   - `pokesapphire`
   - `pret/`
   - `expansion`

2. **检查 ROM 大小**: Decomp ROM 通常不是标准的 8MB/16MB/32MB

3. **检查游戏标题**: Decomp ROM 可能有自定义标题

### 拉丁语言之间的翻译

如果翻译目标不是 CJK 语言（例如英语→西班牙语），则不需要字库注入，因此：

- ✅ Binary ROM 可以翻译
- ✅ Decomp ROM 也可以翻译

工具只在需要字库注入时才检查 decomp ROM。

## 使用示例

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

### 翻译 Binary ROM 到中文

```bash
meowth full pokemon_firered.gba --target zh-Hans
```

工具会：
1. 检测版本（firered）
2. 检测是否为 decomp ROM（否）
3. 继续翻译流程
4. 注入中文字库

### 尝试翻译 Decomp ROM 到中文

```bash
meowth full pokeemerald.gba --target zh-Hans
```

工具会：
1. 检测版本（emerald）
2. 检测是否为 decomp ROM（是）
3. **报错并终止**，提示用户这是 decomp ROM

### 翻译 Decomp ROM 到其他拉丁语言

```bash
meowth full pokeemerald.gba --source en --target es
```

工具会：
1. 检测版本（emerald）
2. 检测目标语言（西班牙语，非 CJK）
3. **跳过 decomp 检测**
4. 继续翻译流程（不需要字库注入）

## 技术细节

### 字库边界配置

不同版本的字库补丁使用不同的内存边界：

```python
_FONT_BOUNDARIES = {
    "firered": 0x01FD3000,
    "leafgreen": 0x01FD3000,
    "emerald": 0x01FD0000,
    "ruby": 0x01FD0000,
    "sapphire": 0x01FD0000,
}
```

### 字库补丁配置

每个版本使用不同的 ASM 文件和输出文件：

```python
_GAME_CONFIG = {
    "firered": {"subdir": "pokeFRLG", "asm": "main_FR.asm", ...},
    "leafgreen": {"subdir": "pokeFRLG", "asm": "main_FR.asm", ...},
    "emerald": {"subdir": "pokeE", "asm": "main_E.asm", ...},
    "ruby": {"subdir": "pokeRS", "asm": "main_R.asm", ...},
    "sapphire": {"subdir": "pokeRS", "asm": "main_S.asm", ...},
}
```

## 常见问题

### Q: 我的改版 ROM 被误判为 decomp ROM 怎么办？

A: 如果你的 binary 改版 ROM 包含了 decomp 相关的字符串（例如在文本中提到了 "pokeemerald"），可能会被误判。请联系开发者报告这个问题。

### Q: 我想翻译 decomp ROM 到中文，有什么办法？

A: 你需要：
1. 在 decomp 源码中添加中文字库支持
2. 修改源码中的文本为中文
3. 重新编译 ROM

或者，你可以先编译成 binary ROM，然后使用本工具翻译。

### Q: 为什么拉丁语言之间的翻译不检查 decomp ROM？

A: 因为拉丁语言使用相同的字符集（ASCII/Latin-1），不需要注入新的字库。工具只需要替换文本内容，不需要修改字库相关的代码。
