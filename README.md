# web-search-mining

A small boolean search engine with wildcard queries and a web interface.
Pure Python standard library: nothing to install.

## Run it

```bash
python run.py
```

This indexes the files in `data/documents/` and opens `http://127.0.0.1:8000/`.

Options:

```bash
python run.py --docs path/to/documents --port 8080 --k 3 --no-browser
```

Run the tests:

```bash
python -m unittest discover -s tests -v
```

## Project structure

```
run.py                     entry point: build the index, start the GUI
search_engine/
  loader.py                1. document loading       folder of .txt files -> Document(id, name, text)
  tokenizer.py             2. tokenization           text -> tokens with character offsets
  normalizer.py            3. normalization          case folding, accent and apostrophe removal
  indexer.py               4. inverted index         term -> {doc_id: term frequency}
  query.py                 5. query processing       parse AND / OR / NOT / ( ) and evaluate
  wildcard.py              6. wildcard processing    k-gram index, expands patterns like retriev*
  engine.py                ties the modules together, ranks hits, builds snippets
gui/
  server.py                7. frontend GUI           HTTP server + JSON API
  static/                  index.html, style.css, app.js
data/documents/            sample corpus (replace with your own .txt files)
tests/                     unit tests for every module
```

## Pipeline

```
documents ─ loader ─ tokenizer ─ normalizer ─┬─ InvertedIndex
                                             └─ KGramIndex (built from the vocabulary)

query ─ query.parse ─ evaluate ─┬─ plain word  → same tokenizer + normalizer → postings
                                └─ wildcard    → KGramIndex.expand → union of postings
      ─ rank by term frequency ─ snippet with highlights ─ GUI
```

## Query syntax

| Query                          | Meaning                                      |
| ------------------------------ | -------------------------------------------- |
| `index retrieval`              | both words (adjacent words are joined by AND) |
| `index AND retrieval`          | both words                                   |
| `crawler OR spider`            | either word                                  |
| `index AND NOT compression`    | first word, but not the second               |
| `(crawler OR spider) AND web`  | parentheses group                            |
| `retriev*`, `*ization`, `r*l`  | `*` matches any run of letters               |

Operators are case-insensitive. Precedence is `NOT` > `AND` > `OR`.

## Design notes

- **Tokenization** splits on anything that is not a letter or digit, except
  apostrophes inside a word, so `state-of-the-art` becomes four tokens and
  `don't` stays one.
- **Normalization** applies `str.casefold()`, strips accents (`café` → `cafe`)
  and removes apostrophes (`don't` → `dont`). Queries go through the same
  steps, so `CAFE` finds `café`.
- **Wildcards** use a k-gram index (k = 2 by default). Each term is padded
  with `$`, the pattern's k-grams select candidate terms, and a regex
  post-filter removes candidates whose k-grams match but in the wrong order.
- **Ranking**: boolean retrieval returns a set; results are ordered by how
  often the matched (non-negated) terms occur in each document.
