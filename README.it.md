# Meowth Traduttore GBA

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org)
[![Version](https://img.shields.io/badge/Version-0.3.0-green.svg)](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**Lingue** | [English](./README.md) | [中文](./README.zh.md) | [Français](./README.fr.md) | [Deutsch](./README.de.md) | [Español](./README.es.md)

Un traduttore intelligente di ROM GBA Pokémon alimentato da LLM con interfacce GUI e CLI

</div>

---

## Panoramica del Progetto

**Meowth GBA Translator** è uno strumento completo progettato per tradurre ROM Pokémon Game Boy Advance (GBA). Combina l'estrazione automatica del testo, la traduzione intelligente alimentata da LLM e la funzionalità di costruzione ROM per semplificare notevolmente il flusso di lavoro di traduzione.

### Caratteristiche Principali

- **Supporto Interfaccia Doppia**: GUI intuitiva e CLI potente
- **Traduzione IA**: Supporto per 11+ provider LLM (OpenAI, DeepSeek, Google Gemini, ecc.)
- **Multipiattaforma**: Supporto per macOS, Windows, Linux
- **Supporto Sei Lingue**: Inglese, spagnolo, francese, tedesco, italiano, cinese
- **Flusso di Lavoro Efficiente**: Estrai → Traduci → Costruisci in un comando
- **Completamente Gratuito**: 100% open source, licenza MIT
- **Libreria Font Intelligente**: Iniezione automatica di font per traduzioni in cinese


## Installazione

### Metodo 1: Applicazione GUI (Consigliato per la Maggior Parte degli Utenti)

Scarica l'ultima versione:

- **macOS**: [Meowth-Translator-macOS.dmg](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)
- **Windows**: [Meowth-Translator-Windows.zip](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**Requisiti di Sistema**:
- macOS 10.13+ o Windows 10+
- Nessuna installazione richiesta, esegui direttamente dopo il download

### Metodo 2: Pacchetto Python (Per Sviluppatori/Utenti CLI)

```bash
# Installa solo CLI
pip install meowth

# O installa con supporto GUI
pip install meowth[gui]
```

**Requisiti di Sistema**:
- Python 3.10 o superiore
- Gestore pacchetti pip

### Metodo 3: Costruisci da Sorgente

```bash
# Clona il repository
git clone https://github.com/Olcmyk/Meowth-GBA-Translator.git
cd Meowth-GBA-Translator

# Crea ambiente virtuale
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Installa in modalità sviluppo
pip install -e ".[gui,dev]"

# Esegui GUI
meowth-gui

# O usa CLI
meowth full pokemon.gba --provider deepseek
```

---

## Avvio Rapido

### Usando GUI (Più Facile)

![Screenshot GUI](https://raw.githubusercontent.com/Olcmyk/Meowth-GBA-Translator/main/images/gui-screenshot.png)

1. Scarica ed esegui **Meowth Translator**
2. Fai clic su "Seleziona ROM" e scegli la tua ROM GBA Pokémon
3. Configura le impostazioni di traduzione:
   - **Provider LLM**: Seleziona provider LLM (OpenAI, DeepSeek, ecc.)
   - **Lingua Sorgente**: Solitamente "Inglese"
   - **Lingua Destinazione**: La tua lingua desiderata
4. Fai clic su "Avvia Traduzione"
5. Attendi il completamento (tipicamente 5-30 minuti a seconda della dimensione della ROM)
6. Scarica la ROM tradotta dalla cartella di output

![Confronto Traduzione](https://raw.githubusercontent.com/Olcmyk/Meowth-GBA-Translator/main/images/translation-comparison.jpg)
*Sinistra: Gioco originale | Destra: Gioco tradotto*

### Usando CLI

#### Passaggio 1: Configura Chiave API

Per prima cosa, imposta la tua chiave API come variabile di ambiente:

```bash
# DeepSeek (Consigliato)
export DEEPSEEK_API_KEY="sk-tua-chiave"

# O altri provider
export OPENAI_API_KEY="sk-tua-chiave"
export GOOGLE_API_KEY="tua-chiave"
```

#### Passaggio 2: Esegui Traduzione

```bash
# Esegui pipeline di traduzione completa
meowth full pokemon_firered.gba \
  --provider deepseek \
  --source en \
  --target it \
  --output-dir translated_roms

# La ROM tradotta verrà salvata in: translated_roms/pokemon_firered_it.gba
```

---

## Provider LLM Supportati

| Provider | Modello Predefinito | Chiave API |
|----------|-------------------|-----------|
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

**Raccomandazione**: Consigliamo di usare **DeepSeek** poiché è stato utilizzato durante tutto lo sviluppo e i test. La traduzione di una tipica ROM GBA Pokémon costa circa 2 RMB (~$0,28 USD) con DeepSeek.

---

## Guida all'Uso

### Comandi CLI

#### 1. Pipeline Completa (Consigliato)

Completa estrazione, traduzione e costruzione in un comando:

```bash
meowth full pokemon.gba \
  --provider deepseek \
  --source en \
  --target it \
  --output-dir outputs
```

**Spiegazione Opzioni**:
- `--provider`: Provider LLM da usare
- `--source`: Codice lingua sorgente (predefinito: "en")
- `--target`: Codice lingua destinazione (predefinito: "it")
- `--output-dir`: Cartella di output (predefinito: "outputs")
- `--work-dir`: Cartella di lavoro temporanea (predefinito: "work")
- `--batch-size`: Testi per lotto di traduzione (predefinito: 30)
- `--workers`: Thread di traduzione paralleli (predefinito: 10)
- `--api-base`: Indirizzo API personalizzato (per API compatibili con OpenAI)
- `--api-key-env`: Nome variabile di ambiente per chiave API
- `--model`: Nome modello personalizzato

#### 2. Pipeline Passo dopo Passo

Per utenti avanzati che hanno bisogno di più controllo:

```bash
# Passaggio 1: Estrai testo da ROM
meowth extract pokemon.gba -o texts.json

# Passaggio 2: Traduci testo
export DEEPSEEK_API_KEY="sk-tua-chiave"
meowth translate texts.json \
  --provider deepseek \
  --target it \
  -o texts_translated.json

# Passaggio 3: Costruisci ROM tradotta
meowth build pokemon.gba \
  --translations texts_translated.json \
  -o pokemon_it.gba
```

#### 3. Usando File di Configurazione (meowth.toml)

Crea `meowth.toml` nella tua directory di lavoro:

```toml
[translation]
provider = "deepseek"
model = "deepseek-chat"
source_language = "en"
target_language = "it"

[translation.api]
key_env = "DEEPSEEK_API_KEY"
base_url = "https://api.deepseek.com/v1"
```

Quindi esegui semplicemente:
```bash
export DEEPSEEK_API_KEY="sk-tua-chiave"
meowth full pokemon.gba
```

### Funzionalità GUI

L'interfaccia GUI fornisce un'interfaccia intuitiva con:

- **Selezione ROM**: Sfoglia e seleziona la tua ROM GBA Pokémon
- **Configurazione Provider**: Facile configurazione delle chiavi API LLM
- **Impostazioni Traduzione**: Configura lingue sorgente/destinazione e parametri di traduzione
- **Tracciamento Progresso**: Aggiornamenti di progresso in tempo reale con registrazione dettagliata
- **Gestione Errori**: Messaggi di errore chiari e suggerimenti di correzione
- **Gestione Output**: Organizza e gestisci ROM tradotte

---

## Lingue Supportate

Lingue attualmente supportate:

- **Inglese** - `en`
- **Spagnolo** - `es`
- **Francese** - `fr`
- **Tedesco** - `de`
- **Italiano** - `it`
- **Cinese** - `zh-Hans`

**Importante**: La traduzione in cinese supporta solo ROM con patch binarie, non progetti di decompilazione. Altre combinazioni di lingue non hanno questa restrizione.

## Configurazione

### Variabili di Ambiente

Imposta queste nel tuo shell o file `.env`:

```bash
# Chiavi API
export DEEPSEEK_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."

# Opzionale: Indirizzo API personalizzato (per servizi compatibili con OpenAI)
export CUSTOM_API_BASE="https://api.example.com/v1"
```

### File di Configurazione (meowth.toml)

```toml
[translation]
provider = "deepseek"              # Provider LLM
model = "deepseek-chat"            # Nome modello
source_language = "en"             # Codice lingua sorgente
target_language = "it"             # Codice lingua destinazione
batch_size = 30                    # Testi per lotto
max_workers = 10                   # Worker paralleli

[translation.api]
key_env = "DEEPSEEK_API_KEY"       # Variabile di ambiente per chiave API
base_url = "https://api.deepseek.com/v1"  # URL endpoint API
```


## Uso Avanzato

### Usando Modelli Personalizzati

Usa un modello diverso con il tuo provider:

```bash
# OpenAI con GPT-4 Turbo
meowth full pokemon.gba \
  --provider openai \
  --model gpt-4-turbo \
  --target it

# Versione specifica DeepSeek
meowth full pokemon.gba \
  --provider deepseek \
  --model deepseek-chat \
  --target it
```

### Usando Endpoint API Personalizzati

Per API compatibili con OpenAI:

```bash
meowth full pokemon.gba \
  --provider openai \
  --api-base "https://api.yourservice.com/v1" \
  --api-key-env "YOUR_API_KEY" \
  --model "your-model" \
  --target it
```

### Traduzione in Batch

Traduci più ROM:

```bash
for rom in *.gba; do
  meowth full "$rom" \
    --provider deepseek \
    --target it \
    --output-dir translated/
done
```

### Ottimizzazione Prestazioni

Regola la dimensione del lotto e il numero di worker per prestazioni ottimali:

```bash
# Più veloce (più aggressivo, costo più alto)
meowth full pokemon.gba \
  --provider deepseek \
  --batch-size 50 \
  --workers 20 \
  --target it

# Più lento (più conservatore, costo più basso)
meowth full pokemon.gba \
  --provider deepseek \
  --batch-size 10 \
  --workers 5 \
  --target it
```


## Giochi Supportati

Questo strumento è stato testato con:

- Pokémon Gaia v3.2
- Pokémon SeaGlass v3.0
- Pokémon Rogue Ex v2.0.1a

Altri giochi GBA Pokémon dovrebbero funzionare, ma potrebbero richiedere regolazioni.


## Risoluzione dei Problemi

### "Impossibile trovare MeowthBridge"
- **Causa**: I file dell'applicazione sono corrotti o installati in modo incompleto
- **Soluzione**: Reinstalla l'applicazione o ricostruisci da sorgente

### "Chiave API non trovata"
- **Causa**: La variabile di ambiente della chiave API non è impostata
- **Soluzione**:
  ```bash
  export DEEPSEEK_API_KEY="sk-tua-chiave-reale"
  ```

### GUI non si avvia (macOS)
- **Causa**: Restrizioni di sicurezza macOS al primo avvio
- **Soluzione**:
  1. Vai a Impostazioni di Sistema → Privacy e Sicurezza
  2. Trova il messaggio su "Meowth Translator" bloccato
  3. Fai clic su "Apri comunque"

### "Estrazione ROM non riuscita"
- **Causa**: La ROM potrebbe essere corrotta o in formato non supportato
- **Soluzione**:
  1. Verifica che la ROM sia un file GBA valido
  2. Per traduzioni in cinese, assicurati che la ROM non sia da un progetto di decompilazione
  3. Prova prima con una ROM nota

Per ulteriore aiuto, consulta [GitHub Issues](https://github.com/Olcmyk/Meowth-GBA-Translator/issues)

---

## Spiegazione del Processo di Traduzione

### Fase 1: Estrazione (meowth extract)
- Scansiona la ROM per testo traducibile
- Estrae stringhe, dialoghi, nomi oggetti, ecc.
- Output: `texts.json`
- Tempo: ~30 secondi

### Fase 2: Traduzione (meowth translate)
- Invia lotti di testo all'LLM
- Preserva codici speciali e formattazione
- Applica ottimizzazioni specifiche della lingua
- Output: `texts_translated.json`
- Tempo: 5-30 minuti (dipende dalla dimensione della ROM e dalla velocità dell'LLM)

### Fase 3: Costruzione (meowth build)
- Reiniezione testo tradotto nella ROM
- Per cinese: Applica patch font (richiesto)
- Crea la ROM tradotta finale
- Output: `pokemon_it.gba`
- Tempo: ~1 minuto

---

## Licenza

Questo progetto è concesso in licenza secondo la Licenza MIT - consulta il file [LICENSE](LICENSE) per i dettagli

---

## Crediti

Costruito con:

- [HexManiacAdvance](https://github.com/entropyus/HexManiacAdvance) - Estrazione e iniezione ROM
- [Pokemon_GBA_Font_Patch](https://github.com/Wokann/Pokemon_GBA_Font_Patch) - Patch font cinese
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) - Framework GUI moderno
- [click](https://click.palletsprojects.com/) - Framework CLI
- [Provider LLM](https://openai.com/) - Traduzione alimentata da IA

---

## Supporto

- Trovato un bug? [Invia una Segnalazione](https://github.com/Olcmyk/Meowth-GBA-Translator/issues)
- Hai una domanda? [Avvia una Discussione](https://github.com/Olcmyk/Meowth-GBA-Translator/discussions)
- Ti piace il progetto? [Mettici una Stella su GitHub](https://github.com/Olcmyk/Meowth-GBA-Translator)

---

## Contribuire

I contributi sono benvenuti! Aree in cui puoi aiutare:

- Aggiungere supporto per più lingue
- Aggiungere supporto per tradurre ROM basate su decompilazione in cinese
- Migliorare GUI/UX
- Scrivere documentazione

---

**Fatto con ❤️ per la comunità di localizzazione Pokémon**
