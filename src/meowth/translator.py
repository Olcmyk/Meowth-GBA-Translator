"""DeepSeek translation with local caching."""

import hashlib
import json
import os
from pathlib import Path

import httpx

DEFAULT_CACHE_DIR = Path(__file__).parent.parent.parent / "work" / "cache"

SYSTEM_PROMPT = """你是一个专业的宝可梦游戏翻译器，负责将GBA宝可梦火红的英文文本翻译成简体中文。

翻译规则：
1. 保持宝可梦游戏的语气和风格（轻松、冒险、友好）
2. 控制码占位符（如 {C0}, {C1} 等）必须原样保留，不要翻译或修改
3. 翻译要简洁，中文文本不要比英文长太多（GBA文本框宽度有限）
4. 每行最多约21个中文字符
5. 专有名词请参考提供的术语表

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

    def _cache_key(self, request_data: dict) -> str:
        content = json.dumps(request_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_cached(self, key: str) -> str | None:
        resp_path = self.cache_dir / f"{key}_response.json"
        if resp_path.exists():
            data = json.loads(resp_path.read_text(encoding="utf-8"))
            return data.get("content")
        return None

    def _save_cache(self, key: str, request_data: dict, content: str):
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
            results = [t.strip() for t in cached.split("|||")]
            # Pad or truncate to match input length
            while len(results) < len(texts):
                results.append(texts[len(results)])  # fallback to original
            return results[: len(texts)]

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

        self._save_cache(cache_key, request_data, content)

        results = [t.strip() for t in content.split("|||")]
        while len(results) < len(texts):
            results.append(texts[len(results)])
        return results[: len(texts)]
