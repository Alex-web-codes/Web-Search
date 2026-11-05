"""The search engine: wires the other modules together.

    load_documents  ->  tokenize  ->  normalize  ->  InvertedIndex
                                                    KGramIndex (for wildcards)
    query  ->  parse  ->  evaluate (resolving each word, expanding wildcards)
           ->  rank by term frequency  ->  snippets with highlights
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter

from .indexer import InvertedIndex
from .loader import Document, load_documents
from .normalizer import normalize, normalize_all
from .query import evaluate, parse, positive_words
from .tokenizer import tokenize, words
from .wildcard import KGramIndex, is_wildcard

SNIPPET_WIDTH = 240
_SPACE_RE = re.compile(r"\s")


def analyze(text: str) -> list[str]:
    """Text -> index terms. Documents and plain query words both use this."""
    return normalize_all(words(text))


@dataclass
class Hit:
    doc_id: int
    name: str
    score: int  # total occurrences of the matched (non-negated) terms
    words: int  # document length in tokens
    snippet: str
    highlights: list[tuple[int, int]]  # [start, end) offsets into snippet


@dataclass
class SearchResult:
    query: str
    hits: list[Hit]
    expansions: dict[str, list[str]] = field(default_factory=dict)
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class SearchEngine:
    def __init__(self, documents: list[Document], k: int = 2) -> None:
        self.documents = {doc.doc_id: doc for doc in documents}

        self.index = InvertedIndex()
        for doc in documents:
            self.index.add_document(doc.doc_id, analyze(doc.text))

        self.kgrams = KGramIndex(k)
        self.kgrams.add_terms(self.index.vocabulary)

    @classmethod
    def from_directory(cls, directory: str | Path, k: int = 2) -> "SearchEngine":
        return cls(load_documents(directory), k)

    # --- searching -----------------------------------------------------------

    def search(self, query: str) -> SearchResult:
        started = perf_counter()
        tree = parse(query)  # raises QueryError on bad syntax

        resolved: dict[str, tuple[list[str], set[int]]] = {}

        def resolve(word: str) -> set[int]:
            if word not in resolved:
                resolved[word] = self._resolve(word)
            return resolved[word][1]

        doc_ids = evaluate(tree, resolve, self.index.all_doc_ids)

        ranking_terms = {term for word in positive_words(tree) for term in resolved[word][0]}
        hits = [self._make_hit(doc_id, ranking_terms) for doc_id in doc_ids]
        hits.sort(key=lambda hit: (-hit.score, hit.name.lower()))

        return SearchResult(
            query=query,
            hits=hits,
            expansions={word: terms for word, (terms, _) in resolved.items() if is_wildcard(word)},
            elapsed_ms=round((perf_counter() - started) * 1000, 3),
        )

    def _resolve(self, word: str) -> tuple[list[str], set[int]]:
        """A query word -> (index terms it stands for, documents that match)."""
        if is_wildcard(word):
            terms = self.kgrams.expand(word)
            return terms, set().union(*(self.index.doc_ids(t) for t in terms))

        # A word like "e-mail" analyzes to two terms; both must appear.
        terms = analyze(word)
        if not terms:
            return [], set()
        return terms, set.intersection(*(self.index.doc_ids(t) for t in terms))

    def _make_hit(self, doc_id: int, terms: set[str]) -> Hit:
        doc = self.documents[doc_id]
        snippet, highlights = make_snippet(doc.text, terms)
        return Hit(
            doc_id=doc_id,
            name=doc.name,
            score=sum(self.index.postings(term).get(doc_id, 0) for term in terms),
            words=self.index.doc_length(doc_id),
            snippet=snippet,
            highlights=highlights,
        )

    # --- info ----------------------------------------------------------------

    def stats(self) -> dict:
        return {
            "documents": len(self.documents),
            "terms": len(self.index),
            "tokens": self.index.total_tokens,
            "k": self.kgrams.k,
            "names": [self.documents[i].name for i in sorted(self.documents)],
        }


def make_snippet(text: str, terms: set[str], width: int = SNIPPET_WIDTH) -> tuple[str, list[tuple[int, int]]]:
    """Cut a window of `text` around the first matching term and mark matches."""
    first = next((tok for tok in tokenize(text) if normalize(tok.text) in terms), None)

    start = 0
    if first is not None and first.start > width // 3:
        start = first.start - width // 3
        space = _SPACE_RE.search(text, start, first.start)  # don't start mid-word
        start = space.end() if space else first.start

    end = min(len(text), start + width)
    if end < len(text):
        cut = max(text.rfind(c, start, end) for c in " \n\t")  # don't end mid-word
        if cut > (first.end if first else start):
            end = cut

    body = " ".join(text[start:end].split())
    snippet = ("… " if start > 0 else "") + body + (" …" if end < len(text) else "")
    highlights = [(tok.start, tok.end) for tok in tokenize(snippet) if normalize(tok.text) in terms]
    return snippet, highlights
