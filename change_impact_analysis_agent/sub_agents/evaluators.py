"""Impact & Risk Evaluators — run as a ParallelAgent.

Three independent evaluators, each reading the shared upstream state
(`change_intent`, `doc_context`, `code_context`, `dependency_map`) and
writing to its own state key so they can run concurrently without
collisions:

- app_arch_eval_agent -> app_impact_result (domain risk, service boundaries,
  data contracts, FinOps cost tier)
- code_eval_agent -> code_impact_result (file-level breaking changes, refactor
  scope)
- testing_eval_agent -> test_impact_result (regression risk, test coverage
  gaps)
"""

from __future__ import annotations

import os

from google.adk.agents import LlmAgent, ParallelAgent

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

app_arch_eval_agent = LlmAgent(
    name="app_arch_eval_agent",
    model=MODEL,
    description="Evaluates application/domain risk, service boundaries, data contracts, and FinOps cost tier.",
    instruction="""\
You are the Application Architecture Evaluator. Using `change_intent`,
`doc_context`, and `dependency_map` from session state, assess:

1. Application domain risk: which services/domain entities are modified, and
   whether the change crosses a service boundary (e.g. shared library used by
   multiple teams, or a change to a public API contract).
2. FinOps cost tier: estimate the monthly cloud-cost impact tier based on any
   NEW or SCALED cloud resources implied by the change (e.g. new DB read
   replica, new cache cluster/Redis instance, new message queue/topic,
   increased compute/autoscaling ceiling, new third-party API with per-call
   billing). Use these tiers:
   - Low (<$50/mo): no new infra, or a trivial addition (e.g. one new small
     table/column, a few extra Cloud Function invocations).
   - Medium ($50-$500/mo): a new managed service/instance at small scale
     (e.g. a small cache cluster, a new Cloud Run service, a queue with
     moderate throughput).
   - High (>$500/mo): a new database replica/cluster, a new
     high-throughput queue/pipeline, or materially increased compute/storage
     at production scale.
   If the ticket/code gives no evidence of new infrastructure, default to Low
   and say so explicitly in the rationale — do not invent cost drivers.
3. Give a plain rationale for both the domain-risk read and the cost tier.

Write your findings (narrative, not the final schema) to state as
`app_impact_result`, covering: modified_services, domain_entity_changes,
api_boundary_impacts, cost_tier, cost_rationale.
""",
    output_key="app_impact_result",
)

code_eval_agent = LlmAgent(
    name="code_eval_agent",
    model=MODEL,
    description="Identifies specific file modifications, refactoring scope, and breaking changes.",
    instruction="""\
You are the Code Impact Evaluator. Using `code_context` and `dependency_map`
from session state, identify:

1. The specific repositories and files that would need to change.
2. The scope of refactoring implied (localized change vs. wide-reaching
   refactor touching many call sites).
3. Breaking changes: any change to a function signature, public API response
   shape, database column type/removal, or shared-library export that would
   break existing callers identified in `dependency_map.upstream_calling_services`
   or the `imported_by` results from static analysis.

Write your findings to state as `code_impact_result`, covering: repositories,
files, breaking_changes (be specific — name the function/endpoint/table and
why it breaks callers, or state clearly that no breaking changes were found).
""",
    output_key="code_impact_result",
)

testing_eval_agent = LlmAgent(
    name="testing_eval_agent",
    model=MODEL,
    description="Outlines regression risks, mock requirements, and integration test coverage.",
    instruction="""\
You are the Testing Impact Evaluator. Using `change_intent`, `dependency_map`,
and `code_impact_result` (if already available in state) plus `code_context`,
recommend a testing strategy:

1. integration_tests: which service-to-service integration paths need
   coverage given the upstream/downstream dependencies.
2. regression_tests: existing behavior at risk of silently breaking (call out
   any area with no visible existing test coverage in `code_context` — that
   is itself a risk signal).
3. contract_tests: needed if `api_contracts_modified` / breaking API changes
   are present, to pin the new contract shape for consumers.

Write your findings to state as `test_impact_result`, covering:
integration_tests, regression_tests, contract_tests (each a list of concrete
recommendations, not generic advice).
""",
    output_key="test_impact_result",
)

impact_risk_evaluators_parallel = ParallelAgent(
    name="impact_risk_evaluators_parallel",
    description="Runs application-architecture, code, and testing impact evaluations concurrently.",
    sub_agents=[app_arch_eval_agent, code_eval_agent, testing_eval_agent],
)
