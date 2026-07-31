"""Static-analysis tool for the Dependency Mapper Agent.

v1 scope (per the design doc's "static analysis only" recommendation):
language-appropriate import/call-graph parsing over the files identified by
the Code Search Agent. Reliably finds direct references — who imports this
module, what this module imports, which functions call which — without
requiring an embedding index. Currently supports Python (``ast``) and a
regex-based fallback for JS/TS ``import``/``require`` statements.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Dict, List

from google.adk.tools import FunctionTool

from ..utils.telemetry import get_logger

_JS_IMPORT_RE = re.compile(
    r"""(?:import\s+.*?from\s+['"](?P<from_spec>[^'"]+)['"])"""
    r"""|(?:require\(\s*['"](?P<require_spec>[^'"]+)['"]\s*\))""",
    re.MULTILINE,
)


def _python_imports(source: str) -> List[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    imports: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return sorted(set(imports))


def _python_calls(source: str) -> List[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    calls: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                calls.append(func.id)
            elif isinstance(func, ast.Attribute):
                calls.append(func.attr)
    return sorted(set(calls))


def _js_imports(source: str) -> List[str]:
    specs: List[str] = []
    for match in _JS_IMPORT_RE.finditer(source):
        spec = match.group("from_spec") or match.group("require_spec")
        if spec:
            specs.append(spec)
    return sorted(set(specs))


def _find_importers(module_hint: str, search_root: str, extensions: tuple[str, ...]) -> List[str]:
    """Reverse lookup: which files under ``search_root`` import ``module_hint``."""
    importers: List[str] = []
    root = Path(search_root)
    if not root.exists():
        return importers

    needle = module_hint.replace(".py", "").split("/")[-1]
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        if needle in text and str(path) != module_hint:
            if re.search(rf"\b{re.escape(needle)}\b", text):
                importers.append(str(path))
    return importers


def analyze_file_dependencies(file_path: str, file_content: str, search_root: str = ".") -> dict:
    """Parse a single source file's import/call graph and find its reverse dependents.

    Args:
        file_path: Repo-relative path of the file to analyze (as returned by the
            code-search tool).
        file_content: Full text contents of the file (as returned by
            ``get_file_contents``).
        search_root: Local checkout root to search for reverse dependents
            (files that import this module). Defaults to the current directory;
            set to a cloned-repo path when available.

    Returns:
        A dict with ``imports`` (what this file depends on), ``calls`` (function/
        method names invoked in this file), and ``imported_by`` (other files in
        ``search_root`` that appear to import this module, i.e. upstream callers).
    """
    logger = get_logger()
    suffix = Path(file_path).suffix.lower()

    if suffix == ".py":
        imports = _python_imports(file_content)
        calls = _python_calls(file_content)
        importers = _find_importers(file_path, search_root, (".py",))
    elif suffix in {".js", ".jsx", ".ts", ".tsx"}:
        imports = _js_imports(file_content)
        calls = []
        importers = _find_importers(file_path, search_root, (".js", ".jsx", ".ts", ".tsx"))
    else:
        imports, calls, importers = [], [], []

    logger.info(
        "static_analysis file=%s imports=%d calls=%d imported_by=%d",
        file_path, len(imports), len(calls), len(importers),
    )
    return {
        "file_path": file_path,
        "imports": imports,
        "calls": calls,
        "imported_by": importers,
    }


def build_dependency_summary(file_analyses: List[dict]) -> dict:
    """Aggregate per-file ``analyze_file_dependencies`` results into a graph summary.

    Args:
        file_analyses: List of results previously returned by
            ``analyze_file_dependencies`` for each implicated file.

    Returns:
        A dict with ``upstream_calling_files`` (union of ``imported_by`` across
        all files) and ``downstream_dependency_modules`` (union of ``imports``),
        de-duplicated and sorted — ready to seed ``DependencyMap``.
    """
    upstream: set[str] = set()
    downstream: set[str] = set()
    for analysis in file_analyses:
        upstream.update(analysis.get("imported_by", []))
        downstream.update(analysis.get("imports", []))
    return {
        "upstream_calling_files": sorted(upstream),
        "downstream_dependency_modules": sorted(downstream),
    }


analyze_file_dependencies_tool = FunctionTool(func=analyze_file_dependencies)
build_dependency_summary_tool = FunctionTool(func=build_dependency_summary)
