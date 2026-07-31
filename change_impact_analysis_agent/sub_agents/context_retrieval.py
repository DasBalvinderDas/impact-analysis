"""Context Retrieval: Doc Search Agent + Code Search Agent, run in parallel.

Both read only from `change_intent` (written by the Intent Extractor) and
write to independent state keys (`doc_context`, `code_context`), so they can
run concurrently inside a ParallelAgent without collisions.
"""

from __future__ import annotations

import os

from google.adk.agents import LlmAgent, ParallelAgent

from ..tools.docs_tools import docs_search_tool
from ..tools.github_tools import build_code_search_toolset

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

doc_search_agent = LlmAgent(
    name="doc_search_agent",
    model=MODEL,
    description="Searches architecture documentation for content relevant to the change intent.",
    instruction="""\
You are the Doc Search Agent. Read `change_intent` from session state and use
the `search_architecture_docs` tool to find existing architecture/design
documentation describing the components, services, or behaviors it
implicates. Run several searches if needed (one per target module/feature).
Summarize what you found — cite the `source` path/URI for every claim — and
note any documentation gaps (areas mentioned in the ticket with no matching
docs). Write your findings to state as `doc_context`.
""",
    tools=[docs_search_tool],
    output_key="doc_context",
)

code_search_agent = LlmAgent(
    name="code_search_agent",
    model=MODEL,
    description="Searches the GitHub codebase for modules/functions/endpoints implicated by the change intent.",
    instruction="""\
You are the Code Search Agent. Read `change_intent` from session state and
use the GitHub code-search tools available to you (`search_code`,
`get_file_contents`) to locate the specific files, functions, classes, and
API endpoints implicated by the change. Prefer precise queries per target
module/feature over one broad query. For each promising hit, fetch the file
contents so downstream agents (Dependency Mapper, Code Impact Evaluator) have
real source to reason about — do not fabricate file paths or contents.
Write a list of candidate files/symbols (with their contents or key excerpts)
to state as `code_context`.
""",
    tools=[build_code_search_toolset()],
    output_key="code_context",
)

context_retrieval_parallel = ParallelAgent(
    name="context_retrieval_parallel",
    description="Runs documentation search and code search concurrently.",
    sub_agents=[doc_search_agent, code_search_agent],
)
