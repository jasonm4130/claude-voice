"""Turn an assistant reply into a short line worth saying out loud."""

import re

MAX_WORDS = 35

_SPOKEN = re.compile(r"<spoken>(.*?)</spoken>", re.S | re.I)
_FENCE = re.compile(r"```.*?(```|$)", re.S)
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$", re.M)
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_URL = re.compile(r"https?://\S+")
_INLINE_CODE = re.compile(r"`([^`]*)`")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s.*$", re.M)
_MARKUP = re.compile(r"^\s{0,3}([-*+]\s+|\d+[.)]\s+|>\s?)", re.M)
_EMPHASIS = re.compile(r"(\*\*|__|\*|_)(?=\S)(.+?)(?<=\S)\1")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def spoken_text(reply: str, max_words: int = MAX_WORDS) -> str:
    """A `<spoken>` block verbatim, else the reply stripped of markup and cut to whole sentences."""
    match = _SPOKEN.search(reply or "")
    if match:
        return _squash(match.group(1))

    text = _FENCE.sub(" ", reply or "")
    text = _TABLE_ROW.sub(" ", text)
    text = _HEADING.sub(" ", text)
    text = _LINK.sub(r"\1", text)
    text = _URL.sub(" ", text)
    text = _INLINE_CODE.sub(r"\1", text)
    text = _MARKUP.sub("", text)
    text = _EMPHASIS.sub(r"\2", text)
    text = _squash(text)
    if not text:
        return ""

    kept: list[str] = []
    count = 0
    for sentence in _SENTENCE_END.split(text):
        words = sentence.split()
        if kept and count + len(words) > max_words:
            break
        if not kept and len(words) > max_words:
            return " ".join(words[:max_words]).rstrip(",;:") + "."
        kept.append(sentence)
        count += len(words)
    return " ".join(kept)


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
