"""Korean text fitting rules for fixed-width GBA table fields."""

from __future__ import annotations

import re

_COMMON_REPLACEMENTS = [
    ("포켓몬", "PKMN"),
    ("기술머신", "TM"),
    ("비전머신", "HM"),
    ("트레이너", "트레너"),
    ("체육관 관장", "관장"),
    ("체육관", "체육"),
    ("마을", "타운"),
    ("시티", "시티"),
    ("타운", "타운"),
    ("도로", "로"),
    ("동굴", "굴"),
    ("산", "산"),
]

_MOVE_REPLACEMENTS = [
    ("연속", "연"),
    ("메가톤", "메가"),
    ("고양이돈받기", "고양이돈"),
    ("솔라빔", "솔라빔"),
    ("하이드로", "하이드로"),
    ("번개펀치", "번개펀치"),
    ("불꽃펀치", "불꽃펀치"),
    ("냉동펀치", "냉동펀치"),
    ("스피드스타", "스피드별"),
    ("일렉트릭", "전기"),
    ("사이코", "염동"),
]

_ITEM_REPLACEMENTS = [
    ("몬스터볼", "몬볼"),
    ("마스터볼", "마스터볼"),
    ("하이퍼볼", "하이퍼볼"),
    ("슈퍼볼", "슈퍼볼"),
    ("좋은상처약", "좋은상처"),
    ("고급상처약", "고급상처"),
    ("풀회복약", "풀회복"),
    ("만병통치제", "만병통치"),
    ("화상치료제", "화상치료"),
    ("마비치료제", "마비치료"),
    ("얼음상태치료제", "얼음치료"),
    ("잠깨는약", "잠깨기"),
    ("기력의조각", "기력조각"),
    ("기력의덩어리", "기력덩이"),
    ("이상한사탕", "이상사탕"),
    ("동굴탈출로프", "탈출로프"),
    ("벌레회피스프레이", "회피스프"),
    ("스프레이", "스프"),
    ("치료제", "치료"),
]

_CATEGORY_REPLACEMENTS = {
    "move_names": _MOVE_REPLACEMENTS,
    "item_names": _ITEM_REPLACEMENTS,
}

_CONTROL_RE = re.compile(
    r"\\(?:btn[0-9A-Fa-f]{2}|CC[0-9A-Fa-f]{4}|B[0-9A-Fa-f]|[?][0-9A-Fa-f]{2}|[A-Za-z.+<>])"
    r"|\[[A-Za-z_][A-Za-z0-9_]*\]"
    r"|\{[0-9A-Fa-f]{2}\}"
)


def estimate_korean_encoded_length(text: str, include_terminator: bool = True) -> int:
    """Estimate encoded byte length under the Korean CJK font patch."""
    length = 1 if include_terminator else 0
    i = 0
    while i < len(text):
        match = _CONTROL_RE.match(text, i)
        if match:
            token = match.group(0)
            length += _estimate_control_length(token)
            i = match.end()
            continue
        ch = text[i]
        if ch == "\n":
            length += 1
        elif ch == "\r":
            length += 0
        elif ch.isascii():
            length += 1
        else:
            length += 2
        i += 1
    return length


def fit_korean_fixed_text(text: str, byte_length: int, category: str = "") -> str:
    """Return a Korean table value that fits a fixed PCS field.

    The final fallback truncates by encoded width, but it does so before ROM
    encoding so the writer never cuts through a 2-byte Korean glyph.
    """
    if byte_length <= 1:
        return ""

    candidate = _normalize_table_text(text)
    if _fits(candidate, byte_length):
        return candidate

    for old, new in _COMMON_REPLACEMENTS + _CATEGORY_REPLACEMENTS.get(category, []):
        if old in candidate:
            shortened = candidate.replace(old, new)
            if _fits(shortened, byte_length):
                return shortened
            candidate = shortened

    no_particles = _remove_particles(candidate)
    if _fits(no_particles, byte_length):
        return no_particles
    candidate = no_particles

    compact = re.sub(r"[·ㆍ\-\s]", "", candidate)
    if _fits(compact, byte_length):
        return compact
    candidate = compact

    return _truncate_to_fit(candidate, byte_length)


def _normalize_table_text(text: str) -> str:
    text = text.strip().strip('"')
    text = text.replace("…", "...")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _fits(text: str, byte_length: int) -> bool:
    return estimate_korean_encoded_length(text, include_terminator=True) <= byte_length


def _remove_particles(text: str) -> str:
    # Useful for auto-generated LLM labels, but conservative for official names.
    for suffix in ("의", "을", "를", "이", "가", "은", "는"):
        if text.endswith(suffix) and len(text) > 2:
            return text[: -len(suffix)]
    return text


def _truncate_to_fit(text: str, byte_length: int) -> str:
    result = []
    used = 1  # terminator
    for ch in text:
        cost = 1 if ch.isascii() else 2
        if used + cost > byte_length:
            break
        result.append(ch)
        used += cost
    return "".join(result)


def _estimate_control_length(token: str) -> int:
    if token.startswith("["):
        return 2
    if token.startswith("{"):
        return 1
    if token.startswith("\\btn"):
        return 2
    if token.startswith("\\CC"):
        return 1 + max(0, (len(token) - 3) // 2)
    if token.startswith("\\?"):
        return 2
    if token in {"\\n", "\\p", "\\l", "\\."}:
        return 1
    return 1
