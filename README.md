# Meowth-GBA-Translator

**AI 驱动的 GBA 宝可梦 ROM 自动翻译工具** — 一键将英文宝可梦改版翻译为简体中文。

> 利用 LLM（DeepSeek）+ HexManiacAdvance 实现全自动文本提取、翻译、注入，无需手动汉化经验。

[English](#english) | [中文](#中文)

---

## 中文

### 功能特性

- **一键翻译**：输入英文 ROM，输出中文 ROM，全流程自动化
- **AI 翻译**：使用 DeepSeek API 进行高质量游戏文本翻译，保持宝可梦风格语气
- **官方术语**：集成 PokeAPI 数据库，宝可梦名、招式名、特性名等使用官方简中译名
- **智能提取**：基于 HexManiacAdvance 自动发现 ROM 表结构，无需硬编码偏移量
- **控制码保护**：自动保护 `\n`、`\p`、`[player]`、`[rival]` 等游戏控制码不被翻译破坏
- **指针重定向**：翻译后文本超长时自动 repoint 到 ROM 扩展区域，不会覆盖游戏数据
- **中文字库注入**：自动应用 Font Patch，注入 11×11 中文字库和渲染引擎
- **本地缓存**：翻译结果 MD5 缓存，断点续传，避免重复调用 API 浪费费用
- **多游戏支持**：支持第三世代全部主要宝可梦游戏

### 支持的游戏

| 游戏 | ROM 代码 | 状态 |
|------|----------|------|
| 宝可梦 火红 (FireRed) | BPRE | ✅ 完全支持 |
| 宝可梦 叶绿 (LeafGreen) | BPGE | ✅ 支持 |
| 宝可梦 绿宝石 (Emerald) | BPEE | ✅ 完全支持 |
| 宝可梦 红宝石 (Ruby) | AXVE | ✅ 支持 |
| 宝可梦 蓝宝石 (Sapphire) | AXPE | ✅ 支持 |

> 理论上支持所有基于以上游戏的改版 ROM（ROM Hack）。

### 技术架构

```
原始 ROM (.gba, 16MB)
  │
  ├─ [C# MeowthBridge] ──→ texts.json（文本 + 指针地址 + 类别）
  │   └─ HexManiacAdvance 自动发现表结构 + loadpointer 扫描
  │
  ├─ [Python translate] ──→ texts_translated.json
  │   ├─ PokeAPI 术语表查表替换
  │   ├─ 控制码占位符保护
  │   └─ DeepSeek API 批量翻译 + MD5 缓存
  │
  └─ [Python build] ──→ output_cn.gba (32MB)
      ├─ ROM 扩展 16MB → 32MB
      ├─ armips 注入中文 Font Patch
      └─ 文本注入 + 指针重定向
```

### 前置要求

- **Python 3.10+**
- **.NET 8.0 SDK**（编译 MeowthBridge 提取工具）
- **DeepSeek API Key**（[申请地址](https://platform.deepseek.com/)）
- **armips**（已包含在 `tools/armips`，macOS 预编译）

### 安装

```bash
# 1. 克隆仓库（含子模块）
git clone --recursive https://github.com/Olcmyk/Meowth-GBA-Translator.git
cd Meowth-GBA-Translator

# 2. 安装 Python 依赖
pip install -e .

# 3. 配置 API Key
echo "DEEPSEEK_API_KEY=sk-your-key-here" > .env

# 4. 初始化子模块（如果克隆时没有 --recursive）
git submodule update --init --recursive
```

### 快速开始

#### 一键翻译（推荐）

```bash
meowth full your_rom.gba
```

这会自动执行：提取文本 → AI 翻译 → 构建中文 ROM，输出到 `outputs/` 目录。

#### 分步执行

```bash
# 第 1 步：提取文本
meowth extract your_rom.gba -o work/texts.json

# 第 2 步：翻译文本
meowth translate work/texts.json -o work/texts_translated.json

# 第 3 步：构建中文 ROM
meowth build your_rom.gba --translations work/texts_translated.json -o outputs/rom_cn.gba
```

#### 使用 C# MeowthBridge（高级）

```bash
# 提取（使用 HexManiacAdvance 引擎）
dotnet run --project src/MeowthBridge extract your_rom.gba -o work/texts.json

# 翻译
meowth translate work/texts.json -o work/texts_translated.json

# 构建
meowth build your_rom.gba --translations work/texts_translated.json -o outputs/rom_cn.gba
```

### 配置

配置文件 `meowth.toml`：

```toml
[translation]
provider = "deepseek"          # 翻译服务提供商
model = "deepseek-chat"        # 模型名称
source_language = "en"         # 源语言
target_language = "zh-Hans"    # 目标语言（简体中文）

[translation.api]
key_env = "DEEPSEEK_API_KEY"   # API Key 环境变量名（从 .env 读取）

[font_patch]
armips_path = "tools/armips"   # armips 汇编器路径
game = "FR"                    # 游戏类型：FR/LG/E/RS

[output]
dir = "outputs"                # 输出目录
cache_dir = "work/cache"       # 翻译缓存目录
```

### 翻译成本

使用 DeepSeek API 翻译一个完整 ROM（约 4000+ 条文本）：

| 项目 | 数值 |
|------|------|
| 文本条数 | ~4,355 条（FireRed） |
| Token 消耗 | ~50,000 tokens |
| API 费用 | 约 ¥0.07 - ¥0.35（$0.01 - $0.05） |

得益于本地缓存机制，中断后重新运行不会产生额外费用。

### 项目结构

```
Meowth-GBA-Translator/
├── src/
│   ├── MeowthBridge/              # C# .NET 8.0 — ROM 文本提取
│   │   ├── Program.cs             # CLI 入口（extract 命令）
│   │   ├── RomLoader.cs           # ROM 加载 + 游戏自动识别
│   │   ├── TextExtractor.cs       # 表结构提取 + loadpointer 扫描
│   │   └── ...
│   └── meowth/                    # Python 主包 — 翻译 + 构建
│       ├── cli.py                 # Click CLI 入口
│       ├── pipeline.py            # 主编排流程
│       ├── translator.py          # DeepSeek 翻译 + 缓存
│       ├── charmap.py             # Font Patch 字符映射
│       ├── control_codes.py       # PCS 控制码保护
│       ├── glossary.py            # PokeAPI 术语表
│       ├── rom_writer.py          # ROM 扩展 + 文本注入 + 指针更新
│       ├── font_patch.py          # armips Font Patch 调用
│       ├── text_wrap.py           # 中文文本自动换行
│       └── pcs_codes.py           # PCS 编码定义
├── Pokemon_GBA_Font_Patch/        # 中文字库 Patch（ASM + charmap）
├── HexManiacAdvance/              # .NET ROM 编辑库（子模块）
├── pokeapi-master/                # PokeAPI 多语言术语数据
├── tools/armips                   # ARM 汇编器（预编译）
├── meowth.toml                    # 用户配置
├── pyproject.toml                 # Python 包配置
└── .env                           # API 密钥（不纳入版本控制）
```

### 工作原理详解

#### 第一阶段：文本提取（C# MeowthBridge）

使用 HexManiacAdvance 库分析 ROM 结构：

1. **表结构提取**：自动发现 `data.pokemon.names`、`data.pokemon.moves.names` 等命名锚点，提取宝可梦名、招式名、道具名、特性名、地图名等
2. **脚本文本扫描**：通过 `loadpointer`（0x0F）指令扫描，找到所有对话、NPC 文本、战斗文本
3. **指针记录**：记录每条文本的所有指针源地址，为后续 repointing 提供依据

输出 JSON 包含：文本内容、ROM 地址、指针地址列表、文本类别。

#### 第二阶段：AI 翻译（Python）

1. **术语表查表**：从 PokeAPI 加载官方中文译名，已知术语直接替换不走 LLM
2. **控制码保护**：将 `\n`、`\p`、`[player]` 等替换为编号占位符，防止 LLM 破坏
3. **批量翻译**：多条文本用 `|||` 分隔符合并，批量发送给 DeepSeek
4. **缓存机制**：MD5 哈希原文作为缓存键，相同文本不重复翻译

#### 第三阶段：ROM 构建（Python）

1. **ROM 扩展**：16MB → 32MB（追加 0xFF 填充），为中文双字节编码腾出空间
2. **Font Patch**：通过 armips 注入中文字库（7,774 个汉字）和渲染引擎
3. **文本注入**：短文本原地写入，长文本写入扩展区域并更新所有指针
4. **输出**：带时间戳的中文 ROM 文件

### 缓存机制

- 翻译结果自动缓存到 `work/cache/` 目录
- 基于原文 MD5 哈希，相同文本只翻译一次
- 支持断点续传：中断后重新运行自动跳过已翻译文本
- 清除缓存：`rm -rf work/cache`

### 常见问题

**Q: 翻译后游戏黑屏/崩溃？**
A: 通常是指针损坏导致。确保使用最新版本，工具已内置指针重定向机制避免此问题。

**Q: 部分文字显示乱码？**
A: 可能是翻译中包含了字库不支持的字符。工具会自动检测并警告不支持的字符。

**Q: 可以翻译改版 ROM 吗？**
A: 可以。只要改版基于支持的基础 ROM（火红/叶绿/绿宝石/红蓝宝石），理论上都能翻译。改版新增的文本也会被提取和翻译。

**Q: 支持其他语言吗？**
A: 目前默认英译中。通过修改 `meowth.toml` 中的 `target_language` 和 DeepSeek 的 system prompt，理论上可以翻译为其他语言。

**Q: API 费用贵吗？**
A: 非常便宜。翻译一个完整 ROM 约 ¥0.07 - ¥0.35，且有缓存机制避免重复消费。

### 致谢

- [HexManiacAdvance](https://github.com/haven1433/HexManiacAdvance) — 强大的 GBA ROM 编辑库
- [Pokemon_GBA_Font_Patch](https://github.com/SPokemon_GBA_Font_Patch) — GBA 中文字库 Patch
- [PokeAPI](https://pokeapi.co/) — 宝可梦多语言术语数据库
- [DeepSeek](https://deepseek.com/) — AI 翻译引擎
- [armips](https://github.com/Kingcom/armips) — ARM/MIPS 汇编器

### 许可证

[MIT License](LICENSE) - Copyright (c) 2026 Olcmyk

---

## English

### What is Meowth?

Meowth-GBA-Translator is an AI-powered tool that automatically translates English Pokemon GBA ROM hacks into Simplified Chinese. It combines HexManiacAdvance for ROM analysis with DeepSeek LLM for intelligent translation, producing playable Chinese ROMs with a single command.

### Features

- **One-click translation**: Input an English ROM, get a Chinese ROM — fully automated
- **AI-powered**: Uses DeepSeek API for high-quality game text translation
- **Official terminology**: Integrates PokeAPI for official Chinese Pokemon names, moves, abilities
- **Smart extraction**: HexManiacAdvance auto-discovers ROM table structures
- **Control code protection**: Preserves `\n`, `\p`, `[player]`, `[rival]` and other game control codes
- **Pointer rewriting**: Automatically repoints overlong translations to expanded ROM space
- **Chinese font injection**: Applies Font Patch with 7,774 Chinese characters (11x11 font)
- **Local caching**: MD5-based cache for resumable translation, no wasted API calls
- **Multi-game support**: All Gen III main Pokemon games

### Supported Games

| Game | ROM Code | Status |
|------|----------|--------|
| Pokemon FireRed | BPRE | ✅ Fully supported |
| Pokemon LeafGreen | BPGE | ✅ Supported |
| Pokemon Emerald | BPEE | ✅ Fully supported |
| Pokemon Ruby | AXVE | ✅ Supported |
| Pokemon Sapphire | AXPE | ✅ Supported |

Also works with ROM hacks based on these games.

### Prerequisites

- Python 3.10+
- .NET 8.0 SDK
- DeepSeek API Key ([get one here](https://platform.deepseek.com/))

### Quick Start

```bash
# Clone with submodules
git clone --recursive https://github.com/Olcmyk/Meowth-GBA-Translator.git
cd Meowth-GBA-Translator

# Install
pip install -e .

# Set API key
echo "DEEPSEEK_API_KEY=sk-your-key-here" > .env

# Translate a ROM
meowth full your_rom.gba
```

Output will be in the `outputs/` directory.

### Step-by-Step Usage

```bash
# Extract texts from ROM
meowth extract your_rom.gba -o work/texts.json

# Translate via DeepSeek
meowth translate work/texts.json -o work/texts_translated.json

# Build Chinese ROM
meowth build your_rom.gba --translations work/texts_translated.json -o outputs/rom_cn.gba
```

### Configuration

Edit `meowth.toml`:

```toml
[translation]
provider = "deepseek"
model = "deepseek-chat"
source_language = "en"
target_language = "zh-Hans"

[translation.api]
key_env = "DEEPSEEK_API_KEY"

[font_patch]
armips_path = "tools/armips"
game = "FR"  # FR/LG/E/RS

[output]
dir = "outputs"
cache_dir = "work/cache"
```

### How It Works

1. **Extract** (C# + HexManiacAdvance): Discovers ROM table structures and scans `loadpointer` instructions to extract all text with pointer metadata
2. **Translate** (Python + DeepSeek): Looks up official terms from PokeAPI, protects control codes with placeholders, batch-translates via LLM with local MD5 caching
3. **Build** (Python + armips): Expands ROM to 32MB, applies Chinese font patch, injects translated text with automatic pointer redirection

### Translation Cost

~$0.01-0.05 per full ROM (~4,000+ text entries) using DeepSeek API. Cached results are free on re-runs.

### License

[MIT License](LICENSE) - Copyright (c) 2026 Olcmyk
