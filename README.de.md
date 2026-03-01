# Meowth GBA Übersetzer

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org)
[![Version](https://img.shields.io/badge/Version-0.3.0-green.svg)](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**Sprachen** | [English](./README.md) | [中文](./README.zh.md) | [Français](./README.fr.md) | [Italiano](./README.it.md) | [Español](./README.es.md)

🐱 Ein intelligenter GBA Pokémon ROM-Übersetzer mit LLM-Antrieb mit GUI und CLI-Schnittstellen

</div>

---

## 📋 Überblick

**Meowth GBA Translator** ist ein umfassendes Tool zum Übersetzen von Pokémon Game Boy Advance (GBA)-Spielen in verschiedene Sprachen. Es kombiniert automatische Textextraktion, LLM-gestützte Übersetzung und intelligente ROM-Erstellung, um den Übersetzungsworkflow zu rationalisieren.

### Hauptmerkmale

- 🎮 **Duale Schnittstelle**: Benutzerfreundliche GUI und leistungsstarke CLI
- 🤖 **KI-Übersetzung**: Unterstützung für 11+ LLM-Anbieter
- 📦 **Plattformübergreifend**: macOS, Windows, Linux
- 🌍 **Mehrsprachunterstützung**: In jede Sprache übersetzen
- ⚡ **Optimierter Workflow**: Extrahieren → Übersetzen → Erstellen in einem Befehl
- 🎁 **Kostenlos**: 100% Open Source, MIT-Lizenz
- 🔤 **Intelligentes Schriftarten-Patching**: Automatische Schrifteinspritzung

### ⚠️ Wichtig: Übersetzungsmethoden

> **⚠️ NUR BINÄRES PATCHING**
>
> Dieses Tool unterstützt **nur** die Methode des binären Patchings:
> - ✅ Text extrahieren → Übersetzen → In ROM zurück injizieren
> - ❌ **NICHT kompatibel mit Decompilation-Projekten**
> - ❌ Schrifteinspritzung ist bei Decomp-Projekten schwierig
>
> Für dekompilierte ROMs verwenden Sie projektspezifische Tools.

---

## 📦 Installation

### Option 1: GUI-Anwendung (Empfohlen)

Laden Sie die neueste Version herunter:

- 🍎 **macOS**: [Meowth-Translator-macOS.dmg](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)
- 🪟 **Windows**: [Meowth-Translator-Windows.zip](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**Anforderungen**:
- macOS 10.13+ oder Windows 10+
- Keine Installation erforderlich

### Option 2: Python-Paket

```bash
# Nur CLI
pip install meowth

# Mit GUI-Unterstützung
pip install meowth[gui]
```

**Anforderungen**:
- Python 3.10 oder höher

### Option 3: Aus Quellcode

```bash
git clone https://github.com/Olcmyk/Meowth-GBA-Translator.git
cd Meowth-GBA-Translator

python3 -m venv venv
source venv/bin/activate

pip install -e ".[gui,dev]"
meowth-gui
```

---

## 🚀 Schnelleinstieg

### GUI verwenden

1. Laden Sie **Meowth Translator** herunter und starten Sie es
2. Klicken Sie auf "ROM auswählen" und wählen Sie Ihre GBA Pokémon ROM
3. Konfigurieren Sie die Übersetzungseinstellungen
4. Klicken Sie auf "Übersetzung starten"
5. Warten Sie auf den Abschluss
6. Laden Sie die übersetzte ROM herunter

### CLI verwenden

```bash
export DEEPSEEK_API_KEY="sk-your-key"

meowth full pokemon_firered.gba \
  --provider deepseek \
  --source en \
  --target de \
  --output-dir translated_roms
```

---

## 🤖 Unterstützte LLM-Anbieter

| Anbieter | Standardmodell | API-Schlüssel | Kosten |
|----------|---------------|--------|-------|
| **DeepSeek** | deepseek-chat | `DEEPSEEK_API_KEY` | 💰 Sehr günstig |
| **OpenAI** | gpt-4o | `OPENAI_API_KEY` | 💰💰 Moderat |
| **Google Gemini** | gemini-2.0-flash | `GOOGLE_API_KEY` | 🆓 Kostenlos |
| **Claude (Anthropic)** | claude-sonnet-4 | `ANTHROPIC_API_KEY` | 💰💰 Moderat |
| **Groq** | llama-3.3-70b | `GROQ_API_KEY` | 🆓 Kostenlos |

---

## 📖 Anleitung

### CLI-Befehle

#### 1. Vollständiger Workflow (Empfohlen)

```bash
meowth full pokemon.gba \
  --provider deepseek \
  --source en \
  --target de \
  --output-dir outputs
```

#### 2. Schritt für Schritt

```bash
# Extrahieren
meowth extract pokemon.gba -o texts.json

# Übersetzen
meowth translate texts.json --provider deepseek --target de -o texts_translated.json

# Erstellen
meowth build pokemon.gba --translations texts_translated.json -o pokemon_de.gba
```

---

## 🌍 Unterstützte Sprachen

- 🇩🇪 **Deutsch** - `de`
- 🇬🇧 **Englisch** - `en`
- 🇫🇷 **Französisch** - `fr`
- 🇮🇹 **Italienisch** - `it`
- 🇪🇸 **Spanisch** - `es`
- 🇨🇳 **Chinesisch** - `zh-Hans`, `zh-Hant`
- 🇯🇵 **Japanisch** - `ja`

Und viele mehr...

---

## ⚙️ Konfiguration

### Umgebungsvariablen

```bash
export DEEPSEEK_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."
```

### Konfigurationsdatei (meowth.toml)

```toml
[translation]
provider = "deepseek"
model = "deepseek-chat"
source_language = "en"
target_language = "de"
```

---

## 🎮 Unterstützte Spiele

- Pokémon FireRed
- Pokémon LeafGreen
- Pokémon Smaragd
- Pokémon Rubin/Saphir
- Pokémon Mystery Dungeon

---

## 📄 Lizenz

MIT-Lizenz - siehe [LICENSE](LICENSE) Datei

---

**Mit ❤️ für die Pokémon-Lokalisierungscommunity erstellt**
