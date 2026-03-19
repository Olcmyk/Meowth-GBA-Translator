# Meowth GBA 翻译工具 - 完整使用指南

## 目录

1. [概述](#概述)
2. [安装](#安装)
3. [配置](#配置)
4. [使用方法](#使用方法)
   - [GUI 使用](#gui-使用)
   - [CLI 使用](#cli-使用)
5. [三步翻译流程详解](#三步翻译流程详解)
6. [常见问题](#常见问题)
7. [高级用法](#高级用法)

---

## 概述

Meowth GBA 翻译工具是一款专为 GBA 宝可梦 ROM 翻译设计的工具，支持：

- **支持的游戏**：火红、叶绿、绿宝石、红宝石、蓝宝石
- **支持的语言**：英语、中文（简体/繁体）、日语、韩语、西班牙语、法语、德语、意大利语
- **翻译引擎**：支持 11+ 个 LLM 提供商（OpenAI、DeepSeek、Google Gemini、Anthropic Claude 等）

### 翻译流程

```
原版 ROM → [1. 提取文本] → texts.json → [2. 翻译文本] → texts_translated.json → [3. 构建 ROM] → 翻译版 ROM
```

---

## 安装

### 方式 1：GUI 应用（推荐）

下载预编译的应用程序：

- **macOS**：[Meowth-Translator-macOS.dmg](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)
- **Windows**：[Meowth-Translator-Windows.zip](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

无需安装 Python，下载后直接运行。

### 方式 2：Python 包

```bash
# 安装 CLI 版本
pip install meowth

# 安装 GUI 版本
pip install meowth[gui]
```

**系统要求**：Python 3.10+

### 方式 3：从源代码

```bash
git clone https://github.com/Olcmyk/Meowth-GBA-Translator.git
cd Meowth-GBA-Translator
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[gui,dev]"
```

---

## 配置

### API 密钥配置

翻译需要 LLM API 密钥。推荐使用 DeepSeek（性价比高）或 OpenAI。

#### 方法 1：环境变量（推荐）

创建 `.env` 文件（项目根目录）：

```bash
# DeepSeek（推荐，便宜且效果好）
DEEPSEEK_API_KEY=sk-your-deepseek-key-here

# 或 OpenAI
OPENAI_API_KEY=sk-your-openai-key-here

# 或 Google Gemini
GOOGLE_API_KEY=your-google-key-here
```

#### 方法 2：配置文件

创建 `meowth.toml` 文件（项目根目录）：

```toml
[translation]
provider = "deepseek"  # 或 "openai", "google", "anthropic" 等
source_language = "en"
target_language = "zh-Hans"  # 简体中文
model = "deepseek-chat"  # 可选，指定模型

[translation.api]
base_url = "https://api.deepseek.com"  # 可选，自定义 API 地址
key_env = "DEEPSEEK_API_KEY"  # API 密钥的环境变量名
```

### 支持的 LLM 提供商

| 提供商 | provider 值 | 推荐模型 | 价格 |
|--------|------------|---------|------|
| DeepSeek | `deepseek` | `deepseek-chat` | 💰 极低 |
| OpenAI | `openai` | `gpt-4o-mini` | 💰💰 中等 |
| Google Gemini | `google` | `gemini-1.5-flash` | 💰 低 |
| Anthropic Claude | `anthropic` | `claude-3-5-sonnet-20241022` | 💰💰💰 高 |
| Groq | `groq` | `llama-3.3-70b-versatile` | 💰 免费额度 |
| OpenRouter | `openrouter` | 多种模型 | 💰-💰💰💰 |

---

## 使用方法

### GUI 使用

#### 1. 启动 GUI

```bash
# 如果安装了 GUI 版本
meowth-gui

# 或从源代码
python -m meowth.gui
```

#### 2. 配置翻译

1. **选择 ROM 文件**：点击"选择 ROM"按钮，选择你的 GBA ROM 文件
2. **配置 LLM**：
   - 选择提供商（如 DeepSeek）
   - 输入 API 密钥（或使用环境变量）
   - 选择模型（可选）
3. **选择语言**：
   - 源语言：通常是 `en`（英语）
   - 目标语言：如 `zh-Hans`（简体中文）
4. **设置输出目录**：选择翻译后 ROM 的保存位置

#### 3. 开始翻译

点击"开始翻译"按钮，工具会自动完成三个步骤：

1. **提取文本**：从 ROM 中提取所有文本（约 1-2 分钟）
2. **翻译文本**：使用 LLM 翻译（约 5-30 分钟，取决于 ROM 大小和 API 速度）
3. **构建 ROM**：将翻译后的文本写入新 ROM（约 1-2 分钟）

#### 4. 查看结果

翻译完成后，在输出目录找到翻译后的 ROM 文件（如 `FireRed_zh.gba`）。

---

### CLI 使用

#### 完整流程（一条命令）

```bash
# 使用 DeepSeek 翻译成简体中文
meowth full pokemon_firered.gba --provider deepseek

# 使用 OpenAI 翻译成西班牙语
meowth full pokemon_emerald.gba --provider openai --target es

# 自定义输出目录
meowth full pokemon.gba --provider deepseek --output-dir ./translated --work-dir ./temp
```

#### 分步执行

如果需要更精细的控制，可以分步执行：

##### 步骤 1：提取文本

```bash
meowth extract pokemon_firered.gba -o work/texts.json
```

**输出**：`work/texts.json` - 包含所有提取的文本

##### 步骤 2：翻译文本

```bash
meowth translate work/texts.json -o work/texts_translated.json \
  --provider deepseek \
  --source en \
  --target zh-Hans \
  --batch-size 30 \
  --workers 10
```

**参数说明**：
- `--provider`：LLM 提供商
- `--source`：源语言代码
- `--target`：目标语言代码
- `--batch-size`：每批翻译的文本数量（默认 30）
- `--workers`：并行翻译线程数（默认 10）

**输出**：`work/texts_translated.json` - 包含翻译后的文本

##### 步骤 3：构建 ROM

```bash
meowth build pokemon_firered.gba \
  --translations work/texts_translated.json \
  -o outputs/FireRed_zh.gba \
  --source en \
  --target zh-Hans
```

**输出**：`outputs/FireRed_zh.gba` - 翻译后的 ROM

---

## 三步翻译流程详解

### 步骤 1：提取文本（Extract）

**功能**：从 ROM 中提取所有可翻译的文本

**技术细节**：
- 使用 MeowthBridge（C# 工具，基于 HexManiac Advance）
- 提取三类文本：
  1. **表格数据**：宝可梦名称、招式名称、道具名称等
  2. **脚本文本**：对话、剧情文本
  3. **自由文本**：通过指针扫描发现的其他文本

**输出格式**（`texts.json`）：

```json
{
  "tables": [
    {
      "category": "pokemon_names",
      "entries": [
        {
          "address": "0x245EE0",
          "original": "BULBASAUR",
          "id": "pokemon_0"
        }
      ]
    }
  ],
  "free_texts": [
    {
      "address": "0x1A8F9C",
      "original": "Welcome to the world of POKéMON!",
      "id": "scr_02329"
    }
  ]
}
```

**过滤规则**：
- 最少 15 个字母
- 至少 3 个单词
- 至少 2 个空格
- 字母比例 ≥ 40%
- 总长度 ≥ 20 字节
- 单词平均长度 2.0-15.0
- 至少包含 1 个常见英语单词

### 步骤 2：翻译文本（Translate）

**功能**：使用 LLM API 翻译提取的文本

**技术细节**：
- **批量翻译**：将文本分批（默认 30 条/批）发送给 LLM
- **并行处理**：使用多线程（默认 10 个）并行翻译
- **控制码保护**：翻译前保护游戏控制码（如 `\n`、`[player]`），翻译后恢复
- **术语表**：使用内置术语表确保宝可梦术语翻译一致
- **缓存机制**：翻译结果缓存在 `work/cache/`，避免重复翻译

**翻译策略**：
1. **表格数据**：优先使用术语表，未找到则使用 LLM
2. **脚本文本**：使用 LLM 翻译，保持上下文
3. **硬编码翻译**：部分重要文本（如开场白）使用预设翻译

**输出格式**（`texts_translated.json`）：

```json
{
  "tables": [
    {
      "category": "pokemon_names",
      "entries": [
        {
          "address": "0x245EE0",
          "original": "BULBASAUR",
          "translated": "妙蛙种子",
          "id": "pokemon_0"
        }
      ]
    }
  ],
  "free_texts": [
    {
      "address": "0x1A8F9C",
      "original": "Welcome to the world of POKéMON!",
      "translated": "欢迎来到宝可梦的世界！",
      "id": "scr_02329"
    }
  ]
}
```

### 步骤 3：构建 ROM（Build）

**功能**：将翻译后的文本写入 ROM，生成翻译版

**技术细节**：

#### 3.1 ROM 扩展
- 原版 ROM：16MB
- 扩展后：32MB
- 扩展区域（0x1000000+）：存放翻译后的文本

#### 3.2 字库注入（仅中文/日文/韩文）
- 使用 armips 汇编器注入字库
- 字库包含 6931 个字符：
  - 中文字符：2 字节编码（0x0100-0x1E5D）
  - 英文/数字：1 字节 PCS 编码
  - 终止符：0xFF

#### 3.3 文本注入
- **原地替换**：如果翻译后文本长度 ≤ 原文，直接替换
- **重定位**：如果翻译后文本更长，写入扩展区域，更新指针
- **指针更新**：自动更新所有指向该文本的指针

**注入统计示例**：

```
Injecting 6586 texts...
✓ In-place: 2341 texts
✓ Relocated: 4245 texts (to expansion area)
✓ Skipped: 0 texts
✓ Partial pointers: 12 (updated)
✓ Unsafe pointers: 0
```

---

## 常见问题

### Q1: 翻译需要多长时间？

**答**：取决于 ROM 大小和 API 速度：
- 火红/叶绿：约 10-20 分钟（~6500 条文本）
- 绿宝石：约 20-40 分钟（~10000 条文本）

### Q2: 翻译费用是多少？

**答**：取决于 LLM 提供商：
- **DeepSeek**：约 $0.10-0.30（推荐）
- **OpenAI GPT-4o-mini**：约 $0.50-1.50
- **Google Gemini Flash**：约 $0.20-0.60
- **Groq**：免费额度内可能免费

### Q3: 支持哪些 ROM？

**答**：
- ✅ **支持**：原版 ROM 和基于原版的二进制改版（binary hacks）
- ❌ **不支持**：decomp ROM（源码编译版本，如 pokeemerald、pokefirered）

**如何判断**：
- 原版 ROM：16MB，文件名如 `Pokemon - Fire Red Version (USA).gba`
- Decomp ROM：通常有自定义标题，大小不规则

### Q4: 翻译后游戏无法运行？

**答**：可能的原因：
1. **ROM 损坏**：确保原版 ROM 完整无损
2. **模拟器不兼容**：推荐使用 mGBA 或 VBA-M
3. **字库问题**：确保使用的是 binary ROM，而非 decomp ROM

### Q5: 部分文本没有翻译？

**答**：可能的原因：
1. **过滤规则**：文本太短或不符合过滤规则（如全大写标签）
2. **黑名单**：某些系统标签（如 "PP"、"HP"）在黑名单中
3. **提取失败**：某些文本可能未被正确提取

**解决方法**：
- 检查 `work/texts.json`，确认文本是否被提取
- 如果文本被过滤，可以修改 `src/MeowthBridge/TextExtractor.cs` 中的过滤规则
- 重新编译 MeowthBridge：`dotnet build src/MeowthBridge/MeowthBridge.csproj`

### Q6: 如何自定义翻译？

**答**：
1. **修改术语表**：编辑 `src/meowth/glossary.py`
2. **添加硬编码翻译**：编辑 `src/meowth/core/engine.py` 中的 `_HARDCODED_TRANSLATIONS`
3. **手动编辑翻译文件**：修改 `work/texts_translated.json`，然后只运行步骤 3（构建 ROM）

---

## 高级用法

### 自定义 LLM 提供商

如果使用自定义 OpenAI 兼容 API：

```bash
meowth full pokemon.gba \
  --api-base https://your-api.com/v1 \
  --api-key-env YOUR_API_KEY \
  --model your-model-name
```

### 批量翻译多个 ROM

```bash
#!/bin/bash
for rom in roms/*.gba; do
  echo "Translating $rom..."
  meowth full "$rom" --provider deepseek --output-dir translated/
done
```

### 使用自定义术语表

编辑 `src/meowth/glossary.py`，添加自定义术语：

```python
CUSTOM_TERMS = {
    "PIKACHU": "皮卡丘",
    "CHARIZARD": "喷火龙",
    # 添加更多...
}
```

### 调试模式

```bash
# 启用详细日志
export MEOWTH_DEBUG=1
meowth full pokemon.gba --provider deepseek
```

### 仅翻译特定类别

修改 `work/texts.json`，删除不需要翻译的类别，然后运行：

```bash
meowth translate work/texts.json -o work/texts_translated.json --provider deepseek
meowth build pokemon.gba --translations work/texts_translated.json -o output.gba
```

---

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Meowth GBA Translator                    │
├─────────────────────────────────────────────────────────────┤
│  GUI (CustomTkinter)          CLI (Click)                   │
│         │                          │                         │
│         └──────────┬───────────────┘                         │
│                    │                                         │
│         ┌──────────▼──────────┐                             │
│         │  TranslationEngine  │                             │
│         └──────────┬──────────┘                             │
│                    │                                         │
│      ┌─────────────┼─────────────┐                          │
│      │             │             │                          │
│  ┌───▼───┐   ┌────▼────┐   ┌───▼────┐                      │
│  │Extract│   │Translate│   │ Build  │                      │
│  └───┬───┘   └────┬────┘   └───┬────┘                      │
│      │            │            │                            │
│  ┌───▼────┐  ┌───▼────┐  ┌───▼────┐                        │
│  │Meowth  │  │  LLM   │  │  ROM   │                        │
│  │Bridge  │  │  API   │  │ Writer │                        │
│  │(C#)    │  │        │  │        │                        │
│  └────────┘  └────────┘  └────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 致谢

- [HexManiac Advance](https://github.com/haven1433/HexManiacAdvance) - ROM 编辑器
- [armips](https://github.com/Kingcom/armips) - 汇编器
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - GUI 框架

---

**问题反馈**：[GitHub Issues](https://github.com/Olcmyk/Meowth-GBA-Translator/issues)

**项目主页**：[GitHub](https://github.com/Olcmyk/Meowth-GBA-Translator)
