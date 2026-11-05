"""Tokenization.

Splits raw text into word tokens. A token is a run of letters or digits,
optionally joined by apostrophes ("don't", "o'brien"). Everything else,
including hyphens, is a separator, so "state-of-the-art" becomes four tokens.

Each token keeps its character offsets so the GUI can highlight matches
in the original text.
"""

from __future__ import annotations

import re
from typing import NamedTuple

# [^\W_] = any Unicode letter or digit.
_TOKEN_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")


class Token(NamedTuple):
    text: str
    start: int
    end: int


def tokenize(text: str) -> list[Token]:
    """Return tokens with their positions in `text`."""
    return [Token(m.group(), m.start(), m.end()) for m in _TOKEN_RE.finditer(text)]


def words(text: str) -> list[str]:
    """Return just the token strings."""
    return _TOKEN_RE.findall(text)
