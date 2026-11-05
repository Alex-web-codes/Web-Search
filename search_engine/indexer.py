"""Inverted index construction.

Maps each term to its postings: the documents it appears in and how many
times (term frequency). This module only deals with terms; turning text
into terms is the tokenizer's and normalizer's job.

    "index" -> {0: 3, 4: 1}     # doc 0 has it 3 times, doc 4 once
"""

from __future__ import annotations

from collections.abc import Iterable


class InvertedIndex:
    def __init__(self) -> None:
        self._postings: dict[str, dict[int, int]] = {}
        self._doc_lengths: dict[int, int] = {}

    def add_document(self, doc_id: int, terms: Iterable[str]) -> None:
        if doc_id in self._doc_lengths:
            raise ValueError(f"Document {doc_id} is already indexed")
        count = 0
        for term in terms:
            postings = self._postings.setdefault(term, {})
            postings[doc_id] = postings.get(doc_id, 0) + 1
            count += 1
        self._doc_lengths[doc_id] = count

    # --- lookups -----------------------------------------------------------

    def postings(self, term: str) -> dict[int, int]:
        """doc_id -> term frequency. Empty if the term is unknown."""
        return self._postings.get(term, {})

    def doc_ids(self, term: str) -> set[int]:
        return set(self._postings.get(term, ()))

    def document_frequency(self, term: str) -> int:
        return len(self._postings.get(term, ()))

    def doc_length(self, doc_id: int) -> int:
        return self._doc_lengths.get(doc_id, 0)

    # --- whole-index views -------------------------------------------------

    @property
    def vocabulary(self) -> list[str]:
        return sorted(self._postings)

    @property
    def all_doc_ids(self) -> set[int]:
        return set(self._doc_lengths)

    @property
    def total_tokens(self) -> int:
        return sum(self._doc_lengths.values())

    def __contains__(self, term: str) -> bool:
        return term in self._postings

    def __len__(self) -> int:
        return len(self._postings)
