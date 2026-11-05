"""Document loading.

Reads every text file in a folder (recursively) and turns each one into a
`Document` with a stable integer id. Files are sorted by path so the same
folder always produces the same ids.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_EXTENSIONS = (".txt",)


@dataclass(frozen=True)
class Document:
    doc_id: int
    name: str  # path relative to the corpus folder, e.g. "news/day1.txt"
    path: Path
    text: str


def load_documents(directory: str | Path, extensions=DEFAULT_EXTENSIONS) -> list[Document]:
    root = Path(directory)
    if not root.is_dir():
        raise FileNotFoundError(f"Document folder not found: {root}")

    wanted = {ext.lower() for ext in extensions}
    files = sorted(
        (p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in wanted),
        key=lambda p: p.relative_to(root).as_posix().lower(),
    )

    return [
        Document(
            doc_id=doc_id,
            name=path.relative_to(root).as_posix(),
            path=path,
            text=path.read_text(encoding="utf-8", errors="replace"),
        )
        for doc_id, path in enumerate(files)
    ]
