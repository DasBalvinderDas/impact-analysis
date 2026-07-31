# Change Impact Analysis Agent

Multi-agent architecture assistant built on the Google Agent Development Kit
(ADK). Given a GitHub Issue (Change Request / Feature Request), it extracts
technical intent, cross-references architecture docs and the codebase, maps
upstream/downstream dependencies, evaluates architectural/code/testing risk
and FinOps cost impact, enforces human-in-the-loop governance on high-risk
changes, and publishes a styled PDF report to GCS with a summary posted back
on the issue.

Analysis-only pipeline — it never modifies code, so it's a single
`SequentialAgent` with two `ParallelAgent` steps and no retry loop.

## Pipeline

```
Issue #N
  -> intent_extractor_agent            (ChangeIntent -> change_intent)
  -> context_retrieval_parallel        (doc_search_agent + code_search_agent, concurrent)
  -> dependency_mapper_agent           (DependencyMap -> dependency_map)
  -> impact_risk_evaluators_parallel   (app_arch_eval + code_eval + testing_eval, concurrent)
  -> report_synthesizer_agent          (ImpactAssessment -> impact_assessment)
  -> publisher_governance_agent        (PDF -> GCS, issue comment, HITL governance)
```

`root_agent` is exported from `agent.py` per the Agent Runtime execution
contract.

## Project layout

```
change_impact_analysis_agent/
  agent.py                  # root_agent = SequentialAgent(...)
  models/schemas.py         # ChangeIntent, DependencyMap, ImpactAssessment (Pydantic)
  sub_agents/                # one module per pipeline stage
  tools/
    github_tools.py         # GitHub MCP toolset + deterministic HITL/publish REST calls
    docs_tools.py            # architecture-docs search (GCS or local docs/ folder)
    static_analysis.py       # import/call-graph parsing for dependency mapping
  utils/
    secrets.py               # GCP Secret Manager (git-agent-secret-key)
    telemetry.py              # OpenTelemetry + Cloud Logging
    pdf_export.py             # Markdown -> styled PDF (weasyprint) -> GCS
  tests/
    test_agent_structure.py
    eval/evalsets/change_impact.evalset.json
  deployment/deploy.py       # Vertex AI Agent Engine (AdkApp) deploy script
```

## Setup

```bash
pip install -r change_impact_analysis_agent/requirements.txt
cp change_impact_analysis_agent/.env.example change_impact_analysis_agent/.env
# edit .env: GOOGLE_CLOUD_PROJECT, REPORTS_GCS_BUCKET, ARCHITECTURE_DOCS_BUCKET, etc.
```

The GitHub PAT is read from Secret Manager **once, at process/import time**
(`tools/github_tools.py` fetches it at module load, mirroring production
behavior: fail fast if no valid secret is configured, rather than failing
deep inside a tool call mid-pipeline). For local development without a live
GCP project:

```bash
export ADK_LOCAL_SECRETS=1
export GITHUB_TOKEN=ghp_xxx
```

`tests/conftest.py` sets these automatically (with a placeholder token) so
the structural test suite (`tests/test_agent_structure.py`) can import and
construct the full pipeline without live credentials.

## Governance guardrails

- **HITL escalation**: the Publisher agent calls `publish_impact_report`,
  which deterministically applies the `impact:high-risk` label and tags
  `@tech-lead-review` in an issue comment whenever
  `impact_assessment.requires_human_approval` is `True` — this is a plain
  REST call in `tools/github_tools.py`, not left to LLM discretion.
- **FinOps cost tiering**: `app_arch_eval_agent` estimates Low (<$50/mo) /
  Medium ($50-$500/mo) / High (>$500/mo) monthly cost impact from newly
  required cloud resources.
- **Secrets**: the GitHub PAT is read from Secret Manager
  (`projects/{PROJECT_ID}/secrets/git-agent-secret-key/versions/latest` by
  default — override the secret name via `GITHUB_TOKEN_SECRET_ID`) via
  `utils/secrets.py`, never hardcoded.
- **Observability**: `utils/telemetry.py` wires OpenTelemetry tracing +
  Google Cloud Logging so every agent step / tool call is auditable.

## Running

```bash
adk run change_impact_analysis_agent
# or, with the dev UI:
adk web change_impact_analysis_agent
```

Trigger with a message like:

> Analyze change impact for issue_number 512 in repo acme-corp/billing-service.

## Evaluation

```bash
adk eval change_impact_analysis_agent \
  change_impact_analysis_agent/tests/eval/evalsets/change_impact.evalset.json \
  change_impact_analysis_agent/tests/eval/test_config.json \
  --print_detailed_results
```

`change_impact.evalset.json` covers a high-risk breaking-API-change scenario
(must trigger HITL governance) and a low-risk additive-change scenario (must
not).

Structural smoke tests (no live credentials required):

```bash
pytest change_impact_analysis_agent/tests/test_agent_structure.py
```

## Deployment (Vertex AI Agent Engine)

```bash
python -m change_impact_analysis_agent.deployment.deploy \
  --project your-gcp-project-id \
  --location us-central1 \
  --staging-bucket gs://your-staging-bucket
```

## Known compatibility note

This ADK release (2.6.0) marks `SequentialAgent`/`ParallelAgent` as
deprecated in favor of a forthcoming `Workflow` primitive, which cannot yet
be used as an `LlmAgent` sub-agent. Per the design doc's architecture
(Section 3), this implementation intentionally uses `SequentialAgent` /
`ParallelAgent`, which remain fully functional in this release.
