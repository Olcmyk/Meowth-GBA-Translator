# Meowth-GBA-Translator

**一键翻译 GBA 宝可梦 ROM 的自动化工具**

将英文/西班牙文宝可梦 GBA ROM（包括改版 ROM Hack）翻译成简体中文、法语、德语、意大利语、西班牙语等语言。基于 LLM（大语言模型）+ HexManiacAdvance 文本提取 + 自动字库补丁，实现全流程自动化。

## 目录

- [功能特性](#功能特性)
- [支持的游戏](#支持的游戏)
- [支持的语言](#支持的语言)
- [系统架构](#系统架构)
- [安装指南](#安装指南)
- [快速开始](#快速开始)
- [命令详解](#命令详解)
- [LLM 服务商配置](#llm-服务商配置)
- [配置文件](#配置文件)
- [翻译流程详解](#翻译流程详解)
- [字库补丁说明](#字库补丁说明)
- [术语表系统](#术语表系统)
- [常见问题](#常见问题)
- [项目结构](#项目结构)
- [开发指南](#开发指南)
- [致谢](#致谢)

## 功能特性

- **全自动翻译流程**：提取 → 翻译 → 构建，一条命令完成
- **多语言支持**：英语、简体中文、法语、德语、意大利语、西班牙语
- **多 LLM 服务商**：支持 DeepSeek、OpenAI、Google Gemini、Groq、Mistral、通义千问、智谱、Moonshot、SiliconFlow、OpenRouter 等任何 OpenAI 兼容 API
- **官方术语表**：自动从 PokeAPI 加载宝可梦、技能、道具、特性等官方译名
- **CJK 字库补丁**：翻译为中文/日文/韩文时自动注入中文字库（基于 Pokemon_GBA_Font_Patch）
- **智能排版**：自动换行、分页，适配 GBA 文本框宽度
- **翻译缓存**：已翻译内容自动缓存，重复运行不浪费 API 调用
- **并行翻译**：多线程批量调用 LLM，大幅提升翻译速度
- **控制码保护**：翻译前自动保护游戏控制码（换行、翻页、颜色、变量等），翻译后精确还原
- **ROM Hack 兼容**：自动检测 ROM 空闲空间，支持各种改版 ROM

## 支持的游戏

| 游戏 | ROM Code | 状态 |
|------|----------|------|
| 火红 (FireRed) | BPRE | ✅ 完全支持 |
| 叶绿 (LeafGreen) | BPGE | ✅ 完全支持 |
| 绿宝石 (Emerald) | BPEE | ✅ 完全支持 |
| 红宝石 (Ruby) | AXVE | 🔧 基础支持 |
| 蓝宝石 (Sapphire) | AXPE | 🔧 基础支持 |

游戏类型通过 ROM 头部字节 0xAC-0xAF 的 4 字节 Game Code 自动检测。

## 支持的语言

| 语言代码 | 语言 | 翻译方向 | 字库补丁 |
|----------|------|----------|----------|
| `en` | English（英语） | 源语言 | 不需要 |
| `es` | Spanish（西班牙语） | 源语言 / 目标语言 | 不需要 |
| `fr` | French（法语） | 目标语言 | 不需要 |
| `de` | German（德语） | 目标语言 | 不需要 |
| `it` | Italian（意大利语） | 目标语言 | 不需要 |
| `zh-Hans` | 简体中文 | 目标语言 | 需要（自动应用） |

拉丁语系（法/德/意/西）使用 GBA 原生 PCS 字符编码，支持所有西欧重音字符（é, è, ê, ë, à, â, ç, ù, û, ü, ô, î, ï, Œ, œ 等）。

中文翻译需要注入自定义字库补丁（Pokemon_GBA_Font_Patch），将 GBA 的单字节字符空间扩展为双字节，以支持数千个汉字。

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    meowth full (一键流程)                  │
├──────────┬──────────────────┬───────────────────────────┤
│  extract │    translate     │          build            │
│          │                  │                           │
│ MeowthBridge               │  Charmap (PCS/字库)        │
│ (C#/.NET)  ┌────────────┐  │  RomWriter (指针重定向)     │
│ 基于 HMA   │ LLM API    │  │  FontPatch (armips)       │
│ 提取文本   │ (翻译引擎)  │  │  TextWrap (自动排版)       │
│ + 指针     │ + 术语表    │  │                           │
│            │ + 控制码保护 │  │                           │
│            └────────────┘  │                           │
└──────────┴──────────────────┴───────────────────────────┘
```

核心组件：

| 组件 | 文件 | 功能 |
|------|------|------|
| CLI | `src/meowth/cli.py` | Click 命令行入口 |
| Pipeline | `src/meowth/pipeline.py` | 流程编排（extract → translate → build） |
| Translator | `src/meowth/translator.py` | LLM API 调用、缓存、批量翻译 |
| Charmap | `src/meowth/charmap.py` | 字符编码映射（PCS / 字库补丁） |
| RomWriter | `src/meowth/rom_writer.py` | ROM 二进制写入、指针重定向 |
| FontPatch | `src/meowth/font_patch.py` | 中文字库补丁（调用 armips） |
| TextWrap | `src/meowth/text_wrap.py` | GBA 文本框自动换行排版 |
| Glossary | `src/meowth/glossary.py` | PokeAPI 官方术语表 |
| ControlCodes | `src/meowth/control_codes.py` | 控制码保护与还原 |
| PCSCodes | `src/meowth/pcs_codes.py` | GBA PCS 编码定义 |
| Languages | `src/meowth/languages.py` | 语言配置 |
| MeowthBridge | `src/MeowthBridge/` | C# 文本提取器（基于 HexManiacAdvance） |

<!-- PLACEHOLDER_INSTALL -->

## 安装指南

### 前置要求

- Python 3.10+
- .NET 8.0 SDK（用于编译 MeowthBridge）
- armips（ARM 汇编器，用于中文字库补丁，仅中文翻译需要）

### 1. 克隆仓库

```bash
git clone --recursive https://github.com/pPokemon/Meowth-GBA-Translator.git
cd Meowth-GBA-Translator
```

> `--recursive` 会同时拉取 `HexManiacAdvance` 和 `pokeapi` 子模块。如果忘记加，可以后续执行：
> ```bash
> git submodule update --init --recursive
> ```

### 2. 安装 Python 包

```bash
pip install -e .
```

这会安装 `meowth` 命令行工具及其依赖（`click`、`httpx`）。

### 3. 编译 MeowthBridge

```bash
dotnet build src/MeowthBridge -c Release
```

MeowthBridge 是基于 HexManiacAdvance 的 C# 文本提取器，负责从 ROM 中提取所有文本及其指针地址。

### 4. 配置 armips（仅中文翻译需要）

将 armips 可执行文件放到 `tools/armips`：

```bash
mkdir -p tools
# macOS (Apple Silicon)
cp /path/to/armips tools/armips
chmod +x tools/armips
```

armips 用于将中文字库补丁注入 ROM。如果只翻译为拉丁语系（法/德/意/西），则不需要 armips。

### 5. 配置 API Key

创建 `.env` 文件：

```bash
# DeepSeek（默认）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# 或者使用其他服务商（见 LLM 服务商配置章节）
# OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
# GOOGLE_API_KEY=AIzaxxxxxxxxxxxxxxxx
```

<!-- PLACEHOLDER_QUICKSTART -->

## 快速开始

### 一键翻译（推荐）

```bash
# 英文火红 → 简体中文（默认使用 DeepSeek）
meowth full testgba/firered_en.gba

# 英文火红 → 法语
meowth full testgba/firered_en.gba --source en --target fr

# 英文绿宝石 → 德语，使用 OpenAI
meowth full testgba/emerald_en.gba --source en --target de --provider openai

# 使用自定义 API
meowth full testgba/firered_en.gba --target fr \
  --api-base https://api.example.com/v1 \
  --api-key-env MY_API_KEY \
  --model gpt-4o
```

### 分步执行

如果需要更精细的控制，可以分三步执行：

```bash
# 第 1 步：提取文本
meowth extract testgba/firered_en.gba -o work/firered_texts.json

# 第 2 步：翻译文本
meowth translate work/firered_texts.json \
  --source en --target fr \
  -o work/firered_texts_fr.json

# 第 3 步：构建 ROM
meowth build testgba/firered_en.gba \
  --translations work/firered_texts_fr.json \
  --source en --target fr \
  -o outputs/firered_fr.gba
```

## 命令详解

### `meowth extract`

从 GBA ROM 中提取所有文本。

```
meowth extract <rom_path> [OPTIONS]

参数:
  rom_path              ROM 文件路径

选项:
  -o, --output TEXT     输出 JSON 路径 (默认: work/texts.json)
  --source TEXT         源语言代码 (默认: en)
  --target TEXT         目标语言代码 (默认: zh-Hans)
```

内部调用 MeowthBridge（基于 HexManiacAdvance），提取内容包括：
- 脚本对话文本（scripts）
- 宝可梦名称（pokemon_names）
- 技能名称（move_names）
- 特性名称（ability_names）
- 道具名称（item_names）
- 属性名称（type_names）
- 性格名称（nature_names）
- 训练师类型（trainer_classes）
- 地图名称（map_names）

输出 JSON 格式：

```json
{
  "entries": [
    {
      "id": "scr_02329",
      "category": "scripts",
      "original": "Hello there!\\nGlad to meet you!",
      "address": "0x01A8F00",
      "byte_length": 32,
      "is_pointer_based": true,
      "pointer_sources": ["0x016A3B4"]
    }
  ]
}
```

<!-- PLACEHOLDER_COMMANDS2 -->

### `meowth translate`

使用 LLM 翻译提取的文本。

```
meowth translate <texts_json> [OPTIONS]

参数:
  texts_json            提取的文本 JSON 路径

选项:
  -o, --output TEXT     输出翻译 JSON 路径 (默认: work/texts_translated.json)
  --batch-size INT      每批发送给 LLM 的文本数 (默认: 30)
  --workers INT         并行翻译线程数 (默认: 10)
  --source TEXT         源语言代码 (默认: en)
  --target TEXT         目标语言代码 (默认: zh-Hans)
  --provider TEXT       LLM 服务商预设 (见下方列表)
  --api-base TEXT       自定义 API 基础 URL
  --api-key-env TEXT    API Key 环境变量名
  --model TEXT          模型名称
```

翻译流程：
1. 表格类数据（宝可梦名、技能名等）优先使用 PokeAPI 术语表直接查找
2. 自由文本（对话、描述等）通过 LLM 批量翻译
3. 翻译前自动保护控制码（`\n`, `\p`, `[player]`, `[rival]` 等），翻译后还原
4. 翻译结果自动缓存到 `work/cache/`，相同请求不会重复调用 API

### `meowth build`

将翻译后的文本写入 ROM，生成最终翻译版。

```
meowth build <rom_path> [OPTIONS]

参数:
  rom_path              原始 ROM 文件路径

选项:
  --translations PATH   翻译 JSON 文件路径 (必需)
  -o, --output TEXT     输出 ROM 路径 (必需)
  --source TEXT         源语言代码 (默认: en)
  --target TEXT         目标语言代码 (默认: zh-Hans)
```

构建流程：
1. 加载 ROM 并扩展到 32MB（GBA 最大容量）
2. 如果目标语言是 CJK，自动应用中文字库补丁
3. 将翻译文本编码为 ROM 字节并写入
4. 短文本原地写入（in-place），长文本重定向到扩展区并更新指针

### `meowth full`

一键执行完整流程：extract → translate → build。

```
meowth full <rom_path> [OPTIONS]

参数:
  rom_path              ROM 文件路径

选项:
  -o, --output-dir TEXT 输出目录 (默认: outputs)
  --work-dir TEXT       工作目录 (默认: work)
  --source TEXT         源语言代码 (默认: en)
  --target TEXT         目标语言代码 (默认: zh-Hans)
  --provider TEXT       LLM 服务商预设
  --api-base TEXT       自定义 API 基础 URL
  --api-key-env TEXT    API Key 环境变量名
  --model TEXT          模型名称
```

输出文件命名格式：`{game}_{target_lang}_{timestamp}.gba`

<!-- PLACEHOLDER_LLM -->

## LLM 服务商配置

Meowth 支持任何兼容 OpenAI Chat Completions API 的服务商。内置以下预设：

| 预设名 | 服务商 | 默认模型 | API Key 环境变量 |
|--------|--------|----------|-----------------|
| `deepseek` | DeepSeek | `deepseek-chat` | `DEEPSEEK_API_KEY` |
| `openai` | OpenAI | `gpt-4o` | `OPENAI_API_KEY` |
| `anthropic` | Anthropic | `claude-sonnet-4-20250514` | `ANTHROPIC_API_KEY` |
| `google` | Google Gemini | `gemini-2.0-flash` | `GOOGLE_API_KEY` |
| `groq` | Groq | `llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| `mistral` | Mistral AI | `mistral-large-latest` | `MISTRAL_API_KEY` |
| `openrouter` | OpenRouter | `openai/gpt-4o` | `OPENROUTER_API_KEY` |
| `siliconflow` | SiliconFlow | `deepseek-ai/DeepSeek-V3` | `SILICONFLOW_API_KEY` |
| `zhipu` | 智谱 AI | `glm-4-flash` | `ZHIPU_API_KEY` |
| `moonshot` | Moonshot (Kimi) | `moonshot-v1-8k` | `MOONSHOT_API_KEY` |
| `qwen` | 通义千问 | `qwen-plus` | `DASHSCOPE_API_KEY` |

### 使用方式

**方式一：命令行参数（优先级最高）**

```bash
# 使用预设
meowth translate texts.json --provider openai --target fr

# 使用预设 + 自定义模型
meowth translate texts.json --provider openai --model gpt-4o-mini --target fr

# 完全自定义（任何 OpenAI 兼容 API）
meowth translate texts.json \
  --api-base https://my-local-llm:8080/v1 \
  --api-key-env MY_LOCAL_KEY \
  --model my-model \
  --target fr
```

**方式二：配置文件 `meowth.toml`**

```toml
[translation]
provider = "openai"          # 使用 OpenAI 预设
model = "gpt-4o-mini"        # 覆盖默认模型

[translation.api]
key_env = "OPENAI_API_KEY"   # API Key 环境变量名
# base_url = "https://..."   # 可选：覆盖预设的 base_url
```

**方式三：环境变量 `.env`**

```bash
# 在 .env 文件中设置 API Key
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
```

优先级：命令行参数 > `meowth.toml` > 默认值（DeepSeek）

### 使用本地模型

如果你运行了本地 LLM 服务（如 Ollama、vLLM、LM Studio），只要它兼容 OpenAI API 格式即可：

```bash
# Ollama
meowth translate texts.json \
  --api-base http://localhost:11434/v1 \
  --model llama3.1 \
  --api-key-env OLLAMA_API_KEY \
  --target fr

# vLLM
meowth translate texts.json \
  --api-base http://localhost:8000/v1 \
  --model my-model \
  --api-key-env VLLM_API_KEY \
  --target zh-Hans
```

> 注意：本地模型的翻译质量取决于模型能力。建议使用 7B+ 参数的模型以获得可接受的翻译质量。

## 配置文件

项目根目录的 `meowth.toml` 是主配置文件：

```toml
[translation]
# LLM 服务商预设名（见上方列表）
provider = "deepseek"
# 模型名称（留空则使用预设默认值）
model = "deepseek-chat"
# 源语言和目标语言
source_language = "en"
target_language = "zh-Hans"

[translation.api]
# API Key 的环境变量名
key_env = "DEEPSEEK_API_KEY"
# 自定义 API 地址（可选，覆盖预设）
# base_url = "https://api.deepseek.com/v1"

[font_patch]
# armips 可执行文件路径
armips_path = "tools/armips"
# 游戏类型（FR=火红, E=绿宝石）
game = "FR"

[output]
# 输出目录
dir = "outputs"
# 翻译缓存目录
cache_dir = "work/cache"
```

<!-- PLACEHOLDER_PIPELINE -->

## 翻译流程详解

### 第 1 步：文本提取 (extract)

MeowthBridge（C#，基于 HexManiacAdvance 库）负责：

1. 解析 ROM 的 PCS（Pokemon Character Set）编码文本
2. 识别文本指针表和脚本中的文本引用
3. 提取所有文本条目，记录：
   - 原始文本内容
   - ROM 中的地址
   - 字节长度
   - 指针来源地址（用于后续重定向）
   - 文本类别（scripts / pokemon_names / move_names 等）
4. 后处理：将 HMA 的原始 FD 转义序列替换为命名宏（如 `\05` → `[kun]`）

### 第 2 步：翻译 (translate)

翻译分两个阶段：

**阶段 A：表格数据（术语表查找）**

宝可梦名、技能名、道具名等结构化数据优先从 PokeAPI 术语表查找官方译名：

```
Pikachu → 皮卡丘 (zh-Hans) / Pikachu (fr) / Pikachu (de)
Thunderbolt → 十万伏特 (zh-Hans) / Tonnerre (fr) / Donnerblitz (de)
```

术语表来源：`pokeapi/data/v2/csv/` 下的 CSV 文件，包含 pokemon_species_names、move_names、ability_names、item_names、type_names、nature_names、location_names、region_names。

**阶段 B：自由文本（LLM 翻译）**

对话、描述等自由文本通过 LLM 翻译：

1. **控制码保护**：将 `\n`、`\p`、`[player]`、`[rival]`、`\CC0106` 等控制码替换为占位符 `{C0}`、`{C1}`...
2. **批量翻译**：每 30 条文本合并为一个 API 请求（用 `|||` 分隔），10 个线程并行
3. **控制码还原**：将占位符替换回原始控制码
4. **自动排版**：根据目标语言的字符宽度自动插入 `\n`（换行）和 `\p`（翻页）
5. **缓存**：翻译结果按请求内容的 SHA256 哈希缓存，相同请求直接返回缓存

### 第 3 步：构建 ROM (build)

1. **ROM 扩展**：将 ROM 扩展到 32MB（0x02000000），用 0xFF 填充
2. **字库补丁**（仅 CJK）：通过 armips 注入中文字库，将字节 0x01-0x1E 重新映射为双字节中文字符前缀
3. **文本编码**：将翻译文本编码为 ROM 字节
   - CJK 语言：使用字库补丁的 charmap（双字节中文字符）
   - 拉丁语言：使用标准 PCS 编码（单字节，支持西欧重音字符）
4. **文本写入**：
   - 短文本（编码后 ≤ 原始长度）：原地写入（in-place）
   - 长文本：写入扩展区（0x01000000 之后的空闲空间），并更新所有指针
5. **指针安全**：跳过 ARM 代码区（< 0x0A0000）的指针，避免破坏可执行代码

## 字库补丁说明

GBA 原生 PCS 编码只支持约 200 个字符（ASCII + 西欧重音字符），无法显示中文。

中文字库补丁（Pokemon_GBA_Font_Patch）的工作原理：

1. 将字节 0x01-0x1E（原本映射到 À, Á, Â 等重音字符）重新定义为双字节字符的高位前缀
2. 高位 + 低位组合可表示数千个汉字（如 0x0100 = 啊, 0x0101 = 阿, ...）
3. 字库数据写入 ROM 的高地址区域（FireRed: 0x01FD3000, Emerald: 0x01FD0000）
4. 通过 armips 汇编器注入字库渲染代码

因此：
- 翻译为中文时，重音字符（À, Á, Â 等）不可用（被字库占用）
- 翻译为拉丁语言时，不应用字库补丁，保留原始 PCS 编码

## 术语表系统

Meowth 使用 PokeAPI 的官方多语言数据作为术语表，确保宝可梦名、技能名等使用官方译名。

数据来源：`pokeapi/` 子模块（git submodule），包含以下 CSV 文件：

| 文件 | 内容 |
|------|------|
| `pokemon_species_names.csv` | 宝可梦名称 |
| `move_names.csv` | 技能名称 |
| `ability_names.csv` | 特性名称 |
| `item_names.csv` | 道具名称 |
| `type_names.csv` | 属性名称 |
| `nature_names.csv` | 性格名称 |
| `location_names.csv` | 地点名称 |
| `region_names.csv` | 地区名称 |

术语表在翻译时自动加载，并作为上下文提供给 LLM，确保翻译一致性。

<!-- PLACEHOLDER_FAQ -->

## 常见问题

### Q: 翻译成法语/德语后游戏开头出现乱码（如 ÊœÔrËñÈàÂÛŒ8ÓÄÄ）

**原因**：旧版本对拉丁语言错误地使用了中文字库补丁的 charmap 编码。中文 charmap 将字节 0x01-0x1E 映射为双字节中文字符前缀，但拉丁语言的 ROM 没有应用字库补丁，这些字节仍然是标准 PCS 编码的单字节重音字符。

**解决方案**：已修复。现在拉丁语言自动使用标准 PCS 编码，中文使用字库补丁编码。请更新到最新版本后重新执行 `meowth build`。

### Q: 如何使用 OpenAI / 其他 API 代替 DeepSeek？

```bash
# 方式一：命令行
meowth full rom.gba --provider openai --target zh-Hans

# 方式二：修改 meowth.toml
# [translation]
# provider = "openai"
# [translation.api]
# key_env = "OPENAI_API_KEY"
```

详见 [LLM 服务商配置](#llm-服务商配置) 章节。

### Q: 翻译后部分文本没有被翻译

可能原因：
1. **API 返回原文**：LLM 有时会原样返回无法理解的文本。Meowth 会检测并标记这些条目，不缓存它们，下次运行会重新翻译
2. **术语表覆盖**：宝可梦名等表格数据优先使用术语表，如果术语表中没有对应条目，会保留原文
3. **垃圾数据过滤**：ROM 中的二进制数据有时被误识别为文本，Meowth 会自动跳过这些条目

### Q: 翻译后文字显示不全或被截断

GBA 文本框有固定宽度（约 30 个英文字符或 15 个中文字符）。如果翻译后的文本过长：
- 有指针的文本会被重定向到扩展区，不受长度限制
- 无指针的文本（如道具名、宝可梦名）会被截断到原始长度

### Q: 如何清除翻译缓存？

```bash
rm -rf work/cache/
```

### Q: 支持哪些 ROM Hack？

理论上支持所有基于火红/叶绿/绿宝石的 ROM Hack。Meowth 会自动检测 ROM 中的空闲空间，避免覆盖 Hack 的自定义数据。但如果 Hack 使用了非常规的文本存储方式，可能需要手动调整。

### Q: MeowthBridge 编译失败

确保安装了 .NET 8.0 SDK：

```bash
dotnet --version  # 应显示 8.x.x
dotnet build src/MeowthBridge -c Release
```

如果 HexManiacAdvance 子模块缺失：

```bash
git submodule update --init --recursive
```

## 项目结构

```
Meowth-GBA-Translator/
├── src/
│   ├── meowth/                    # Python 主包
│   │   ├── cli.py                 # Click CLI 入口
│   │   ├── pipeline.py            # 流程编排
│   │   ├── translator.py          # LLM API 翻译引擎
│   │   ├── charmap.py             # 字符编码映射
│   │   ├── rom_writer.py          # ROM 二进制写入
│   │   ├── font_patch.py          # 中文字库补丁
│   │   ├── text_wrap.py           # 自动换行排版
│   │   ├── glossary.py            # PokeAPI 术语表
│   │   ├── control_codes.py       # 控制码保护/还原
│   │   ├── pcs_codes.py           # PCS 编码定义
│   │   ├── pcs_scanner.py         # ROM 文本扫描
│   │   ├── languages.py           # 语言配置
│   │   └── manual_entries.json    # 手动翻译条目
│   └── MeowthBridge/              # C# 文本提取器
│       ├── Program.cs             # 入口
│       ├── RomLoader.cs           # ROM 加载
│       ├── TextExtractor.cs       # 文本提取
│       ├── TextWriter.cs          # 文本写入
│       ├── TextPreprocessor.cs    # 文本预处理
│       └── ChsEncoder.cs          # 中文编码
├── HexManiacAdvance/              # Git 子模块：HMA 库
├── Pokemon_GBA_Font_Patch/        # 中文字库补丁资源
│   ├── pokeFRLG/                  # 火红/叶绿字库
│   │   ├── main_FR.asm            # armips 汇编脚本
│   │   └── PMRSEFRLG_charmap.txt  # 字库 charmap
│   └── pokeE/                     # 绿宝石字库
│       └── main_E.asm
├── pokeapi/                       # Git 子模块：PokeAPI 数据
│   └── data/v2/csv/               # 多语言术语 CSV
├── tools/                         # 外部工具
│   └── armips                     # ARM 汇编器
├── testgba/                       # 测试用 ROM
├── work/                          # 工作目录（自动生成）
│   ├── cache/                     # 翻译缓存
│   └── *.json                     # 中间文件
├── outputs/                       # 输出目录
├── meowth.toml                    # 项目配置
├── pyproject.toml                 # Python 包配置
├── .env                           # API Key（不提交到 Git）
└── README.md
```

<!-- PLACEHOLDER_DEV -->

## 开发指南

### 环境搭建

```bash
git clone --recursive https://github.com/pPokemon/Meowth-GBA-Translator.git
cd Meowth-GBA-Translator
pip install -e ".[dev]"
dotnet build src/MeowthBridge -c Release
```

### 运行测试

```bash
pytest
```

### 添加新语言

1. 在 `src/meowth/languages.py` 的 `SUPPORTED_LANGUAGES` 中添加语言条目
2. 如果是 CJK 语言，添加到 `_CJK_LANGUAGES` 集合
3. 如果是拉丁语言，添加到 `_LATIN_LANGUAGES` 集合
4. 确保 PokeAPI CSV 中有对应语言的 `local_language_id`

### 添加新 LLM 服务商预设

在 `src/meowth/translator.py` 的 `PROVIDER_PRESETS` 字典中添加：

```python
PROVIDER_PRESETS = {
    # ...
    "my_provider": ("https://api.example.com/v1", "default-model", "MY_API_KEY"),
}
```

### 关键技术细节

**PCS 编码**：GBA 宝可梦使用自定义的 PCS（Pokemon Character Set）编码，不是 ASCII 或 UTF-8。例如：
- 0x00 = 空格, 0x01 = À, 0xBB = A, 0xD5 = a, 0xFF = 终止符
- 0xFE = 换行, 0xFB = 翻页, 0xFC = 控制码前缀, 0xFD = 变量前缀

**指针重定向**：GBA ROM 中的文本通过 4 字节小端序指针引用（基址 0x08000000）。当翻译后的文本比原文长时，Meowth 将新文本写入扩展区，并更新所有指向原文的指针。

**字库补丁原理**：将字节 0x01-0x1E（排除 0x06 和 0x1B）重新定义为双字节字符的高位前缀。高位 + 低位组合映射到 charmap 中的汉字。字库渲染代码通过 armips 汇编器注入 ROM。

## 致谢

- [HexManiacAdvance](https://github.com/haven1433/HexManiacAdvance) - GBA ROM 编辑器，提供文本提取和指针分析能力
- [Pokemon_GBA_Font_Patch](https://github.com/pret/Pokemon_GBA_Font_Patch) - GBA 宝可梦中文字库补丁
- [PokeAPI](https://github.com/PokeAPI/pokeapi) - 宝可梦官方多语言术语数据
- [armips](https://github.com/Kingcom/armips) - ARM/MIPS 汇编器
- [DeepSeek](https://www.deepseek.com/) - 默认 LLM 翻译引擎

## License

MIT







