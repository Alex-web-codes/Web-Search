"""Wildcard processing with a k-gram index.

Every vocabulary term is padded with '$' and split into k-grams
(k = 2 by default):

    "index" -> "$index$" -> $i, in, nd, de, ex, x$

To answer a pattern such as "ind*x":

1. pad it and take the k-grams of each fixed piece: "$ind" and "x$"
   -> $i, in, nd, x$
2. intersect the term lists of those k-grams to get candidates
3. post-filter the candidates against the real pattern, because k-grams
   ignore order ("index" and "xdni" share k-grams but only one matches)

'*' can appear anywhere and any number of times.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .normalizer import normalize

WILDCARD = "*"
BOUNDARY = "$"


def is_wildcard(word: str) -> bool:
    return WILDCARD in word


def normalize_pattern(pattern: str) -> str:
    """Normalize the fixed parts of a pattern and collapse repeated '*'."""
    pieces = (normalize(piece) for piece in pattern.split(WILDCARD))
    return re.sub(r"\*+", WILDCARD, WILDCARD.join(pieces))


class KGramIndex:
    def __init__(self, k: int = 2) -> None:
        if k < 2:
            raise ValueError("k must be at least 2")
        self.k = k
        self._grams: dict[str, set[str]] = {}
        self._terms: set[str] = set()

    def add_terms(self, terms: Iterable[str]) -> None:
        for term in terms:
            self.add_term(term)

    def add_term(self, term: str) -> None:
        if term in self._terms:
            return
        self._terms.add(term)
        for gram in self._kgrams(BOUNDARY + term + BOUNDARY):
            self._grams.setdefault(gram, set()).add(term)

    def expand(self, pattern: str) -> list[str]:
        """Return every vocabulary term that matches `pattern`, sorted."""
        pattern = normalize_pattern(pattern)
        if not pattern.strip(WILDCARD):
            return sorted(self._terms)  # "*" on its own matches everything

        grams: set[str] = set()
        for piece in (BOUNDARY + pattern + BOUNDARY).split(WILDCARD):
            grams |= self._kgrams(piece)  # pieces shorter than k add nothing

        if grams:
            candidates = set.intersection(*(self._grams.get(g, set()) for g in grams))
        else:
            candidates = set(self._terms)

        matcher = re.compile(".*".join(re.escape(p) for p in pattern.split(WILDCARD)))
        return sorted(term for term in candidates if matcher.fullmatch(term))

    def _kgrams(self, text: str) -> set[str]:
        return {text[i : i + self.k] for i in range(len(text) - self.k + 1)}
