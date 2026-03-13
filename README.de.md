# Meowth GBA Übersetzer

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org)
[![Version](https://img.shields.io/badge/Version-0.3.3-green.svg)](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**Sprachen** | [English](./README.md) | [中文](./README.zh.md) | [Français](./README.fr.md) | [Italiano](./README.it.md) | [Español](./README.es.md)

Ein intelligenter GBA Pokémon ROM-Übersetzer mit LLM-Antrieb mit GUI und CLI-Schnittstellen

</div>

---

## Projektübersicht

**Meowth GBA Translator** ist ein umfassendes Tool zum Übersetzen von Pokémon Game Boy Advance (GBA) ROMs. Es kombiniert automatische Textextraktion, intelligente LLM-gestützte Übersetzung und ROM-Erstellungsfunktionalität, um den Übersetzungsworkflow erheblich zu vereinfachen.

### Hauptmerkmale

- **Duale Schnittstellenunterstützung**: Benutzerfreundliche GUI und leistungsstarke CLI
- **KI-Übersetzung**: Unterstützung für 11+ LLM-Anbieter (OpenAI, DeepSeek, Google Gemini, etc.)
- **Plattformübergreifend**: Unterstützung für macOS, Windows, Linux
- **Unterstützung für Sechs Sprachen**: Englisch, Spanisch, Französisch, Deutsch, Italienisch, Chinesisch
- **Optimierter Workflow**: Extrahieren → Übersetzen → Erstellen in einem Befehl
- **Vollständig Kostenlos**: 100% Open Source, MIT-Lizenz
- **Intelligente Schriftartenbibliothek**: Automatische Schrifteinspritzung für chinesische Übersetzungen


## Installation

### Methode 1: GUI-Anwendung (Empfohlen für die Meisten Benutzer)

Laden Sie die neueste Version herunter:

- **macOS**: [Meowth-Translator-macOS.dmg](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)
- **Windows**: [Meowth-Translator-Windows.zip](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**Systemanforderungen**:
- macOS 10.13+ oder Windows 10+
- Keine Installation erforderlich, direkt nach dem Download ausführen

### Methode 2: Python-Paket (Für Entwickler/CLI-Benutzer)

```bash
# Nur CLI installieren
pip install meowth

# Oder mit GUI-Unterstützung installieren
pip install meowth[gui]
```

**Systemanforderungen**:
- Python 3.10 oder höher
- pip-Paketmanager

### Methode 3: Aus Quellcode Erstellen

```bash
# Repository klonen
git clone https://github.com/Olcmyk/Meowth-GBA-Translator.git
cd Meowth-GBA-Translator

# Virtuelle Umgebung erstellen
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Im Entwicklungsmodus installieren
pip install -e ".[gui,dev]"

# GUI ausführen
meowth-gui

# Oder CLI verwenden
meowth full pokemon.gba --provider deepseek
```

---

## Schnelleinstieg

### GUI Verwenden (Am Einfachsten)

![GUI-Screenshot](https://raw.githubusercontent.com/Olcmyk/Meowth-GBA-Translator/main/images/gui-screenshot.png)

1. Laden Sie **Meowth Translator** herunter und starten Sie es
2. Klicken Sie auf "ROM auswählen" und wählen Sie Ihre GBA Pokémon ROM
3. Konfigurieren Sie die Übersetzungseinstellungen:
   - **LLM-Anbieter**: Wählen Sie LLM-Anbieter (OpenAI, DeepSeek, etc.)
   - **Quellsprache**: Normalerweise "Englisch"
   - **Zielsprache**: Ihre gewünschte Sprache
4. Klicken Sie auf "Übersetzung starten"
5. Warten Sie auf den Abschluss (normalerweise 5-30 Minuten je nach ROM-Größe)
6. Laden Sie die übersetzte ROM aus dem Ausgabeordner herunter

![Übersetzungsvergleich](https://raw.githubusercontent.com/Olcmyk/Meowth-GBA-Translator/main/images/translation-comparison.jpg)
*Links: Originalspiel | Rechts: Übersetztes Spiel*

### CLI Verwenden

#### Schritt 1: API-Schlüssel Konfigurieren

Legen Sie zunächst Ihren API-Schlüssel als Umgebungsvariable fest:

```bash
# DeepSeek (Empfohlen)
export DEEPSEEK_API_KEY="sk-ihr-schlüssel"

# Oder andere Anbieter
export OPENAI_API_KEY="sk-ihr-schlüssel"
export GOOGLE_API_KEY="ihr-schlüssel"
```

#### Schritt 2: Übersetzung Ausführen

```bash
# Führen Sie die vollständige Übersetzungs-Pipeline aus
meowth full pokemon_firered.gba \
  --provider deepseek \
  --source en \
  --target de \
  --output-dir translated_roms

# Die übersetzte ROM wird gespeichert in: translated_roms/pokemon_firered_de.gba
```

---

## Unterstützte LLM-Anbieter

| Anbieter | Standardmodell | API-Schlüssel |
|----------|----------------|---------------|
| **DeepSeek** | deepseek-chat | `DEEPSEEK_API_KEY` |
| **OpenAI** | gpt-4o | `OPENAI_API_KEY` |
| **Google Gemini** | gemini-2.0-flash | `GOOGLE_API_KEY` |
| **Claude (Anthropic)** | claude-sonnet-4 | `ANTHROPIC_API_KEY` |
| **Groq** | llama-3.3-70b | `GROQ_API_KEY` |
| **Mistral** | mistral-large-latest | `MISTRAL_API_KEY` |
| **OpenRouter** | openai/gpt-4o | `OPENROUTER_API_KEY` |
| **SiliconFlow** | DeepSeek-V3 | `SILICONFLOW_API_KEY` |
| **Zhipu GLM** | glm-4-flash | `ZHIPU_API_KEY` |
| **Moonshot** | moonshot-v1-8k | `MOONSHOT_API_KEY` |
| **Qwen** | qwen-plus | `DASHSCOPE_API_KEY` |

**Empfehlung**: Wir empfehlen die Verwendung von **DeepSeek**, da es während der gesamten Entwicklung und des Testens verwendet wurde. Die Übersetzung einer typischen Pokémon GBA ROM kostet etwa 2 RMB (~0,28 USD) mit DeepSeek.

---

## Verwendungsanleitung

### CLI-Befehle

#### 1. Vollständige Pipeline (Empfohlen)

Führen Sie Extraktion, Übersetzung und Erstellung in einem Befehl durch:

```bash
meowth full pokemon.gba \
  --provider deepseek \
  --source en \
  --target de \
  --output-dir outputs
```

**Optionserklärung**:
- `--provider`: Zu verwendender LLM-Anbieter
- `--source`: Quellsprachcode (Standard: "en")
- `--target`: Zielsprachcode (Standard: "de")
- `--output-dir`: Ausgabeordner (Standard: "outputs")
- `--work-dir`: Temporärer Arbeitsordner (Standard: "work")
- `--batch-size`: Texte pro Übersetzungsstapel (Standard: 30)
- `--workers`: Parallele Übersetzungs-Threads (Standard: 10)
- `--api-base`: Benutzerdefinierte API-Adresse (für OpenAI-kompatible APIs)
- `--api-key-env`: Umgebungsvariablenname für API-Schlüssel
- `--model`: Benutzerdefinierter Modellname

#### 2. Schritt-für-Schritt-Pipeline

Für fortgeschrittene Benutzer, die mehr Kontrolle benötigen:

```bash
# Schritt 1: Text aus ROM extrahieren
meowth extract pokemon.gba -o texts.json

# Schritt 2: Text übersetzen
export DEEPSEEK_API_KEY="sk-ihr-schlüssel"
meowth translate texts.json \
  --provider deepseek \
  --target de \
  -o texts_translated.json

# Schritt 3: Übersetzte ROM erstellen
meowth build pokemon.gba \
  --translations texts_translated.json \
  -o pokemon_de.gba
```

#### 3. Konfigurationsdatei Verwenden (meowth.toml)

Erstellen Sie `meowth.toml` in Ihrem Arbeitsverzeichnis:

```toml
[translation]
provider = "deepseek"
model = "deepseek-chat"
source_language = "en"
target_language = "de"

[translation.api]
key_env = "DEEPSEEK_API_KEY"
base_url = "https://api.deepseek.com/v1"
```

Führen Sie dann einfach aus:
```bash
export DEEPSEEK_API_KEY="sk-ihr-schlüssel"
meowth full pokemon.gba
```

### GUI-Funktionen

Die GUI bietet eine benutzerfreundliche Schnittstelle mit:

- **ROM-Auswahl**: Durchsuchen und wählen Sie Ihre GBA Pokémon ROM
- **Anbieter-Konfiguration**: Einfache Einrichtung von LLM-API-Schlüsseln
- **Übersetzungseinstellungen**: Konfigurieren Sie Quell-/Zielsprachen und Übersetzungsparameter
- **Fortschrittsverfolgung**: Echtzeit-Fortschrittsaktualisierungen mit detaillierter Protokollierung
- **Fehlerbehandlung**: Klare Fehlermeldungen und Korrekturvorschläge
- **Ausgabeverwaltung**: Organisieren und verwalten Sie übersetzte ROMs

---

## Unterstützte Sprachen

Derzeit unterstützte Sprachen:

- **Englisch** - `en`
- **Spanisch** - `es`
- **Französisch** - `fr`
- **Deutsch** - `de`
- **Italienisch** - `it`
- **Chinesisch** - `zh-Hans`

**Wichtig**: Chinesische Übersetzung unterstützt nur binär gepatschte ROMs, keine Decompilation-Projekte. Andere Sprachkombinationen haben diese Einschränkung nicht.

## Konfiguration

### Umgebungsvariablen

Legen Sie diese in Ihrer Shell oder `.env`-Datei fest:

```bash
# API-Schlüssel
export DEEPSEEK_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."

# Optional: Benutzerdefinierte API-Adresse (für OpenAI-kompatible Dienste)
export CUSTOM_API_BASE="https://api.example.com/v1"
```

### Konfigurationsdatei (meowth.toml)

```toml
[translation]
provider = "deepseek"              # LLM-Anbieter
model = "deepseek-chat"            # Modellname
source_language = "en"             # Quellsprachcode
target_language = "de"             # Zielsprachcode
batch_size = 30                    # Texte pro Stapel
max_workers = 10                   # Parallele Worker

[translation.api]
key_env = "DEEPSEEK_API_KEY"       # Umgebungsvariable für API-Schlüssel
base_url = "https://api.deepseek.com/v1"  # API-Endpunkt-URL
```


## Erweiterte Verwendung

### Benutzerdefinierte Modelle Verwenden

Verwenden Sie ein anderes Modell mit Ihrem Anbieter:

```bash
# OpenAI mit GPT-4 Turbo
meowth full pokemon.gba \
  --provider openai \
  --model gpt-4-turbo \
  --target de

# DeepSeek spezifische Version
meowth full pokemon.gba \
  --provider deepseek \
  --model deepseek-chat \
  --target de
```

### Benutzerdefinierte API-Endpunkte Verwenden

Für OpenAI-kompatible APIs:

```bash
meowth full pokemon.gba \
  --provider openai \
  --api-base "https://api.yourservice.com/v1" \
  --api-key-env "YOUR_API_KEY" \
  --model "your-model" \
  --target de
```

### Batch-Übersetzung

Übersetzen Sie mehrere ROMs:

```bash
for rom in *.gba; do
  meowth full "$rom" \
    --provider deepseek \
    --target de \
    --output-dir translated/
done
```

### Leistungsoptimierung

Passen Sie die Stapelgröße und die Anzahl der Worker für optimale Leistung an:

```bash
# Schneller (aggressiver, höhere Kosten)
meowth full pokemon.gba \
  --provider deepseek \
  --batch-size 50 \
  --workers 20 \
  --target de

# Langsamer (konservativer, niedrigere Kosten)
meowth full pokemon.gba \
  --provider deepseek \
  --batch-size 10 \
  --workers 5 \
  --target de
```


## Unterstützte Spiele

Dieses Tool wurde getestet mit:

- Pokémon Gaia v3.2
- Pokémon SeaGlass v3.0
- Pokémon Rogue Ex v2.0.1a

Andere GBA Pokémon-Spiele sollten auch funktionieren, benötigen aber möglicherweise Anpassungen.


## Fehlerbehebung

### "MeowthBridge nicht gefunden"
- **Ursache**: Anwendungsdateien sind beschädigt oder unvollständig installiert
- **Lösung**: Installieren Sie die Anwendung neu oder erstellen Sie sie aus dem Quellcode neu

### "API-Schlüssel nicht gefunden"
- **Ursache**: Umgebungsvariable für API-Schlüssel ist nicht gesetzt
- **Lösung**:
  ```bash
  export DEEPSEEK_API_KEY="sk-ihr-echter-schlüssel"
  ```

### GUI startet nicht (macOS)
- **Ursache**: macOS-Sicherheitseinschränkungen beim ersten Start
- **Lösung**:
  1. Gehen Sie zu Systemeinstellungen → Datenschutz und Sicherheit
  2. Finden Sie die Meldung über "Meowth Translator" blockiert
  3. Klicken Sie auf "Trotzdem öffnen"

### "ROM-Extraktion fehlgeschlagen"
- **Ursache**: ROM könnte beschädigt oder in nicht unterstütztem Format sein
- **Lösung**:
  1. Überprüfen Sie, dass die ROM eine gültige GBA-Datei ist
  2. Für chinesische Übersetzungen stellen Sie sicher, dass die ROM nicht aus einem Decompilation-Projekt stammt
  3. Testen Sie zuerst mit einer bekannten ROM

Weitere Hilfe finden Sie unter [GitHub Issues](https://github.com/Olcmyk/Meowth-GBA-Translator/issues)

---

## Erklärung des Übersetzungsprozesses

### Phase 1: Extraktion (meowth extract)
- Scannt die ROM nach übersetzbarem Text
- Extrahiert Strings, Dialoge, Objektnamen, etc.
- Ausgabe: `texts.json`
- Zeit: ~30 Sekunden

### Phase 2: Übersetzung (meowth translate)
- Sendet Textblöcke an das LLM
- Behält spezielle Codes und Formatierung bei
- Wendet sprachspezifische Optimierungen an
- Ausgabe: `texts_translated.json`
- Zeit: 5-30 Minuten (hängt von ROM-Größe und LLM-Geschwindigkeit ab)

### Phase 3: Erstellung (meowth build)
- Injiziert übersetzten Text zurück in die ROM
- Für Chinesisch: Wendet Schriftarten-Patches an (erforderlich)
- Erstellt die endgültige übersetzte ROM
- Ausgabe: `pokemon_de.gba`
- Zeit: ~1 Minute

---

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe die [LICENSE](LICENSE)-Datei für Details

---

## Danksagungen

Erstellt mit:

- [HexManiacAdvance](https://github.com/entropyus/HexManiacAdvance) - ROM-Extraktion und -Injektion
- [Pokemon_GBA_Font_Patch](https://github.com/Wokann/Pokemon_GBA_Font_Patch) - Chinesischer Schriftarten-Patch
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) - Modernes GUI-Framework
- [click](https://click.palletsprojects.com/) - CLI-Framework
- [LLM-Anbieter](https://openai.com/) - KI-gestützte Übersetzung

---

## Unterstützung

- Fehler gefunden? [Problem einreichen](https://github.com/Olcmyk/Meowth-GBA-Translator/issues)
- Frage? [Diskussion starten](https://github.com/Olcmyk/Meowth-GBA-Translator/discussions)
- Gefällt Ihnen das Projekt? [Geben Sie uns einen Stern auf GitHub](https://github.com/Olcmyk/Meowth-GBA-Translator)

---

## Beitragen

Beiträge sind willkommen! Bereiche, in denen Sie helfen können:

- Unterstützung für mehr Sprachen hinzufügen
- Unterstützung für die Übersetzung von Decompilation-basierten ROMs ins Chinesische hinzufügen
- GUI/UX verbessern
- Dokumentation schreiben

---

**Mit ❤️ für die Pokémon-Lokalisierungscommunity erstellt**
