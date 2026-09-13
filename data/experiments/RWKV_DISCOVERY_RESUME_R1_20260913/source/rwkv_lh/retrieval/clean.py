"""Deterministic bounded cleanup for untrusted retrieved documents."""

from __future__ import annotations

import json
import re
from html import unescape
from html.parser import HTMLParser
from typing import Any


_BLOCK = {
    "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt",
    "figcaption", "figure", "h1", "h2", "h3", "h4", "h5", "h6",
    "header", "hr", "li", "main", "p", "pre", "section", "table",
    "td", "th", "tr", "ul", "ol",
}
_SKIP = {"script", "style", "noscript", "svg", "template", "form"}


class _ReadableHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0
        self.title_parts: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        selected = tag.casefold()
        if self.skip_depth:
            if selected not in {"meta", "link", "img", "br", "hr", "input"}:
                self.skip_depth += 1
            return
        if selected in _SKIP:
            self.skip_depth = 1
            return
        if selected == "title":
            self.in_title = True
        if selected in _BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        selected = tag.casefold()
        if self.skip_depth:
            self.skip_depth -= 1
            return
        if selected == "title":
            self.in_title = False
        if selected in _BLOCK:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        value = unescape(str(data or ""))
        if self.in_title:
            self.title_parts.append(value)
            return
        self.parts.append(value)

    def result(self) -> tuple[str, str]:
        text = "".join(self.parts).replace("\r\n", "\n").replace("\r", "\n")
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
        compact: list[str] = []
        for line in lines:
            if line:
                compact.append(line)
            elif compact and compact[-1] != "":
                compact.append("")
        cleaned = "\n".join(compact).strip()
        title = re.sub(r"\s+", " ", "".join(self.title_parts)).strip()
        return cleaned, title


def clean_document(payload: bytes, media_type: str) -> tuple[str, str]:
    """Return clean UTF-8 text and a best-effort title without authoring facts."""

    if len(payload) > 8_000_000:
        raise ValueError("retrieved payload exceeds the cleanup bound")
    text = payload.decode("utf-8", errors="replace")
    selected_type = str(media_type or "").split(";", 1)[0].strip().casefold()
    if selected_type in {"application/json", "application/ld+json"}:
        try:
            parsed: Any = json.loads(text)
        except json.JSONDecodeError:
            return text.strip(), ""
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True, indent=2), ""
    if selected_type in {"text/html", "application/xhtml+xml"} or "<html" in text[:1000].casefold():
        parser = _ReadableHTML()
        parser.feed(text)
        parser.close()
        return parser.result()
    return text.replace("\r\n", "\n").replace("\r", "\n").strip(), ""


__all__ = ["clean_document"]
