# Meowth GBA 翻译工具

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org)
[![Version](https://img.shields.io/badge/Version-0.3.0-green.svg)](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**语言** | [English](./README.md) | [Français](./README.fr.md) | [Deutsch](./README.de.md) | [Italiano](./README.it.md) | [Español](./README.es.md)

使用 LLM 驱动的智能 GBA 宝可梦 ROM 翻译工具，提供 GUI 和 CLI 两种界面

</div>

---

## 项目简介

**Meowth GBA 翻译工具**是一款专为宝可梦Game Boy Advance (GBA) ROM 翻译而设计的综合工具。它结合了自动文本提取、AI驱动的智能翻译和ROM构建功能，大大简化了翻译流程。

### 主要特点

- **双界面支持**：提供用户友好的 GUI 和强大的 CLI
- **AI翻译**：支持 11+ 个 LLM 提供商（OpenAI、DeepSeek、Google Gemini 等）
- **跨平台**：支持 macOS、Windows、Linux
- **六种语言支持**：英语、西班牙语、法语、德语、意大利语、中文
- **高效工作流**：一条命令完成提取 → 翻译 → 构建
- **完全免费**：100% 开源，MIT 协议
- **智能字库**：中文翻译自动注入字库


## 安装

### 方式1：GUI 应用（推荐大多数用户）

下载最新版本：

- **macOS**：[Meowth-Translator-macOS.dmg](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)
- **Windows**：[Meowth-Translator-Windows.zip](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**系统要求**：
- macOS 10.13+ 或 Windows 10+
- 无需安装，下载后直接运行

### 方式2：Python 包（开发者/CLI 用户）

```bash
# 仅安装 CLI
pip install meowth

# 或安装 GUI 支持
pip install meowth[gui]
```

**系统要求**：
- Python 3.10 或更高版本
- pip 包管理器

### 方式3：从源代码构建

```bash
# 克隆仓库
git clone https://github.com/Olcmyk/Meowth-GBA-Translator.git
cd Meowth-GBA-Translator

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 以开发模式安装
pip install -e ".[gui,dev]"

# 运行 GUI
meowth-gui

# 或使用 CLI
meowth full pokemon.gba --provider deepseek
```

---

## 快速开始

### 使用 GUI（最简单）

![GUI 截图](https://raw.githubusercontent.com/Olcmyk/Meowth-GBA-Translator/main/images/gui-screenshot.png)

1. 下载并运行 **Meowth 翻译工具**
2. 点击"选择 ROM"，选择你的 GBA 宝可梦 ROM
3. 配置翻译设置：
   - **LLM 提供商**：选择 LLM 提供商（OpenAI、DeepSeek 等）
   - **源语言**：通常是"英文"
   - **目标语言**：你想翻译成的语言
4. 点击"开始翻译"
5. 等待完成（通常 5-30 分钟，取决于 ROM 大小）
6. 从输出文件夹下载翻译后的 ROM

![翻译对比](https://raw.githubusercontent.com/Olcmyk/Meowth-GBA-Translator/main/images/translation-comparison.jpg)
*左：原版游戏 | 右：翻译后游戏*

### 使用 CLI

#### 步骤1：配置 API 密钥

首先，设置 API 密钥环境变量：

```bash
# DeepSeek（推荐）
export DEEPSEEK_API_KEY="sk-你的密钥"

# 或其他提供商
export OPENAI_API_KEY="sk-你的密钥"
export GOOGLE_API_KEY="你的密钥"
```

#### 步骤2：运行翻译

```bash
# 运行完整翻译流程
meowth full pokemon_firered.gba \
  --provider deepseek \
  --source en \
  --target zh-Hans \
  --output-dir translated_roms

# 翻译后的 ROM 将保存到：translated_roms/pokemon_firered_zh.gba
```

---

## 支持的 LLM 提供商

| 提供商 | 默认模型 | API 密钥 |
|-------|---------|--------|
| **DeepSeek** | deepseek-chat | `DEEPSEEK_API_KEY` |
| **OpenAI** | gpt-4o | `OPENAI_API_KEY` |
| **Google Gemini** | gemini-2.0-flash | `GOOGLE_API_KEY` |
| **Claude（Anthropic）** | claude-sonnet-4 | `ANTHROPIC_API_KEY` |
| **Groq** | llama-3.3-70b | `GROQ_API_KEY` |
| **Mistral** | mistral-large-latest | `MISTRAL_API_KEY` |
| **OpenRouter** | openai/gpt-4o | `OPENROUTER_API_KEY` |
| **硅基流动**|DeepSeek-V3 | `SILICONFLOW_API_KEY` |
| **智谱 GLM** | glm-4-flash | `ZHIPU_API_KEY` |
| **Moonshot** | moonshot-v1-8k | `MOONSHOT_API_KEY` |
| **通义千问** | qwen-plus | `DASHSCOPE_API_KEY` |

**推荐**：我们推荐使用 **DeepSeek**，因为本工具在开发和测试时一直使用 DeepSeek。翻译一个典型的 GBA 宝可梦 ROM 大约需要 2 元人民币。

---

## 使用指南

### CLI 命令

#### 1. 完整流程（推荐）

一条命令完成提取、翻译和构建：

```bash
meowth full pokemon.gba \
  --provider deepseek \
  --source en \
  --target zh-Hans \
  --output-dir outputs
```

**选项说明**：
- `--provider`：使用的 LLM 提供商
- `--source`：源语言代码（默认："en"）
- `--target`：目标语言代码（默认："zh-Hans"）
- `--output-dir`：输出文件夹（默认："outputs"）
- `--work-dir`：临时工作文件夹（默认："work"）
- `--batch-size`：每批翻译的文本数（默认：30）
- `--workers`：并行翻译线程数（默认：10）
- `--api-base`：自定义 API 地址（用于 OpenAI 兼容 API）
- `--api-key-env`：API 密钥的环境变量名
- `--model`：自定义模型名称

#### 2. 分步流程

供需要更多控制的高级用户使用：

```bash
# 步骤1：从 ROM 提取文本
meowth extract pokemon.gba -o texts.json

# 步骤2：翻译文本
export DEEPSEEK_API_KEY="sk-你的密钥"
meowth translate texts.json \
  --provider deepseek \
  --target zh-Hans \
  -o texts_translated.json

# 步骤3：构建翻译后的 ROM
meowth build pokemon.gba \
  --translations texts_translated.json \
  -o pokemon_zh.gba
```

#### 3. 使用配置文件（meowth.toml）

在工作目录创建 `meowth.toml`：

```toml
[translation]
provider = "deepseek"
model = "deepseek-chat"
source_language = "en"
target_language = "zh-Hans"

[translation.api]
key_env = "DEEPSEEK_API_KEY"
base_url = "https://api.deepseek.com/v1"
```

然后简单运行：
```bash
export DEEPSEEK_API_KEY="sk-你的密钥"
meowth full pokemon.gba
```

### GUI 功能

GUI 提供友好的界面，包括：

- **ROM 选择**：浏览和选择你的 GBA 宝可梦 ROM
- **提供商配置**：轻松设置 LLM API 密钥
- **翻译设置**：配置源/目标语言和翻译参数
- **进度跟踪**：实时进度更新和详细日志
- **错误处理**：清晰的错误提示和解决建议
- **输出管理**：整理和管理翻译后的 ROM

---

## 支持的语言

目前支持的语言：

- **英语** - `en`
- **西班牙语** - `es`
- **法语** - `fr`
- **德语** - `de`
- **意大利语** - `it`
- **中文** - `zh-Hans`

**重要**：翻译为中文时，只支持二进制改版 ROM，不支持反编译项目。其他语言组合没有此限制。

## 配置

### 环境变量

在你的 shell 或 `.env` 文件中设置：

```bash
# API 密钥
export DEEPSEEK_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."

# 可选：自定义 API 地址（用于 OpenAI 兼容服务）
export CUSTOM_API_BASE="https://api.example.com/v1"
```

### 配置文件（meowth.toml）

```toml
[translation]
provider = "deepseek"              # LLM 提供商
model = "deepseek-chat"            # 模型名称
source_language = "en"             # 源语言代码
target_language = "zh-Hans"        # 目标语言代码
batch_size = 30                    # 每批文本数
max_workers = 10                   # 并行工作线程数

[translation.api]
key_env = "DEEPSEEK_API_KEY"       # API 密钥的环境变量名
base_url = "https://api.deepseek.com/v1"  # API 端点地址
```


## 高级用法

### 使用自定义模型

使用提供商的其他模型：

```bash
# OpenAI with GPT-4 Turbo
meowth full pokemon.gba \
  --provider openai \
  --model gpt-4-turbo \
  --target zh-Hans

# DeepSeek 特定版本
meowth full pokemon.gba \
  --provider deepseek \
  --model deepseek-chat \
  --target zh-Hans
```

### 使用自定义 API 端点

用于 OpenAI 兼容的 API：

```bash
meowth full pokemon.gba \
  --provider openai \
  --api-base "https://api.yourservice.com/v1" \
  --api-key-env "YOUR_API_KEY" \
  --model "your-model" \
  --target zh-Hans
```

### 批量翻译

翻译多个 ROM：

```bash
for rom in *.gba; do
  meowth full "$rom" \
    --provider deepseek \
    --target zh-Hans \
    --output-dir translated/
done
```

### 性能调优

调整批大小和工作线程数以获得最佳性能：

```bash
# 更快（更激进，成本更高）
meowth full pokemon.gba \
  --provider deepseek \
  --batch-size 50 \
  --workers 20 \
  --target zh-Hans

# 更慢（更保守，成本更低）
meowth full pokemon.gba \
  --provider deepseek \
  --batch-size 10 \
  --workers 5 \
  --target zh-Hans
```


## 支持的游戏

本工具已在以下游戏中测试过：

- 宝可梦 Gaia v3.2
- 宝可梦 SeaGlass v3.0
- 宝可梦 Rogue Ex v2.0.1a

其他 GBA 宝可梦游戏应该也能工作，但可能需要调整。


## 故障排除

### "找不到 MeowthBridge"
- **原因**：应用程序文件损坏或安装不完整
- **解决方案**：重新安装应用程序或从源代码重新构建

### "API 密钥未找到"
- **原因**：API 密钥环境变量未设置
- **解决方案**：
  ```bash
  export DEEPSEEK_API_KEY="sk-你的实际密钥"
  ```

### GUI 无法启动（macOS）
- **原因**：macOS 首次运行的安全限制
- **解决方案**：
  1. 前往"系统设置" → "隐私与安全性"
  2. 找到关于"Meowth Translator"被阻止的消息
  3. 点击"仍要打开"

### "ROM 提取失败"
- **原因**：ROM 可能损坏或格式不支持
- **解决方案**：
  1. 验证 ROM 是有效的 GBA 文件
  2. 如果要翻译为中文，请确保 ROM 不是反编译项目
  3. 先用已知有效的 ROM 测试

更多帮助，请查看 [GitHub Issues](https://github.com/Olcmyk/Meowth-GBA-Translator/issues)

---

## 翻译过程说明

### 第1阶段：提取（meowth extract）
- 扫描 ROM 查找可翻译的文本
- 提取字符串、对话、物品名称等
- 输出：`texts.json`
- 耗时：约 30 秒

### 第2阶段：翻译（meowth translate）
- 将文本批次发送给 LLM
- 保留特殊代码和格式
- 应用语言特定优化
- 输出：`texts_translated.json`
- 耗时：5-30 分钟（取决于 ROM 大小和 LLM 速度）

### 第3阶段：构建（meowth build）
- 将翻译文本注入回 ROM
- 对于中文：应用字库补丁（必需）
- 创建最终翻译 ROM
- 输出：`pokemon_zh.gba`
- 耗时：约 1 分钟

---

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

---

## 致谢

本项目使用了以下项目：

- [HexManiacAdvance](https://github.com/entropyus/HexManiacAdvance) - ROM 提取和注入
- [Pokemon_GBA_Font_Patch](https://github.com/Wokann/Pokemon_GBA_Font_Patch) - 中文字库补丁
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) - 现代 GUI 框架
- [click](https://click.palletsprojects.com/) - CLI 框架
- [LLM 提供商](https://openai.com/) - AI 驱动的翻译

---

## 支持

- 发现 bug？[提交 Issue](https://github.com/Olcmyk/Meowth-GBA-Translator/issues)
- 有问题？[开启讨论](https://github.com/Olcmyk/Meowth-GBA-Translator/discussions)
- 喜欢这个项目？[在 GitHub 上给我们一个 Star](https://github.com/Olcmyk/Meowth-GBA-Translator)

---

## 贡献

欢迎贡献！你可以帮助的领域：

- 添加更多语言支持
- 添加将反编译改版汉化的功能
- 改进 GUI/UX
- 编写文档

---

**用 ❤️ 为宝可梦汉化社区创作**
