"""DeepSeek translation with local caching."""

import hashlib
import json
import os
import re
import threading
from pathlib import Path

import httpx

DEFAULT_CACHE_DIR = Path(__file__).parent.parent.parent / "work" / "cache"

SYSTEM_PROMPT = """你是一个专业的宝可梦游戏本地化翻译专家。请将以下宝可梦游戏的英文文本翻译成简体中文。

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
9. 翻译时不需要考虑换行，系统会自动排版
10. 保留所有 \\. 等待标记的位置，它们表示游戏中的停顿效果
11. 保留段落分隔（空行），它们表示游戏中的翻页

重要：占位符代表游戏运行时会替换的变量（如玩家名、劲敌名等），翻译时不要用人名替代周围的 rival 等词。
- "rival" 一词翻译为"劲敌"，不要翻译为具体人名（如小茂）
- 例如 "your rival {{C0}}" 应翻译为 "你的劲敌{{C0}}"，而不是 "小茂{{C0}}"

重要：你必须将所有英文内容翻译成中文。不要原样返回英文文本。即使是地名、专有名词也要翻译或音译。

术语表：
{glossary}"""

USER_PROMPT = """请将以下宝可梦游戏文本从英文翻译成简体中文。
每条文本用 ||| 分隔，请按相同顺序返回翻译结果，也用 ||| 分隔。
不要添加编号或额外说明，只返回翻译后的文本。

{texts}"""


class Translator:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "deepseek-chat",
        cache_dir: Path = DEFAULT_CACHE_DIR,
    ):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.model = model
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://api.deepseek.com/v1"
        self._cache_lock = threading.Lock()

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
        """Translate a batch of texts. Uses cache when available."""
        joined = " ||| ".join(texts)
        system = SYSTEM_PROMPT.replace("{glossary}", glossary_context or "（无）")
        user = USER_PROMPT.replace("{texts}", joined)

        request_data = {
            "model": self.model,
            "system": system,
            "user": user,
        }

        cache_key = self._cache_key(request_data)
        cached = self._get_cached(cache_key)
        if cached is not None:
            results = self._split_results(cached, len(texts), texts)
            return results

        # Call DeepSeek API
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
        content = response.json()["choices"][0]["message"]["content"]

        # Only cache if the result actually contains translations
        results = self._split_results(content, len(texts), texts)
        has_untranslated = any(
            self._translation_unchanged(orig, trans)
            for orig, trans in zip(texts, results)
        )
        if not has_untranslated:
            self._save_cache(cache_key, request_data, content)
        else:
            print(f"  [部分未翻译，不缓存此批次]")

        return results

    @staticmethod
    def _translation_unchanged(original: str, translated: str) -> bool:
        """Check if the API returned text essentially unchanged (not translated)."""
        orig_norm = original.strip().lower()
        trans_norm = translated.strip().lower()

        if orig_norm == trans_norm:
            return True

        # Check if the translated text still has mostly ASCII letters
        # (meaning it wasn't really translated to Chinese)
        ascii_letters = sum(1 for c in translated if c.isascii() and c.isalpha())
        chinese_chars = sum(1 for c in translated if "\u4e00" <= c <= "\u9fff")
        total = ascii_letters + chinese_chars
        if total > 0 and ascii_letters / total > 0.8:
            return True

        return False

    @staticmethod
    def _split_results(
        content: str, expected: int, originals: list[str]
    ) -> list[str]:
        """Split LLM response by ||| and align with expected count.

        If the LLM produced more segments than expected (e.g. a translation
        contained |||), try to merge excess segments back together.
        """
        parts = [t.strip() for t in content.split("|||")]

        if len(parts) == expected:
            return parts

        if len(parts) > expected:
            # Too many splits — merge excess segments back.
            # Strategy: greedily assign segments to each expected slot,
            # merging adjacent segments when we have too many.
            merged: list[str] = []
            extra = len(parts) - expected
            i = 0
            for slot in range(expected):
                merged.append(parts[i])
                i += 1
                # Distribute extra segments to earlier slots
                if extra > 0 and slot < expected - 1:
                    # Check if next part looks like a continuation
                    # (doesn't start with a CJK char or capital letter)
                    while extra > 0 and i < len(parts):
                        next_part = parts[i]
                        if next_part and (
                            next_part[0].islower()
                            or not next_part[0].isalpha()
                        ):
                            merged[-1] += "|||" + next_part
                            i += 1
                            extra -= 1
                        else:
                            break
            # Append any remaining
            while i < len(parts):
                if len(merged) < expected:
                    merged.append(parts[i])
                else:
                    merged[-1] += "|||" + parts[i]
                i += 1
            parts = merged

        # Pad with originals if too few
        while len(parts) < expected:
            parts.append(originals[len(parts)])
        return parts[:expected]
