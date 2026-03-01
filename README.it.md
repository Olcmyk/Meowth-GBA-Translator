# Meowth Traduttore GBA

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org)
[![Version](https://img.shields.io/badge/Version-0.3.0-green.svg)](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**Lingue** | [English](./README.md) | [中文](./README.zh.md) | [Français](./README.fr.md) | [Deutsch](./README.de.md) | [Español](./README.es.md)

🐱 Un traduttore ROM GBA Pokémon intelligente alimentato da LLM con interfacce GUI e CLI

</div>

---

## 📋 Panoramica

**Meowth GBA Translator** è uno strumento completo per tradurre i giochi Pokémon Game Boy Advance (GBA) in diverse lingue. Combina l'estrazione automatica del testo, la traduzione alimentata da LLM e la creazione intelligente della ROM per semplificare il flusso di lavoro di traduzione.

### Caratteristiche principali

- 🎮 **Interfaccia doppia**: GUI user-friendly e CLI potente
- 🤖 **Traduzione IA**: Supporto per 11+ fornitori LLM
- 📦 **Multipiattaforma**: macOS, Windows, Linux
- 🌍 **Supporto multilingue**: Traduci in qualsiasi lingua
- ⚡ **Flusso di lavoro ottimizzato**: Estrai → Traduci → Crea in un comando
- 🎁 **Gratuito**: 100% open source, licenza MIT
- 🔤 **Patch font intelligente**: Iniezione automatica del font

### ⚠️ Importante: Metodi di traduzione

> **⚠️ SOLO PATCHING BINARIO**
>
> Questo strumento supporta **solo** il metodo di patching binario:
> - ✅ Estrai testo → Traduci → Reinietta nella ROM
> - ❌ **NON compatibile con progetti di decompilazione**
> - ❌ L'iniezione di font è difficile nei progetti decomp
>
> Per le ROM decompilate, utilizza gli strumenti specifici del progetto.

---

## 📦 Installazione

### Opzione 1: Applicazione GUI (Consigliato)

Scarica l'ultima versione:

- 🍎 **macOS**: [Meowth-Translator-macOS.dmg](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)
- 🪟 **Windows**: [Meowth-Translator-Windows.zip](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**Requisiti**:
- macOS 10.13+ o Windows 10+
- Non è richiesta l'installazione

### Opzione 2: Pacchetto Python

```bash
# Solo CLI
pip install meowth

# Con supporto GUI
pip install meowth[gui]
```

**Requisiti**:
- Python 3.10 o versione successiva

### Opzione 3: Dal sorgente

```bash
git clone https://github.com/Olcmyk/Meowth-GBA-Translator.git
cd Meowth-GBA-Translator

python3 -m venv venv
source venv/bin/activate

pip install -e ".[gui,dev]"
meowth-gui
```

---

## 🚀 Avvio rapido

### Usa l'interfaccia GUI

1. Scarica e avvia **Meowth Translator**
2. Fai clic su "Seleziona ROM" e scegli la tua ROM GBA Pokémon
3. Configura le impostazioni di traduzione
4. Fai clic su "Avvia traduzione"
5. Attendi il completamento
6. Scarica la ROM tradotta

### Usa la CLI

```bash
export DEEPSEEK_API_KEY="sk-your-key"

meowth full pokemon_firered.gba \
  --provider deepseek \
  --source en \
  --target it \
  --output-dir translated_roms
```

---

## 🤖 Fornitori LLM supportati

| Fornitore | Modello predefinito | Chiave API | Costo |
|-----------|------------------|---------|-------|
| **DeepSeek** | deepseek-chat | `DEEPSEEK_API_KEY` | 💰 Molto economico |
| **OpenAI** | gpt-4o | `OPENAI_API_KEY` | 💰💰 Moderato |
| **Google Gemini** | gemini-2.0-flash | `GOOGLE_API_KEY` | 🆓 Gratuito |
| **Claude (Anthropic)** | claude-sonnet-4 | `ANTHROPIC_API_KEY` | 💰💰 Moderato |
| **Groq** | llama-3.3-70b | `GROQ_API_KEY` | 🆓 Gratuito |

---

## 📖 Guida all'uso

### Comandi CLI

#### 1. Flusso di lavoro completo (Consigliato)

```bash
meowth full pokemon.gba \
  --provider deepseek \
  --source en \
  --target it \
  --output-dir outputs
```

#### 2. Passo dopo passo

```bash
# Estrai
meowth extract pokemon.gba -o texts.json

# Traduci
meowth translate texts.json --provider deepseek --target it -o texts_translated.json

# Crea
meowth build pokemon.gba --translations texts_translated.json -o pokemon_it.gba
```

---

## 🌍 Lingue supportate

- 🇮🇹 **Italiano** - `it`
- 🇬🇧 **Inglese** - `en`
- 🇫🇷 **Francese** - `fr`
- 🇩🇪 **Tedesco** - `de`
- 🇪🇸 **Spagnolo** - `es`
- 🇨🇳 **Cinese** - `zh-Hans`, `zh-Hant`
- 🇯🇵 **Giapponese** - `ja`

E molti altri...

---

## ⚙️ Configurazione

### Variabili d'ambiente

```bash
export DEEPSEEK_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."
```

### File di configurazione (meowth.toml)

```toml
[translation]
provider = "deepseek"
model = "deepseek-chat"
source_language = "en"
target_language = "it"
```

---

## 🎮 Giochi supportati

- Pokémon FireRed
- Pokémon LeafGreen
- Pokémon Smeraldo
- Pokémon Rubino/Zaffiro
- Pokémon Mystery Dungeon

---

## 📄 Licenza

Licenza MIT - vedere il file [LICENSE](LICENSE)

---

**Creato con ❤️ per la comunità di localizzazione Pokémon**
