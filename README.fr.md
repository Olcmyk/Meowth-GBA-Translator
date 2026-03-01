# Meowth Traducteur GBA

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org)
[![Version](https://img.shields.io/badge/Version-0.3.0-green.svg)](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**Langues** | [English](./README.md) | [中文](./README.zh.md) | [Deutsch](./README.de.md) | [Italiano](./README.it.md) | [Español](./README.es.md)

🐱 Un traducteur de ROM GBA Pokémon intelligent alimenté par LLM avec interfaces GUI et CLI

</div>

---

## 📋 Aperçu

**Meowth GBA Translator** est un outil complet pour traduire les jeux Pokémon Game Boy Advance (GBA) dans différentes langues. Il combine l'extraction automatique de texte, la traduction alimentée par LLM et la construction intelligente de ROM pour rationaliser le flux de travail de traduction.

### Caractéristiques principales

- 🎮 **Interface double**: GUI conviviale et CLI puissante
- 🤖 **Traduction IA**: Support pour 11+ fournisseurs LLM
- 📦 **Multi-plateforme**: Supporté sur macOS, Windows, Linux
- 🌍 **Support multilingue**: Traduire vers n'importe quelle langue
- ⚡ **Flux de travail optimisé**: Extraire → Traduire → Construire en une commande
- 🎁 **Gratuit**: 100% open source, licence MIT
- 🔤 **Patch de police intelligente**: Injection automatique de police

### ⚠️ Important: Méthodes de traduction

> **⚠️ PATCH BINAIRE UNIQUEMENT**
>
> Cet outil ne supporte **que** la méthode de patch binaire:
> - ✅ Extraire le texte → Traduire → Réinjecter dans ROM
> - ❌ **PAS compatible avec les projets de décompilation**
> - ❌ L'injection de police est difficile dans les projets decomp
>
> Pour les ROM de décompilation, utilisez les outils spécifiques au projet.

---

## 📦 Installation

### Option 1: Application GUI (Recommandée)

Téléchargez la dernière version:

- 🍎 **macOS**: [Meowth-Translator-macOS.dmg](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)
- 🪟 **Windows**: [Meowth-Translator-Windows.zip](https://github.com/Olcmyk/Meowth-GBA-Translator/releases)

**Exigences**:
- macOS 10.13+ ou Windows 10+
- Pas d'installation requise

### Option 2: Paquet Python

```bash
# CLI uniquement
pip install meowth

# Avec support GUI
pip install meowth[gui]
```

**Exigences**:
- Python 3.10 ou supérieur

### Option 3: Depuis la source

```bash
git clone https://github.com/Olcmyk/Meowth-GBA-Translator.git
cd Meowth-GBA-Translator

python3 -m venv venv
source venv/bin/activate

pip install -e ".[gui,dev]"
meowth-gui
```

---

## 🚀 Démarrage rapide

### Utiliser l'interface GUI

1. Téléchargez et exécutez **Meowth Translator**
2. Cliquez sur "Sélectionner ROM" et choisissez votre ROM GBA Pokémon
3. Configurez les paramètres de traduction
4. Cliquez sur "Démarrer la traduction"
5. Attendez la fin du processus
6. Téléchargez la ROM traduite

### Utiliser la CLI

```bash
export DEEPSEEK_API_KEY="sk-your-key"

meowth full pokemon_firered.gba \
  --provider deepseek \
  --source en \
  --target fr \
  --output-dir translated_roms
```

---

## 🤖 Fournisseurs LLM pris en charge

| Fournisseur | Modèle par défaut | Clé API | Coût |
|-------------|-----------------|---------|------|
| **DeepSeek** | deepseek-chat | `DEEPSEEK_API_KEY` | 💰 Très bon marché |
| **OpenAI** | gpt-4o | `OPENAI_API_KEY` | 💰💰 Modéré |
| **Google Gemini** | gemini-2.0-flash | `GOOGLE_API_KEY` | 🆓 Gratuit |
| **Claude (Anthropic)** | claude-sonnet-4 | `ANTHROPIC_API_KEY` | 💰💰 Modéré |
| **Groq** | llama-3.3-70b | `GROQ_API_KEY` | 🆓 Gratuit |
| **Mistral** | mistral-large-latest | `MISTRAL_API_KEY` | 💰 Bon marché |
| **OpenRouter** | openai/gpt-4o | `OPENROUTER_API_KEY` | 💰 Variable |

---

## 📖 Guide d'utilisation

### Commandes CLI

#### 1. Pipeline complet (Recommandé)

```bash
meowth full pokemon.gba \
  --provider deepseek \
  --source en \
  --target fr \
  --output-dir outputs
```

#### 2. Étape par étape

```bash
# Extraire
meowth extract pokemon.gba -o texts.json

# Traduire
export DEEPSEEK_API_KEY="sk-your-key"
meowth translate texts.json --provider deepseek --target fr -o texts_translated.json

# Construire
meowth build pokemon.gba --translations texts_translated.json -o pokemon_fr.gba
```

---

## 🌍 Langues prises en charge

- 🇫🇷 **Français** - `fr`
- 🇬🇧 **Anglais** - `en`
- 🇩🇪 **Allemand** - `de`
- 🇮🇹 **Italien** - `it`
- 🇪🇸 **Espagnol** - `es`
- 🇨🇳 **Chinois** - `zh-Hans`, `zh-Hant`
- 🇯🇵 **Japonais** - `ja`

Et bien d'autres...

---

## ⚙️ Configuration

### Variables d'environnement

```bash
export DEEPSEEK_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."
```

### Fichier de configuration (meowth.toml)

```toml
[translation]
provider = "deepseek"
model = "deepseek-chat"
source_language = "en"
target_language = "fr"

[translation.api]
key_env = "DEEPSEEK_API_KEY"
base_url = "https://api.deepseek.com/v1"
```

---

## 🎮 Jeux pris en charge

- Pokémon FireRed
- Pokémon LeafGreen
- Pokémon Emerald
- Pokémon Ruby/Sapphire
- Pokémon Mystery Dungeon: Red Rescue Team

> **Note**: Cet outil est pour le **patch binaire uniquement**. Si votre ROM cible est une décompilation, utilisez les outils spécifiques à la décompilation.

---

## 🐛 Dépannage

### "Impossible de trouver MeowthBridge"
**Solution**: Réinstallez l'application ou reconstruisez à partir de la source

### "Clé API non trouvée"
**Solution**:
```bash
export DEEPSEEK_API_KEY="sk-your-actual-key"
```

### "La qualité de la traduction est faible"
**Solution**: Essayez un modèle plus puissant:
```bash
meowth full pokemon.gba --provider openai --model gpt-4o --target fr
```

---

## 📝 Processus de traduction

### Phase 1: Extraction
- Scanne le ROM pour le texte traduisible
- Extrait les chaînes, dialogues, noms d'objets
- Temps: ~30 secondes

### Phase 2: Traduction
- Envoie les lots de texte au LLM
- Préserve les codes spéciaux
- Temps: 5-30 minutes

### Phase 3: Construction
- Réinjecte le texte traduit dans la ROM
- Applique les correctifs de police si nécessaire
- Temps: ~1 minute

---

## 💡 Conseils pour les meilleurs résultats

1. Commencez par une ROM de test
2. Surveillez les coûts de l'API
3. Gardez les traductions simples
4. Testez toujours sur la console
5. Sauvegardez les ROM originales

---

## 📄 Licence

Licence MIT - voir le fichier [LICENSE](LICENSE)

---

## 🙏 Remerciements

Construit avec:
- [HexManiacAdvance](https://github.com/entropyus/HexManiacAdvance)
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter)
- [click](https://click.palletsprojects.com/)
- Fournisseurs LLM

---

**Créé avec ❤️ pour la communauté de localisation Pokémon**
