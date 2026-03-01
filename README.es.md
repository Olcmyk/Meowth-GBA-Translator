# Meowth Traductor GBA

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org)
[![Version](https://img.shields.io/badge/Version-0.3.0-green.svg)](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**Idiomas** | [English](./README.md) | [中文](./README.zh.md) | [Français](./README.fr.md) | [Deutsch](./README.de.md) | [Italiano](./README.it.md)

🐱 Un traductor inteligente de ROM GBA Pokémon impulsado por LLM con interfaces GUI y CLI

</div>

---

## 📋 Descripción general

**Meowth GBA Translator** es una herramienta completa para traducir juegos de Pokémon Game Boy Advance (GBA) a diferentes idiomas. Combina la extracción automática de texto, la traducción impulsada por LLM y la creación inteligente de ROM para optimizar el flujo de trabajo de traducción.

### Características principales

- 🎮 **Interfaz dual**: GUI fácil de usar y CLI potente
- 🤖 **Traducción IA**: Soporte para 11+ proveedores de LLM
- 📦 **Multiplataforma**: macOS, Windows, Linux
- 🌍 **Soporte multilingüe**: Traduce a cualquier idioma
- ⚡ **Flujo de trabajo optimizado**: Extraer → Traducir → Construir en un comando
- 🎁 **Gratuito**: 100% código abierto, licencia MIT
- 🔤 **Parche de fuente inteligente**: Inyección automática de fuentes

### ⚠️ Importante: Métodos de traducción

> **⚠️ SOLO PARCHES BINARIOS**
>
> Esta herramienta solo soporta el método de parches binarios:
> - ✅ Extraer texto → Traducir → Reinjectar en ROM
> - ❌ **NO es compatible con proyectos de descompilación**
> - ❌ La inyección de fuentes es difícil en proyectos de decomp
>
> Para ROMs descompiladas, utilice herramientas específicas del proyecto.

---

## 📦 Instalación

### Opción 1: Aplicación GUI (Recomendada)

Descargar la última versión:

- 🍎 **macOS**: [Meowth-Translator-macOS.dmg](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)
- 🪟 **Windows**: [Meowth-Translator-Windows.zip](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**Requisitos**:
- macOS 10.13+ o Windows 10+
- No se requiere instalación

### Opción 2: Paquete Python

```bash
# Solo CLI
pip install meowth

# Con soporte GUI
pip install meowth[gui]
```

**Requisitos**:
- Python 3.10 o superior

### Opción 3: Desde fuente

```bash
git clone https://github.com/Olcmyk/Meowth-GBA-Translator.git
cd Meowth-GBA-Translator

python3 -m venv venv
source venv/bin/activate

pip install -e ".[gui,dev]"
meowth-gui
```

---

## 🚀 Inicio rápido

### Usar la interfaz GUI

1. Descarga y ejecuta **Meowth Translator**
2. Haz clic en "Seleccionar ROM" y elige tu ROM GBA de Pokémon
3. Configura los parámetros de traducción
4. Haz clic en "Iniciar traducción"
5. Espera a que se complete
6. Descarga la ROM traducida

### Usar la CLI

```bash
export DEEPSEEK_API_KEY="sk-your-key"

meowth full pokemon_firered.gba \
  --provider deepseek \
  --source en \
  --target es \
  --output-dir translated_roms
```

---

## 🤖 Proveedores LLM admitidos

| Proveedor | Modelo predeterminado | Clave API | Costo |
|-----------|-------------------|---------|-------|
| **DeepSeek** | deepseek-chat | `DEEPSEEK_API_KEY` | 💰 Muy barato |
| **OpenAI** | gpt-4o | `OPENAI_API_KEY` | 💰💰 Moderado |
| **Google Gemini** | gemini-2.0-flash | `GOOGLE_API_KEY` | 🆓 Gratis |
| **Claude (Anthropic)** | claude-sonnet-4 | `ANTHROPIC_API_KEY` | 💰💰 Moderado |
| **Groq** | llama-3.3-70b | `GROQ_API_KEY` | 🆓 Gratis |

---

## 📖 Guía de uso

### Comandos CLI

#### 1. Flujo de trabajo completo (Recomendado)

```bash
meowth full pokemon.gba \
  --provider deepseek \
  --source en \
  --target es \
  --output-dir outputs
```

#### 2. Paso a paso

```bash
# Extraer
meowth extract pokemon.gba -o texts.json

# Traducir
meowth translate texts.json --provider deepseek --target es -o texts_translated.json

# Construir
meowth build pokemon.gba --translations texts_translated.json -o pokemon_es.gba
```

---

## 🌍 Idiomas admitidos

- 🇪🇸 **Español** - `es`
- 🇬🇧 **Inglés** - `en`
- 🇫🇷 **Francés** - `fr`
- 🇩🇪 **Alemán** - `de`
- 🇮🇹 **Italiano** - `it`
- 🇨🇳 **Chino** - `zh-Hans`, `zh-Hant`
- 🇯🇵 **Japonés** - `ja`

Y muchos más...

---

## ⚙️ Configuración

### Variables de entorno

```bash
export DEEPSEEK_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."
```

### Archivo de configuración (meowth.toml)

```toml
[translation]
provider = "deepseek"
model = "deepseek-chat"
source_language = "en"
target_language = "es"
```

---

## 🎮 Juegos compatibles

- Pokémon FireRed
- Pokémon LeafGreen
- Pokémon Esmeralda
- Pokémon Rojo/Zafiro
- Pokémon Mystery Dungeon

---

## 📄 Licencia

Licencia MIT - ver archivo [LICENSE](LICENSE)

---

**Hecho con ❤️ para la comunidad de localización de Pokémon**
