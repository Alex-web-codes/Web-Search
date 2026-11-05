"""A small boolean search engine with wildcard support.

Modules, in pipeline order:
    loader      read documents from disk
    tokenizer   split text into tokens
    normalizer  case folding and other clean-up
    indexer     build the inverted index
    query       parse and evaluate boolean queries
    wildcard    expand '*' patterns with a k-gram index
    engine      ties them together
"""

from .engine import Hit, SearchEngine, SearchResult
from .query import QueryError

__all__ = ["Hit", "QueryError", "SearchEngine", "SearchResult"]
