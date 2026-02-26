"""DeepSeek translation with local caching."""

import hashlib
import json
import os
import threading
import time
from pathlib import Path

import httpx

from .languages import get_language_name

DEFAULT_CACHE_DIR = Path(__file__).parent.parent.parent / "work" / "cache"

# Language-specific prompt templates
PROMPT_TEMPLATES = {
    "zh-Hans": {
        "system": """你是一个专业的宝可梦游戏本地化翻译专家。请将以下宝可梦游戏的英文文本翻译成简体中文。

核心规则：
1. 控制码占位符（如 {{C0}}, {{C1}} 等）必须原样保留，不得修改、删除或增加
   - 这些是游戏的控制码（换行、翻页、颜色等），改动会导致游戏崩溃
2. 占位符的数量和顺序必须与原文完全一致
3. 使用宝可梦官方简体中文译名（皮卡丘、小火龙、妙蛙种子等）
4. POKéMON / Pokémon 翻译为"宝可梦"
5. 保持游戏对话的自然口语风格
6. 人名地名等专有名词如果有官方译名则使用官方译名，否则音译
7. 只返回翻译结果，不要任何解释或注释
8. 如果输入文本中没有任何可翻译的内容（纯符号或乱码），请原封不动地返回原文
9. 翻译时不要插入任何换行符，输出纯文本即可，系统会自动排版
10. 保留所有 \\. 等待标记的位置，它们表示游戏中的停顿效果
11. 保留段落分隔（空行），它们表示游戏中的翻页

重要：占位符代表游戏运行时会替换的变量（如玩家名、劲敌名等），翻译时不要用人名替代周围的 rival 等词。
- "rival" 一词翻译为"劲敌"，不要翻译为具体人名（如小茂）
- 例如 "your rival {{C0}}" 应翻译为 "你的劲敌{{C0}}"，而不是 "小茂{{C0}}"

重要：你必须将所有英文内容翻译成中文。不要原样返回英文文本。即使是地名、专有名词也要翻译或音译。

术语表：
{glossary}""",
        "user": """请将以下宝可梦游戏文本从英文翻译成简体中文。
每条文本用 ||| 分隔，请按相同顺序返回翻译结果，也用 ||| 分隔。
不要添加编号或额外说明，只返回翻译后的文本。

{texts}""",
    },
    "generic": {
        "system": """You are a professional Pokemon game localization expert. Translate the following Pokemon game text from {source_lang} to {target_lang}.

Core rules:
1. Control code placeholders (like {{C0}}, {{C1}}, etc.) MUST be preserved exactly - do not modify, delete, or add any
   - These are game control codes (line breaks, page breaks, colors, etc.) and changing them will crash the game
2. The number and order of placeholders must match the original text exactly
3. Use official Pokemon terminology from the glossary provided
4. Maintain the natural conversational style of game dialogue
5. For proper nouns (character names, place names), use official translations if available in the glossary, otherwise transliterate
6. Return only the translation, no explanations or notes
7. If the input contains no translatable content (pure symbols or gibberish), return it unchanged
8. Do not insert any line breaks in your translation - output plain text, the system will handle formatting
9. Preserve all \\. pause markers, they represent in-game pauses
10. Preserve paragraph breaks (blank lines), they represent page breaks in the game

Important: Placeholders represent variables that will be replaced at runtime (player name, rival name, etc.). Do not replace words like "rival" with specific names.
- For example, "your rival {{C0}}" should be translated preserving the word "rival" in {target_lang}, not replaced with a specific character name

Terminology glossary:
{glossary}""",
        "user": """Translate the following Pokemon game text from {source_lang} to {target_lang}.
Each text is separated by |||. Return translations in the same order, also separated by |||.
Do not add numbering or extra explanations, only return the translated text.

{texts}""",
    },
}


class Translator:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "deepseek-chat",
        cache_dir: Path = DEFAULT_CACHE_DIR,
        source_lang: str = "en",
        target_lang: str = "zh-Hans",
    ):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.model = model
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://api.deepseek.com/v1"
        self._cache_lock = threading.Lock()
        self.source_lang = source_lang
        self.target_lang = target_lang

        # Select appropriate prompt template
        if target_lang in PROMPT_TEMPLATES:
            self.prompts = PROMPT_TEMPLATES[target_lang]
        else:
            # Use generic template with language names
            self.prompts = {
                "system": PROMPT_TEMPLATES["generic"]["system"].replace(
                    "{source_lang}", get_language_name(source_lang)
                ).replace("{target_lang}", get_language_name(target_lang)),
                "user": PROMPT_TEMPLATES["generic"]["user"].replace(
                    "{source_lang}", get_language_name(source_lang)
                ).replace("{target_lang}", get_language_name(target_lang)),
            }

    def _cache_key(self, request_data: dict) -> str:
        content = json.dumps(request_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_cached(self, key: str) -> str | None:
        with self._cache_lock:
            resp_path = self.cache_dir / f"{key}_response.json"
            if resp_path.exists():
                data = json.loads(resp_path.read_text(encoding="utf-8"))
                return data.get("content")
            return None

    def _save_cache(self, key: str, request_data: dict, content: str):
        with self._cache_lock:
            req_path = self.cache_dir / f"{key}_request.json"
            resp_path = self.cache_dir / f"{key}_response.json"
            req_path.write_text(
                json.dumps(request_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            resp_path.write_text(
                json.dumps({"content": content}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def translate_batch(
        self, texts: list[str], glossary_context: str = ""
    ) -> list[str]:
        """Translate a batch of texts. Uses cache when available.

        Sends all texts joined by ||| in one API call.  If the LLM response
        splits into the wrong number of segments, falls back to translating
        each text individually to avoid misalignment.
        """
        joined = " ||| ".join(texts)
        system = self.prompts["system"].replace("{glossary}", glossary_context or "（无）")
        user = self.prompts["user"].replace("{texts}", joined)

        request_data = {
            "model": self.model,
            "system": system,
            "user": user,
        }

        cache_key = self._cache_key(request_data)
        cached = self._get_cached(cache_key)
        if cached is not None:
            parts = [t.strip() for t in cached.split("|||")]
            if len(parts) == len(texts):
                return parts
            # Cache had misaligned result — fall through to re-translate
            print(f"  [缓存分割不匹配 ({len(parts)} vs {len(texts)})，重新翻译]")

        # Call DeepSeek API
        content = self._call_api(system, user)

        # Split and check alignment
        parts = [t.strip() for t in content.split("|||")]
        if len(parts) == len(texts):
            # Perfect split — cache and return
            has_untranslated = any(
                self._translation_unchanged(orig, trans)
                for orig, trans in zip(texts, parts)
            )
            if not has_untranslated:
                self._save_cache(cache_key, request_data, content)
            else:
                print(f"  [部分未翻译，不缓存此批次]")
            return parts

        # Misaligned — fall back to one-by-one translation
        print(f"  [批量分割不匹配 ({len(parts)} vs {len(texts)})，逐条翻译]")
        return self._translate_individually(texts, glossary_context)

    def _call_api(self, system: str, user: str, max_retries: int = 3) -> str:
        """Send a single chat completion request and return the content."""
        for attempt in range(max_retries):
            try:
                response = httpx.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 4096,
                    },
                    timeout=120.0,
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError) as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"  [API 请求失败: {e}，{wait}秒后重试 ({attempt+1}/{max_retries})]")
                    time.sleep(wait)
                else:
                    raise

    def _translate_individually(
        self, texts: list[str], glossary_context: str = ""
    ) -> list[str]:
        """Translate texts one by one as fallback when batch splitting fails."""
        system = self.prompts["system"].replace("{glossary}", glossary_context or "（无）")
        results = []
        for text in texts:
            # Use the appropriate user prompt for single text
            if self.target_lang == "zh-Hans":
                user = f"请将以下宝可梦游戏文本从英文翻译成简体中文。\n\n{text}"
            else:
                user = f"Translate the following Pokemon game text from {get_language_name(self.source_lang)} to {get_language_name(self.target_lang)}.\n\n{text}"

            request_data = {
                "model": self.model,
                "system": system,
                "user": user,
            }
            cache_key = self._cache_key(request_data)
            cached = self._get_cached(cache_key)
            if cached is not None:
                results.append(cached)
                continue

            content = self._call_api(system, user)
            if not self._translation_unchanged(text, content):
                self._save_cache(cache_key, request_data, content)
            results.append(content)
        return results

    def _translation_unchanged(self, original: str, translated: str) -> bool:
        """Check if the API returned text essentially unchanged (not translated)."""
        orig_norm = original.strip().lower()
        trans_norm = translated.strip().lower()

        if orig_norm == trans_norm:
            return True

        # For CJK target languages, check if translation actually contains CJK characters
        from .languages import is_cjk_language
        if is_cjk_language(self.target_lang):
            # Check if the translated text still has mostly ASCII letters
            # (meaning it wasn't really translated to Chinese/Japanese/Korean)
            ascii_letters = sum(1 for c in translated if c.isascii() and c.isalpha())
            chinese_chars = sum(1 for c in translated if "\u4e00" <= c <= "\u9fff")
            total = ascii_letters + chinese_chars
            if total > 0 and ascii_letters / total > 0.8:
                return True

        # For Latin-to-Latin translations, we can't use character set detection
        # Just check if the text is exactly the same
        return False

