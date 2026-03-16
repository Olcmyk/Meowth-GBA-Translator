# 更新日志 - 版本支持扩展和 Decomp ROM 检测

## 新增功能

### 1. 完整的第三代版本支持

现在支持所有第三代宝可梦游戏：

- ✅ 火红 (FireRed) - BPRE
- ✅ 叶绿 (LeafGreen) - BPGE
- ✅ 绿宝石 (Emerald) - BPEE
- ✅ 红宝石 (Ruby) - AXVE
- ✅ 蓝宝石 (Sapphire) - AXPE

#### 技术实现

1. **字库补丁配置** (`src/meowth/font_patch.py`):
   - 为红宝石和蓝宝石添加了字库补丁配置
   - 使用 `pokeRS` 目录下的 `main_R.asm` 和 `main_S.asm`

2. **字库边界配置** (`src/meowth/rom_writer.py`):
   - 为红宝石和蓝宝石添加了字库边界地址 `0x01FD0000`

3. **自动版本检测** (`src/meowth/core/engine.py`):
   - `detect_game()` 函数已支持所有5个版本
   - 基于 ROM 头部 0xAC-0xAF 的游戏代码自动识别

### 2. Decomp ROM 检测

新增 `is_decomp_rom()` 函数，用于检测 ROM 是否为源码编译版本。

#### 检测方法

1. **字符串检测**: 扫描 ROM 前 2MB，查找 decomp 标识：
   - `pokeemerald`
   - `pokefirered`
   - `pokeleafgreen`
   - `pokeruby`
   - `pokesapphire`
   - `pret/`
   - `expansion`

2. **ROM 大小检测**: 检查是否为非标准大小（不是 8MB/16MB/32MB）

3. **游戏标题检测**: 检查是否有自定义标题（不以 "POKEMON" 开头）

#### 智能错误处理

- **翻译到 CJK 语言时**: 如果检测到 decomp ROM，立即报错并终止
  ```
  错误：检测到这是一个 decomp ROM（源码编译版本），而非 binary ROM。
  Decomp ROM 无法使用字库注入功能，因此无法翻译成中文。
  ```

- **翻译到拉丁语言时**: 不检查 decomp ROM，因为不需要字库注入

#### 使用场景

```bash
# Binary ROM 翻译到中文 - ✅ 正常工作
meowth full pokemon_firered.gba --target zh-Hans

# Decomp ROM 翻译到中文 - ❌ 报错终止
meowth full pokeemerald.gba --target zh-Hans

# Decomp ROM 翻译到西班牙语 - ✅ 正常工作（不需要字库）
meowth full pokeemerald.gba --source en --target es
```

## 修改的文件

### 核心引擎
- `src/meowth/core/engine.py`
  - 新增 `is_decomp_rom()` 函数
  - 在 `build_rom()` 中添加 decomp 检测
  - 在 `run_full()` 中添加 decomp 检测

### 字库补丁
- `src/meowth/font_patch.py`
  - 为红宝石添加配置：`main_R.asm` -> `chsfontrom_R.gba`
  - 为蓝宝石添加配置：`main_S.asm` -> `chsfontrom_S.gba`

### ROM 写入器
- `src/meowth/rom_writer.py`
  - 为红宝石和蓝宝石添加字库边界 `0x01FD0000`

### 向后兼容
- `src/meowth/pipeline.py`
  - 导出 `is_decomp_rom` 函数以保持向后兼容

## 测试工具

### 版本检测测试
```bash
python test_version_detection.py <rom_path>
```

输出示例：
```
=== Testing ROM: pokemon_emerald.gba ===

Detected game: emerald
Is decomp ROM: False

✅ This is a binary ROM
Can be translated to any language
```

## 文档

新增文档 `docs/VERSION_SUPPORT.md`，包含：
- 支持的游戏版本列表
- 自动版本检测说明
- Decomp ROM 检测原理
- 使用示例和常见问题

## 用户体验改进

### 避免浪费翻译 API 调用

在开始翻译之前就检测 decomp ROM，避免用户：
1. 等待文本提取完成
2. 消耗 API 额度进行翻译
3. 在最后构建 ROM 时才发现无法注入字库

现在会在流程开始时就报错，节省时间和成本。

### 清晰的错误提示

错误信息包含：
- 问题说明（这是 decomp ROM）
- 原因解释（无法注入字库）
- 解决方案（修改源码或使用 binary ROM）

### 智能判断

只在需要字库注入时才检查 decomp ROM，不影响拉丁语言之间的翻译。

## 技术细节

### CJK 语言判断

使用 `is_cjk_language()` 函数判断目标语言：
- 中文（zh-Hans, zh-Hant）
- 日文（ja）
- 韩文（ko）

这些语言需要字库注入，因此需要检查 decomp ROM。

### 检测时机

1. **`run_full()` 开始时**: 在提取文本之前检测
2. **`build_rom()` 开始时**: 在构建 ROM 之前检测

双重检测确保无论使用哪个入口点都能正确处理。

## 向后兼容性

所有改动都是向后兼容的：
- 现有的 API 没有改变
- 新增的检测不影响现有功能
- 只在需要时才触发错误

## 未来改进

可能的改进方向：
1. 添加配置选项跳过 decomp 检测（高级用户）
2. 支持更多 decomp ROM 的检测特征
3. 提供 decomp ROM 的字库注入指南
