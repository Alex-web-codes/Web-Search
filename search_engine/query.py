"""Query processing.

Parses a boolean query into a small tree and evaluates it against sets of
document ids.

Syntax
    AND, OR, NOT     operators (case-insensitive)
    ( )              grouping
    cat dog          words next to each other are joined with AND
    retriev*         wildcard words are passed through untouched; the
                     engine expands them (see wildcard.py)

Precedence: NOT > AND > OR, so  a OR b AND NOT c  means  a OR (b AND (NOT c)).

This module knows nothing about the index. `evaluate` takes a `resolve`
function that turns a word into the set of documents containing it.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass


class QueryError(ValueError):
    """The query could not be parsed. The message is safe to show users."""


# --- syntax tree -------------------------------------------------------------


@dataclass(frozen=True)
class Term:
    word: str


@dataclass(frozen=True)
class Not:
    operand: "Node"


@dataclass(frozen=True)
class And:
    left: "Node"
    right: "Node"


@dataclass(frozen=True)
class Or:
    left: "Node"
    right: "Node"


Node = Term | Not | And | Or

# --- lexing ------------------------------------------------------------------

_OPERATORS = {"AND", "OR", "NOT"}
_PRECEDENCE = {"NOT": 3, "AND": 2, "OR": 1}
_LEX_RE = re.compile(r"[()]|[^\s()]+")


@dataclass(frozen=True)
class _Tok:
    kind: str  # "TERM", "AND", "OR", "NOT", "(", ")"
    text: str


def _lex(query: str) -> list[_Tok]:
    tokens = []
    for raw in _LEX_RE.findall(query):
        if raw in "()":
            tokens.append(_Tok(raw, raw))
        elif raw.upper() in _OPERATORS:
            tokens.append(_Tok(raw.upper(), raw))
        else:
            tokens.append(_Tok("TERM", raw))
    return _insert_implicit_and(tokens)


def _insert_implicit_and(tokens: list[_Tok]) -> list[_Tok]:
    out: list[_Tok] = []
    for tok in tokens:
        if out and out[-1].kind in ("TERM", ")") and tok.kind in ("TERM", "(", "NOT"):
            out.append(_Tok("AND", ""))
        out.append(tok)
    return out


# --- parsing (shunting-yard into postfix, then into a tree) -----------------


def _to_postfix(tokens: list[_Tok]) -> list[_Tok]:
    output: list[_Tok] = []
    stack: list[_Tok] = []
    for tok in tokens:
        if tok.kind == "TERM":
            output.append(tok)
        elif tok.kind in ("NOT", "("):
            stack.append(tok)  # NOT is a prefix operator: nothing to pop yet
        elif tok.kind in ("AND", "OR"):
            while stack and stack[-1].kind in _PRECEDENCE and (
                _PRECEDENCE[stack[-1].kind] >= _PRECEDENCE[tok.kind]
            ):
                output.append(stack.pop())
            stack.append(tok)
        elif tok.kind == ")":
            while stack and stack[-1].kind != "(":
                output.append(stack.pop())
            if not stack:
                raise QueryError("There is a ')' without a matching '('.")
            stack.pop()
    while stack:
        tok = stack.pop()
        if tok.kind == "(":
            raise QueryError("There is a '(' that is never closed.")
        output.append(tok)
    return output


def parse(query: str) -> Node:
    tokens = _lex(query)
    if not tokens:
        raise QueryError("Type a word to search for.")

    stack: list[Node] = []
    for tok in _to_postfix(tokens):
        if tok.kind == "TERM":
            stack.append(Term(tok.text))
        elif tok.kind == "NOT":
            if not stack:
                raise QueryError("NOT needs a word after it.")
            stack.append(Not(stack.pop()))
        else:
            if len(stack) < 2:
                raise QueryError(f"{tok.kind} needs a word on both sides.")
            right, left = stack.pop(), stack.pop()
            stack.append(And(left, right) if tok.kind == "AND" else Or(left, right))

    if len(stack) != 1:
        raise QueryError("The query is incomplete.")
    return stack[0]


# --- evaluation --------------------------------------------------------------


def evaluate(node: Node, resolve: Callable[[str], set[int]], universe: set[int]) -> set[int]:
    if isinstance(node, Term):
        return resolve(node.word)
    if isinstance(node, Not):
        return universe - evaluate(node.operand, resolve, universe)
    left = evaluate(node.left, resolve, universe)
    right = evaluate(node.right, resolve, universe)
    return left & right if isinstance(node, And) else left | right


def positive_words(node: Node, negated: bool = False) -> list[str]:
    """Words that count *for* a match (not under an odd number of NOTs).

    Used for ranking and highlighting, where negated words make no sense.
    """
    if isinstance(node, Term):
        return [] if negated else [node.word]
    if isinstance(node, Not):
        return positive_words(node.operand, not negated)
    return positive_words(node.left, negated) + positive_words(node.right, negated)


def all_words(node: Node) -> list[str]:
    if isinstance(node, Term):
        return [node.word]
    if isinstance(node, Not):
        return all_words(node.operand)
    return all_words(node.left) + all_words(node.right)
