"""Dependency Mapping Agent.

Traces upstream callers and downstream dependencies of the code identified
by the Code Search Agent, using the static-analysis tool (import/call-graph
parsing) rather than free-form reasoning, and writes the result to
`dependency_map`.
"""

from __future__ import annotations

import os

from google.adk.agents import LlmAgent

from ..models.schemas import DependencyMap
from ..tools.static_analysis import (
    analyze_file_dependencies_tool,
    build_dependency_summary_tool,
)

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

_INSTRUCTION = """\
You are the Dependency Mapper Agent. Read `code_context` (files/symbols found
by the Code Search Agent) from session state.

For each implicated file:
1. Call `analyze_file_dependencies` with its path and content to get its
   direct imports, function calls, and reverse dependents (files that import
   it) via static import/call-graph parsing — do not guess at dependencies
   the tool didn't report.
2. Optionally call `build_dependency_summary` with the collected per-file
   results to get a de-duplicated aggregate view.

Then, cross-referencing `doc_context` for anything the docs call out that the
static analysis missed (e.g. external API contracts described only in prose),
produce the final dependency map:
- upstream_calling_services: services/jobs/UI components that call into the
  affected code (from `imported_by` / doc mentions of callers).
- downstream_dependencies: services, external APIs, or shared libraries the
  affected code calls out to (from `imports` / doc mentions).
- database_tables_affected: tables/collections referenced in the code or docs.
- api_contracts_modified: API endpoints/contracts whose shape or behavior
  would change.

Output strictly as the `DependencyMap` schema.
"""

dependency_mapper_agent = LlmAgent(
    name="dependency_mapper_agent",
    model=MODEL,
    description="Maps upstream/downstream dependencies of the implicated code via static analysis.",
    instruction=_INSTRUCTION,
    tools=[analyze_file_dependencies_tool, build_dependency_summary_tool],
    output_schema=DependencyMap,
    output_key="dependency_map",
)
