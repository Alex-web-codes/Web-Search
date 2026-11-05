"""Build the index and start the search page.

    python run.py
    python run.py --docs path/to/your/documents --port 8080 --no-browser
"""

import argparse
import sys
from pathlib import Path

from gui.server import serve
from search_engine import SearchEngine

DEFAULT_DOCS = Path(__file__).parent / "data" / "documents"


def main() -> int:
    parser = argparse.ArgumentParser(description="Boolean search engine with wildcard queries.")
    parser.add_argument("--docs", type=Path, default=DEFAULT_DOCS, help="folder of .txt documents")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--k", type=int, default=2, help="k-gram size for wildcard lookup")
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    args = parser.parse_args()

    try:
        engine = SearchEngine.from_directory(args.docs, k=args.k)
    except FileNotFoundError as err:
        print(err, file=sys.stderr)
        return 1

    stats = engine.stats()
    print(f"Indexed {stats['documents']} documents, {stats['terms']} terms, {stats['tokens']} tokens.")
    serve(engine, args.host, args.port, open_browser=not args.no_browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())
