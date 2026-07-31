"""Change Impact Analysis Agent — root orchestration.

Given a GitHub Issue (CR / Feature Request) as input, this pipeline:
1. Extracts technical intent from the ticket (Intent Extractor Agent).
2. Concurrently searches architecture docs and the codebase (Context
   Retrieval: ParallelAgent of Doc Search + Code Search).
3. Maps upstream/downstream dependencies via static analysis (Dependency
   Mapper Agent).
4. Concurrently evaluates application-architecture, code, and testing
   impact — including FinOps cost tier estimation (Impact & Risk
   Evaluators: ParallelAgent).
5. Synthesizes a structured, schema-enforced Change Impact Assessment
   (Report Synthesizer Agent).
6. Publishes a styled PDF report to GCS, comments on the GitHub issue, and
   enforces human-in-the-loop governance (high-risk label + tech-lead
   mention) for High-risk / breaking changes (Publisher & Governance Agent).

This is an analysis-only pipeline: it never modifies code, so there is no
generate/validate/retry loop to manage — state flows forward through
session-state keys with no backward edges, mirroring the SequentialAgent +
single ParallelAgent design in the requirements doc.

`root_agent` is exported at module level per the Google Cloud Agent Runtime
execution contract (`adk run` / `adk web` / `AdkApp` all look for this name).
`app` (an ADK `App` wrapping `root_agent`) is also exported for runtimes
that expect the newer App contract.
"""

from __future__ import annotations

from google.adk.agents import SequentialAgent

try:
    from google.adk.apps.app import App
except ImportError:  # pragma: no cover - older ADK releases without App
    App = None

from .sub_agents import (
    context_retrieval_parallel,
    dependency_mapper_agent,
    impact_risk_evaluators_parallel,
    intent_extractor_agent,
    publisher_governance_agent,
    report_synthesizer_agent,
)
from .utils.telemetry import configure_telemetry

# Configure OpenTelemetry tracing + Cloud Logging as soon as the pipeline is
# constructed, so every agent step / tool call below is captured for audit.
configure_telemetry()

root_agent = SequentialAgent(
    name="change_impact_analysis_pipeline",
    description=(
        "Analyzes a Change Request / Feature Request GitHub issue end-to-end: "
        "extracts intent, cross-references docs and code, maps dependencies, "
        "assesses architectural/code/FinOps/testing risk, and publishes a "
        "governed Change Impact Assessment report."
    ),
    sub_agents=[
        intent_extractor_agent,
        context_retrieval_parallel,  # ParallelAgent: doc_search + code_search
        dependency_mapper_agent,
        impact_risk_evaluators_parallel,  # ParallelAgent: app_arch + code + testing evals
        report_synthesizer_agent,
        publisher_governance_agent,
    ],
)

if App is not None:
    app = App(root_agent=root_agent, name="change_impact_analysis_agent")
