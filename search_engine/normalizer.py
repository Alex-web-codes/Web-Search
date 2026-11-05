"""Text normalization and case folding.

Turns a token into the form stored in the index:

1. case folding     "Retrieval" -> "retrieval"  (casefold also handles "Straße" -> "strasse")
2. accent removal   "café"      -> "cafe"
3. apostrophes      "don't"     -> "dont"

Documents and queries go through the same function, so they always meet
in the same vocabulary.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable

_DROP = str.maketrans("", "", "'’")


def normalize(token: str) -> str:
    folded = unicodedata.normalize("NFKD", token.casefold())
    no_accents = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return no_accents.translate(_DROP)


def normalize_all(tokens: Iterable[str]) -> list[str]:
    """Normalize many tokens, dropping any that end up empty."""
    return [term for term in map(normalize, tokens) if term]
