# Meowth GBA Translator

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org)
[![Version](https://img.shields.io/badge/Version-0.3.0-green.svg)](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**Languages** | [中文](./README.zh.md) | [Français](./README.fr.md) | [Deutsch](./README.de.md) | [Italiano](./README.it.md) | [Español](./README.es.md)

🐱 An intelligent GBA Pokémon ROM translator powered by LLM with both GUI and CLI interfaces

</div>

---

## 📋 Overview

**Meowth GBA Translator** is a comprehensive tool for translating Pokémon Game Boy Advance (GBA) ROMs into different languages. It combines automated text extraction, intelligent LLM-powered translation, and intelligent ROM building to streamline the translation workflow.

### Key Features

- 🎮 **Dual Interface**: Use the user-friendly GUI or powerful CLI
- 🤖 **AI-Powered Translation**: Support for 11+ LLM providers (OpenAI, DeepSeek, Google Gemini, etc.)
- 📦 **Multi-Platform**: macOS, Windows, Linux support
- 🌍 **Multi-Language Support**: Translate to any language (with optimized templates for Chinese, Japanese, Spanish, etc.)
- ⚡ **Optimized Workflow**: Extract → Translate → Build in one command
- 🎁 **Free**: 100% open source and MIT licensed
- 🔤 **Smart Font Patching**: Automatic font injection for supported languages

### Important Notes on Localization Methods

> **⚠️ BINARY PATCHING ONLY**
>
> This tool supports **binary patching** method only:
> - ✅ Extract text from original ROM → Translate → Insert translations back
> - ❌ **NOT compatible with decompilation-based projects** (like Pokémon Emerald decomp)
> - ❌ Font injection is difficult/impossible in decomp due to structural differences
>
> If your target ROM is a decomp project, you'll need to use decomp-specific tools and methods.

---

## 📦 Installation

### Option 1: GUI Application (Recommended for Most Users)

Download the latest release for your platform:

- 🍎 **macOS**: [Meowth-Translator-macOS.dmg](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)
- 🪟 **Windows**: [Meowth-Translator-Windows.zip](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**Requirements:**
- macOS 10.13+ or Windows 10+
- No installation needed, just run the application

### Option 2: Python Package (For Developers/CLI Users)

```bash
# Install CLI only
pip install meowth

# Or install with GUI support
pip install meowth[gui]
```

**Requirements:**
- Python 3.10 or higher
- pip package manager

### Option 3: Build from Source

```bash
# Clone the repository
git clone https://github.com/Olcmyk/Meowth-GBA-Translator.git
cd Meowth-GBA-Translator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[gui,dev]"

# Run GUI
meowth-gui

# Or use CLI
meowth full pokemon.gba --provider deepseek
```

---

## 🚀 Quick Start

### Using GUI (Easiest)

1. Download and run **Meowth Translator**
2. Click "Select ROM" and choose your GBA Pokémon ROM
3. Configure translation settings:
   - **Provider**: Select LLM provider (OpenAI, DeepSeek, etc.)
   - **Source Language**: Usually "English"
   - **Target Language**: Your desired language
4. Click "Start Translation"
5. Wait for the process to complete (typically 5-30 minutes depending on ROM size)
6. Download the translated ROM from the output folder

### Using CLI

```bash
# Set up API key (example: DeepSeek)
export DEEPSEEK_API_KEY="sk-your-api-key"

# Run full translation pipeline
meowth full pokemon_firered.gba \
  --provider deepseek \
  --source en \
  --target zh-Hans \
  --output-dir translated_roms

# The translated ROM will be saved to: translated_roms/pokemon_firered_zh.gba
```

---

## 🤖 Supported LLM Providers

| Provider | Default Model | Required API Key | Cost |
|----------|---------------|------------------|------|
| **DeepSeek** | deepseek-chat | `DEEPSEEK_API_KEY` | 💰 Very cheap |
| **OpenAI** | gpt-4o | `OPENAI_API_KEY` | 💰💰 Moderate |
| **Google Gemini** | gemini-2.0-flash | `GOOGLE_API_KEY` | 🆓 Free tier |
| **Anthropic Claude** | claude-sonnet-4 | `ANTHROPIC_API_KEY` | 💰💰 Moderate |
| **Groq** | llama-3.3-70b-versatile | `GROQ_API_KEY` | 🆓 Free |
| **Mistral** | mistral-large-latest | `MISTRAL_API_KEY` | 💰 Cheap |
| **OpenRouter** | openai/gpt-4o | `OPENROUTER_API_KEY` | 💰 Variable |
| **SiliconFlow** | DeepSeek-V3 | `SILICONFLOW_API_KEY` | 💰 Very cheap |
| **Zhipu GLM** | glm-4-flash | `ZHIPU_API_KEY` | 💰 Cheap |
| **Moonshot** | moonshot-v1-8k | `MOONSHOT_API_KEY` | 💰 Cheap |
| **Qwen** | qwen-plus | `DASHSCOPE_API_KEY` | 💰 Cheap |

**Recommendation**: Start with **DeepSeek** (cheapest) or **Google Gemini** (free tier available)

---

## 📖 Usage Guide

### CLI Commands

#### 1. Full Pipeline (Recommended)

Extracts text, translates, and builds the ROM in one command:

```bash
meowth full pokemon.gba \
  --provider deepseek \
  --source en \
  --target zh-Hans \
  --output-dir outputs
```

**Options:**
- `--provider`: LLM provider to use
- `--source`: Source language code (default: "en")
- `--target`: Target language code (default: "zh-Hans")
- `--output-dir`: Directory to save translated ROM (default: "outputs")
- `--work-dir`: Temporary working directory (default: "work")
- `--batch-size`: Texts per LLM batch (default: 30)
- `--workers`: Parallel translation threads (default: 10)
- `--api-base`: Custom API base URL (for OpenAI-compatible APIs)
- `--api-key-env`: Environment variable name for API key
- `--model`: Specify a custom model name

#### 2. Step-by-Step Pipeline

For advanced users who need more control:

```bash
# Step 1: Extract texts from ROM
meowth extract pokemon.gba -o texts.json

# Step 2: Translate texts
export DEEPSEEK_API_KEY="sk-your-key"
meowth translate texts.json \
  --provider deepseek \
  --target zh-Hans \
  -o texts_translated.json

# Step 3: Build translated ROM
meowth build pokemon.gba \
  --translations texts_translated.json \
  -o pokemon_zh.gba
```

#### 3. Using Configuration File (meowth.toml)

Create a `meowth.toml` file in your working directory:

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

Then simply run:
```bash
export DEEPSEEK_API_KEY="sk-your-key"
meowth full pokemon.gba
```

### GUI Features

The GUI provides a user-friendly interface with:

- **ROM Selection**: Browse and select your GBA Pokémon ROM
- **Provider Configuration**: Easy setup of LLM API keys
- **Translation Settings**: Configure source/target languages and translation parameters
- **Progress Tracking**: Real-time progress updates with detailed logging
- **Error Handling**: Clear error messages and suggestions for fixes
- **Output Management**: Organize and manage translated ROMs

---

## 🌍 Language Support

The tool uses smart prompt templates optimized for each target language:

### Fully Optimized Languages

- 🇨🇳 **Chinese (Simplified)** - `zh-Hans`
- 🇨🇳 **Chinese (Traditional)** - `zh-Hant`
- 🇯🇵 **Japanese** - `ja`

### Supported Languages

- 🇬🇧 **English** - `en`
- 🇪🇸 **Spanish** - `es`
- 🇫🇷 **French** - `fr`
- 🇩🇪 **German** - `de`
- 🇮🇹 **Italian** - `it`
- 🇵🇹 **Portuguese** - `pt`
- 🇷🇺 **Russian** - `ru`
- 🇰🇷 **Korean** - `ko`

Or any other language (using generic template)

---

## ⚙️ Configuration

### Environment Variables

Set these in your shell or `.env` file:

```bash
# API Keys
export DEEPSEEK_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."

# Optional: Custom API base URL (for OpenAI-compatible services)
export CUSTOM_API_BASE="https://api.example.com/v1"
```

### Configuration File (meowth.toml)

```toml
[translation]
provider = "deepseek"           # LLM provider
model = "deepseek-chat"         # Model name
source_language = "en"          # Source language code
target_language = "zh-Hans"     # Target language code
batch_size = 30                 # Texts per batch
max_workers = 10                # Parallel workers

[translation.api]
key_env = "DEEPSEEK_API_KEY"    # Environment variable for API key
base_url = "https://api.deepseek.com/v1"  # API endpoint URL
```

---

## 🔧 Advanced Usage

### Custom LLM Models

Use a different model with your provider:

```bash
# OpenAI with GPT-4 Turbo
meowth full pokemon.gba \
  --provider openai \
  --model gpt-4-turbo \
  --target zh-Hans

# DeepSeek with specific version
meowth full pokemon.gba \
  --provider deepseek \
  --model deepseek-chat \
  --target zh-Hans
```

### Using Custom API Endpoints

For OpenAI-compatible APIs:

```bash
meowth full pokemon.gba \
  --provider openai \
  --api-base "https://api.yourservice.com/v1" \
  --api-key-env "YOUR_API_KEY" \
  --model "your-model" \
  --target zh-Hans
```

### Batch Translation

Translate multiple ROMs:

```bash
for rom in *.gba; do
  meowth full "$rom" \
    --provider deepseek \
    --target zh-Hans \
    --output-dir translated/
done
```

### Performance Tuning

Adjust batch size and worker count for optimal performance:

```bash
# Faster (more aggressive, higher cost)
meowth full pokemon.gba \
  --provider deepseek \
  --batch-size 50 \
  --workers 20 \
  --target zh-Hans

# Slower (more conservative, lower cost)
meowth full pokemon.gba \
  --provider deepseek \
  --batch-size 10 \
  --workers 5 \
  --target zh-Hans
```

---

## 🎮 Supported Games

This tool has been tested with:

- Pokémon FireRed
- Pokémon LeafGreen
- Pokémon Emerald
- Pokémon Ruby/Sapphire
- Pokémon Mystery Dungeon: Red Rescue Team

Other GBA Pokémon games should work but may need adjustments.

> **Note**: This tool is for **binary patching only**. If your target is a decompiled ROM (like Pokémon Emerald decomp), use decomp-specific tools instead.

---

## 🐛 Troubleshooting

### "Could not find MeowthBridge"
- **Cause**: Application files are corrupted or incompletely installed
- **Solution**: Reinstall the application or rebuild from source

### "API Key not found"
- **Cause**: API key environment variable is not set
- **Solution**:
  ```bash
  export DEEPSEEK_API_KEY="sk-your-actual-key"
  ```

### "Translation quality is poor"
- **Cause**: Model may not be optimal for the target language
- **Solution**: Try a more powerful model:
  ```bash
  meowth full pokemon.gba --provider openai --model gpt-4o --target zh-Hans
  ```

### GUI doesn't launch (macOS)
- **Cause**: Security restrictions on first run
- **Solution**:
  1. Open Applications folder
  2. Right-click "Meowth Translator"
  3. Select "Open" (ignore security warning)

### "ROM extraction failed"
- **Cause**: ROM might be corrupted or unsupported format
- **Solution**:
  1. Verify the ROM is a valid GBA file
  2. Ensure the ROM is not a decomp project
  3. Try a known working ROM first

For more help, check [GitHub Issues](https://github.com/Olcmyk/Meowth-GBA-Translator/issues)

---

## 📝 Translation Process Explained

### Phase 1: Extraction (meowth extract)
- Scans the ROM for translatable text
- Extracts strings, dialogue, item names, etc.
- Outputs: `texts.json`
- Time: ~30 seconds

### Phase 2: Translation (meowth translate)
- Sends text batches to the LLM
- Preserves special codes and formatting
- Applies language-specific optimizations
- Outputs: `texts_translated.json`
- Time: 5-30 minutes (depends on ROM size and LLM speed)

### Phase 3: Building (meowth build)
- Injects translated text back into the ROM
- Applies font patches if needed
- Creates the final translated ROM
- Outputs: `pokemon_zh.gba`
- Time: ~1 minute

---

## 💡 Tips for Best Results

1. **Start with a test ROM**: Try with a smaller or known ROM first
2. **Use Chinese optimized templates**: For Chinese translations, the tool uses specialized prompts
3. **Monitor API costs**: Start with DeepSeek or free tier providers
4. **Keep translations simple**: Shorter, simpler translations are usually better
5. **Test on console**: Always test the translated ROM on your GBA emulator or console
6. **Backup originals**: Always keep the original ROM safe

---

## 🤝 Contributing

Contributions are welcome! Areas you can help:

- Adding support for more Pokémon games
- Improving translation quality for specific languages
- Adding new LLM providers
- Improving GUI/UX
- Writing documentation

See [Development Setup](./docs/DEVELOPMENT.md) for details

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

---

## 🙏 Credits

Built with:

- [HexManiacAdvance](https://github.com/entropyus/HexManiacAdvance) - ROM extraction and injection
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern GUI framework
- [click](https://click.palletsprojects.com/) - CLI framework
- [LLM Providers](https://openai.com/) - AI-powered translation

---

## 📞 Support

- 🐛 Found a bug? [Create an Issue](https://github.com/Olcmyk/Meowth-GBA-Translator/issues)
- 💬 Have a question? [Start a Discussion](https://github.com/Olcmyk/Meowth-GBA-Translator/discussions)
- 🌟 Like the project? [Star us on GitHub](https://github.com/Olcmyk/Meowth-GBA-Translator)

---

**Made with ❤️ for the Pokémon fan translation community**
