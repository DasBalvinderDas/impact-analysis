"""Architecture documentation search tool.

Supports two sources, selected by ``DOCS_SOURCE``:

- ``gcs`` (default): searches Markdown/text docs stored in a GCS bucket
  (``ARCHITECTURE_DOCS_BUCKET``), e.g. mirrored Confluence/Notion exports.
- ``local``: searches a docs/ folder in the repository checkout, for teams
  that keep architecture docs alongside the code.

Exposed as a ``FunctionTool`` for the Doc Search Agent.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List

from google.adk.tools import FunctionTool

from ..utils.telemetry import get_logger

_MAX_RESULTS = 8
_SNIPPET_RADIUS = 400


def _search_local_docs(query: str, docs_root: str) -> List[dict]:
    root = Path(docs_root)
    results: List[dict] = []
    if not root.exists():
        return results

    terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".mdx", ".txt", ".rst"}:
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        lowered = text.lower()
        hits = sum(lowered.count(t) for t in terms)
        if hits == 0:
            continue
        first_idx = min((lowered.find(t) for t in terms if t in lowered), default=0)
        start = max(0, first_idx - _SNIPPET_RADIUS // 2)
        snippet = text[start:start + _SNIPPET_RADIUS].strip()
        results.append({"source": str(path), "score": hits, "snippet": snippet})

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:_MAX_RESULTS]


def _search_gcs_docs(query: str, bucket_name: str, prefix: str = "architecture-docs/") -> List[dict]:
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]

    results: List[dict] = []
    for blob in client.list_blobs(bucket, prefix=prefix):
        if not blob.name.lower().endswith((".md", ".txt", ".rst")):
            continue
        text = blob.download_as_text(encoding="utf-8", errors="ignore")
        lowered = text.lower()
        hits = sum(lowered.count(t) for t in terms)
        if hits == 0:
            continue
        first_idx = min((lowered.find(t) for t in terms if t in lowered), default=0)
        start = max(0, first_idx - _SNIPPET_RADIUS // 2)
        snippet = text[start:start + _SNIPPET_RADIUS].strip()
        results.append({"source": f"gs://{bucket_name}/{blob.name}", "score": hits, "snippet": snippet})

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:_MAX_RESULTS]


def search_architecture_docs(query: str) -> dict:
    """Search architecture/design documentation for content relevant to ``query``.

    Args:
        query: Keywords describing the components/behaviors implicated by the change
            (typically drawn from ``technical_intent``).

    Returns:
        A dict with a ``results`` list of ``{source, score, snippet}`` matches,
        ordered by relevance, or an empty list if nothing matched.
    """
    logger = get_logger()
    source = os.environ.get("DOCS_SOURCE", "gcs")

    if source == "local":
        docs_root = os.environ.get("ARCHITECTURE_DOCS_PATH", "docs")
        results = _search_local_docs(query, docs_root)
    else:
        bucket_name = os.environ.get("ARCHITECTURE_DOCS_BUCKET")
        if not bucket_name:
            logger.warning("ARCHITECTURE_DOCS_BUCKET unset; no docs to search.")
            return {"results": []}
        results = _search_gcs_docs(query, bucket_name)

    logger.info("doc_search query=%r results=%d source=%s", query, len(results), source)
    return {"results": results}


docs_search_tool = FunctionTool(func=search_architecture_docs)
