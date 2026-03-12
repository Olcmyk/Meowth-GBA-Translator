# Meowth Traductor GBA

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org)
[![Version](https://img.shields.io/badge/Version-0.3.0-green.svg)](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**Idiomas** | [English](./README.md) | [中文](./README.zh.md) | [Français](./README.fr.md) | [Deutsch](./README.de.md) | [Italiano](./README.it.md)

Un traductor inteligente de ROM GBA Pokémon impulsado por LLM con interfaces GUI y CLI

</div>

---

## Descripción General

**Meowth GBA Translator** es una herramienta completa diseñada para traducir ROMs de Pokémon Game Boy Advance (GBA). Combina extracción automática de texto, traducción inteligente impulsada por LLM y funcionalidad de construcción de ROM para simplificar enormemente el flujo de trabajo de traducción.

### Características Principales

- **Soporte de Interfaz Dual**: GUI fácil de usar y CLI potente
- **Traducción IA**: Soporte para 11+ proveedores de LLM (OpenAI, DeepSeek, Google Gemini, etc.)
- **Multiplataforma**: Soporte para macOS, Windows, Linux
- **Soporte de Seis Idiomas**: Inglés, español, francés, alemán, italiano, chino
- **Flujo de Trabajo Eficiente**: Extraer → Traducir → Construir en un comando
- **Completamente Gratuito**: 100% código abierto, licencia MIT
- **Biblioteca de Fuentes Inteligente**: Inyección automática de fuentes para traducciones al chino


## Instalación

### Método 1: Aplicación GUI (Recomendado para la Mayoría de Usuarios)

Descargue la última versión:

- **macOS**: [Meowth-Translator-macOS.dmg](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)
- **Windows**: [Meowth-Translator-Windows.zip](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**Requisitos del Sistema**:
- macOS 10.13+ o Windows 10+
- No se requiere instalación, ejecute directamente después de descargar

### Método 2: Paquete Python (Para Desarrolladores/Usuarios de CLI)

```bash
# Instalar solo CLI
pip install meowth

# O instalar con soporte GUI
pip install meowth[gui]
```

**Requisitos del Sistema**:
- Python 3.10 o superior
- Gestor de paquetes pip

### Método 3: Construir desde la Fuente

```bash
# Clonar repositorio
git clone https://github.com/Olcmyk/Meowth-GBA-Translator.git
cd Meowth-GBA-Translator

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar en modo desarrollo
pip install -e ".[gui,dev]"

# Ejecutar GUI
meowth-gui

# O usar CLI
meowth full pokemon.gba --provider deepseek
```

---

## Inicio Rápido

### Usando GUI (Lo Más Fácil)

![Captura de Pantalla de GUI](https://raw.githubusercontent.com/Olcmyk/Meowth-GBA-Translator/main/images/gui-screenshot.png)

1. Descargue y ejecute **Meowth Translator**
2. Haga clic en "Seleccionar ROM" y elija su ROM GBA de Pokémon
3. Configure los parámetros de traducción:
   - **Proveedor de LLM**: Seleccione proveedor de LLM (OpenAI, DeepSeek, etc.)
   - **Idioma de Origen**: Generalmente "Inglés"
   - **Idioma de Destino**: Su idioma deseado
4. Haga clic en "Iniciar Traducción"
5. Espere a que se complete (típicamente 5-30 minutos dependiendo del tamaño de la ROM)
6. Descargue la ROM traducida de la carpeta de salida

![Comparación de Traducción](https://raw.githubusercontent.com/Olcmyk/Meowth-GBA-Translator/main/images/translation-comparison.jpg)
*Izquierda: Juego original | Derecha: Juego traducido*

### Usando CLI

#### Paso 1: Configurar Clave API

Primero, establezca su clave API como variable de entorno:

```bash
# DeepSeek (Recomendado)
export DEEPSEEK_API_KEY="sk-su-clave"

# U otros proveedores
export OPENAI_API_KEY="sk-su-clave"
export GOOGLE_API_KEY="su-clave"
```

#### Paso 2: Ejecutar Traducción

```bash
# Ejecutar pipeline completo de traducción
meowth full pokemon_firered.gba \
  --provider deepseek \
  --source en \
  --target es \
  --output-dir translated_roms

# La ROM traducida se guardará en: translated_roms/pokemon_firered_es.gba
```

---

## Proveedores LLM Soportados

| Proveedor | Modelo Predeterminado | Clave API |
|-----------|----------------------|-----------|
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

**Recomendación**: Recomendamos usar **DeepSeek** ya que se utilizó durante todo el desarrollo y pruebas. Traducir una ROM típica de Pokémon GBA cuesta aproximadamente 2 RMB (~$0.28 USD) con DeepSeek.

---

## Guía de Uso

### Comandos CLI

#### 1. Pipeline Completo (Recomendado)

Complete la extracción, traducción y construcción en un comando:

```bash
meowth full pokemon.gba \
  --provider deepseek \
  --source en \
  --target es \
  --output-dir outputs
```

**Explicación de Opciones**:
- `--provider`: Proveedor de LLM a usar
- `--source`: Código de idioma de origen (predeterminado: "en")
- `--target`: Código de idioma de destino (predeterminado: "es")
- `--output-dir`: Carpeta de salida (predeterminado: "outputs")
- `--work-dir`: Carpeta de trabajo temporal (predeterminado: "work")
- `--batch-size`: Textos por lote de traducción (predeterminado: 30)
- `--workers`: Hilos de traducción paralelos (predeterminado: 10)
- `--api-base`: Dirección API personalizada (para APIs compatibles con OpenAI)
- `--api-key-env`: Nombre de variable de entorno para clave API
- `--model`: Nombre de modelo personalizado

#### 2. Pipeline Paso a Paso

Para usuarios avanzados que necesitan más control:

```bash
# Paso 1: Extraer texto de ROM
meowth extract pokemon.gba -o texts.json

# Paso 2: Traducir texto
export DEEPSEEK_API_KEY="sk-su-clave"
meowth translate texts.json \
  --provider deepseek \
  --target es \
  -o texts_translated.json

# Paso 3: Construir ROM traducida
meowth build pokemon.gba \
  --translations texts_translated.json \
  -o pokemon_es.gba
```

#### 3. Usando Archivo de Configuración (meowth.toml)

Cree `meowth.toml` en su directorio de trabajo:

```toml
[translation]
provider = "deepseek"
model = "deepseek-chat"
source_language = "en"
target_language = "es"

[translation.api]
key_env = "DEEPSEEK_API_KEY"
base_url = "https://api.deepseek.com/v1"
```

Luego simplemente ejecute:
```bash
export DEEPSEEK_API_KEY="sk-su-clave"
meowth full pokemon.gba
```

### Características de GUI

La GUI proporciona una interfaz fácil de usar con:

- **Selección de ROM**: Explore y seleccione su ROM GBA de Pokémon
- **Configuración de Proveedor**: Configuración fácil de claves API de LLM
- **Parámetros de Traducción**: Configure idiomas de origen/destino y parámetros de traducción
- **Seguimiento de Progreso**: Actualizaciones de progreso en tiempo real con registro detallado
- **Manejo de Errores**: Mensajes de error claros y sugerencias de corrección
- **Gestión de Salida**: Organice y gestione ROMs traducidas

---

## Idiomas Soportados

Idiomas actualmente soportados:

- **Inglés** - `en`
- **Español** - `es`
- **Francés** - `fr`
- **Alemán** - `de`
- **Italiano** - `it`
- **Chino** - `zh-Hans`

**Importante**: La traducción al chino solo soporta ROMs con parches binarios, no proyectos de descompilación. Otras combinaciones de idiomas no tienen esta restricción.

## Configuración

### Variables de Entorno

Establezca estas en su shell o archivo `.env`:

```bash
# Claves API
export DEEPSEEK_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."

# Opcional: Dirección API personalizada (para servicios compatibles con OpenAI)
export CUSTOM_API_BASE="https://api.example.com/v1"
```

### Archivo de Configuración (meowth.toml)

```toml
[translation]
provider = "deepseek"              # Proveedor de LLM
model = "deepseek-chat"            # Nombre del modelo
source_language = "en"             # Código de idioma de origen
target_language = "es"             # Código de idioma de destino
batch_size = 30                    # Textos por lote
max_workers = 10                   # Trabajadores paralelos

[translation.api]
key_env = "DEEPSEEK_API_KEY"       # Variable de entorno para clave API
base_url = "https://api.deepseek.com/v1"  # URL de punto final de API
```


## Uso Avanzado

### Usando Modelos Personalizados

Use un modelo diferente con su proveedor:

```bash
# OpenAI con GPT-4 Turbo
meowth full pokemon.gba \
  --provider openai \
  --model gpt-4-turbo \
  --target es

# Versión específica de DeepSeek
meowth full pokemon.gba \
  --provider deepseek \
  --model deepseek-chat \
  --target es
```

### Usando Puntos Finales de API Personalizados

Para APIs compatibles con OpenAI:

```bash
meowth full pokemon.gba \
  --provider openai \
  --api-base "https://api.yourservice.com/v1" \
  --api-key-env "YOUR_API_KEY" \
  --model "your-model" \
  --target es
```

### Traducción por Lotes

Traduzca múltiples ROMs:

```bash
for rom in *.gba; do
  meowth full "$rom" \
    --provider deepseek \
    --target es \
    --output-dir translated/
done
```

### Ajuste de Rendimiento

Ajuste el tamaño del lote y el número de trabajadores para un rendimiento óptimo:

```bash
# Más rápido (más agresivo, costo más alto)
meowth full pokemon.gba \
  --provider deepseek \
  --batch-size 50 \
  --workers 20 \
  --target es

# Más lento (más conservador, costo más bajo)
meowth full pokemon.gba \
  --provider deepseek \
  --batch-size 10 \
  --workers 5 \
  --target es
```


## Juegos Soportados

Esta herramienta ha sido probada con:

- Pokémon Gaia v3.2
- Pokémon SeaGlass v3.0
- Pokémon Rogue Ex v2.0.1a

Otros juegos GBA de Pokémon también deberían funcionar, pero pueden requerir ajustes.


## Solución de Problemas

### "No se puede encontrar MeowthBridge"
- **Causa**: Los archivos de la aplicación están dañados o instalados incompletamente
- **Solución**: Reinstale la aplicación o reconstruya desde la fuente

### "Clave API no encontrada"
- **Causa**: La variable de entorno de clave API no está establecida
- **Solución**:
  ```bash
  export DEEPSEEK_API_KEY="sk-su-clave-real"
  ```

### GUI no se inicia (macOS)
- **Causa**: Restricciones de seguridad de macOS en la primera ejecución
- **Solución**:
  1. Vaya a Configuración del Sistema → Privacidad y Seguridad
  2. Encuentre el mensaje sobre "Meowth Translator" siendo bloqueado
  3. Haga clic en "Abrir de Todas Formas"

### "Extracción de ROM fallida"
- **Causa**: La ROM podría estar dañada o en formato no compatible
- **Solución**:
  1. Verifique que la ROM sea un archivo GBA válido
  2. Para traducciones al chino, asegúrese de que la ROM no sea de un proyecto de descompilación
  3. Intente primero con una ROM conocida

Para más ayuda, consulte [GitHub Issues](https://github.com/Olcmyk/Meowth-GBA-Translator/issues)

---

## Explicación del Proceso de Traducción

### Fase 1: Extracción (meowth extract)
- Escanea la ROM en busca de texto traducible
- Extrae cadenas, diálogos, nombres de objetos, etc.
- Salida: `texts.json`
- Tiempo: ~30 segundos

### Fase 2: Traducción (meowth translate)
- Envía lotes de texto al LLM
- Preserva códigos especiales y formato
- Aplica optimizaciones específicas del idioma
- Salida: `texts_translated.json`
- Tiempo: 5-30 minutos (depende del tamaño de la ROM y velocidad del LLM)

### Fase 3: Construcción (meowth build)
- Inyecta texto traducido de vuelta en la ROM
- Para chino: Aplica parches de fuentes (requerido)
- Crea la ROM traducida final
- Salida: `pokemon_es.gba`
- Tiempo: ~1 minuto

---

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - consulte el archivo [LICENSE](LICENSE) para más detalles

---

## Créditos

Construido con:

- [HexManiacAdvance](https://github.com/entropyus/HexManiacAdvance) - Extracción e inyección de ROM
- [Pokemon_GBA_Font_Patch](https://github.com/Wokann/Pokemon_GBA_Font_Patch) - Parche de fuente chino
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) - Marco GUI moderno
- [click](https://click.palletsprojects.com/) - Marco CLI
- [Proveedores LLM](https://openai.com/) - Traducción impulsada por IA

---

## Soporte

- ¿Encontró un error? [Envíe un Problema](https://github.com/Olcmyk/Meowth-GBA-Translator/issues)
- ¿Tiene una pregunta? [Inicie una Discusión](https://github.com/Olcmyk/Meowth-GBA-Translator/discussions)
- ¿Le gusta el proyecto? [Denos una Estrella en GitHub](https://github.com/Olcmyk/Meowth-GBA-Translator)

---

## Contribuyendo

¡Las contribuciones son bienvenidas! Áreas en las que puede ayudar:

- Agregar soporte para más idiomas
- Agregar soporte para traducir ROMs basadas en descompilación al chino
- Mejorar GUI/UX
- Escribir documentación

---

**Hecho con ❤️ para la comunidad de localización de Pokémon**
