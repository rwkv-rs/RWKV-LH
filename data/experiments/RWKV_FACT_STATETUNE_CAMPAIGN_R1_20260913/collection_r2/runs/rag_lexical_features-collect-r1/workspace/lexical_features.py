import re
from typing import Any


_ALIAS_KEYS = (
    "aliases",
    "alias",
    "redirects",
    "redirect",
    "alternate_names",
    "alternate_name",
    "aka",
)
_ALIAS_PATTERN = re.compile(
    r"(?:又称|又稱|又名|亦称|亦稱|也称|也稱|曾称|曾稱|简称|簡稱|旧称|舊稱|原名|别称|別稱)"
    r"(?:为|為|作)?[：:]?\s*([^，,。！？!?；;）)\n]{1,80})"
)
_PARENTHETICAL_TITLE = re.compile(r"^(?P<base>.+?)\s*[（(][^）)]{1,40}[）)]$")
_ALIAS_SPLIT = re.compile(r"[、，,；;]|(?:或称|或稱|以及|及|和|与|與)")
_ALIAS_PREFIX = re.compile(r"^(?:为|為|作|叫作|称作|稱作)\s*")
_ALIAS_SUFFIX = re.compile(r"(?:之一|等)$")


def _metadata_alias_values(metadata: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in _ALIAS_KEYS:
        value = metadata.get(key)
        if isinstance(value, (list, tuple, set)):
            values.extend(str(item) for item in value)
        elif value is not None:
            values.append(str(value))
    return values


def _clean_alias(value: str) -> str:
    cleaned = value.strip(" \t\"'“”‘’《》【】[]（）()")
    cleaned = _ALIAS_PREFIX.sub("", cleaned)
    cleaned = _ALIAS_SUFFIX.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" 的")
    return cleaned


def extract_document_aliases(
    title: str,
    text: str,
    metadata: dict[str, Any] | None = None,
) -> list[str]:
    """Extract conservative document aliases for lexical entity lookup."""
    candidates = _metadata_alias_values(metadata or {})
    title_match = _PARENTHETICAL_TITLE.match(title.strip())
    if title_match:
        candidates.append(title_match.group("base"))

    lead = " ".join(text[:800].splitlines())
    for match in _ALIAS_PATTERN.finditer(lead):
        value = re.split(
            r"[，,](?:是|为|為|指|属于|屬於|位于|位於)",
            match.group(1),
            maxsplit=1,
        )[0]
        candidates.extend(_ALIAS_SPLIT.split(value))

    aliases: list[str] = []
    normalized_title = _clean_alias(title)
    for candidate in candidates:
        alias = _clean_alias(candidate)
        if (
            1 < len(alias) <= 40
            and alias != normalized_title
            and not alias.startswith(("一种", "一種", "一个", "一個"))
            and alias not in aliases
        ):
            aliases.append(alias)
    return aliases[:16]
