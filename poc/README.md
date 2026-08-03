# Change Impact Analysis POC

This directory contains a complete, disposable test target for the Change
Impact Analysis Agent. The checked-in `target_app/` is the canonical seed; the
setup script publishes a copy as a separate GitHub repository and creates Low,
Medium, and High risk issues against it.

## What is included

- Layered Python billing code: API, services, models, repository, client, and
  upstream reporting consumer.
- SQL schema, OpenAPI v1 contract, architecture/API/data-model documents, and
  deterministic tests.
- Three issue bodies with explicit expected risk, cost, compatibility, and
  governance outcomes.
- GitHub setup and end-to-end validation scripts.

## Prerequisites

1. Python 3.10 or newer.
2. GitHub CLI authenticated with permission to create repositories, issues,
   labels, and comments (`gh auth status`).
3. Google Cloud CLI authenticated to the POC project.
4. A GCS bucket for PDFs and credentials that can create objects in it.
5. A GitHub PAT usable by the configured GitHub MCP server. For a public target
   repository, grant only the repository metadata/content read and issue write
   permissions needed by the agent.

Copy `poc/.env.poc.example` to `change_impact_analysis_agent/.env`, replace all
placeholder values, and use an absolute `ARCHITECTURE_DOCS_PATH` pointing to
`poc/target_app/docs`. Do not commit the resulting `.env` file.

Create the report bucket if needed:

```bash
gcloud storage buckets create gs://YOUR_GLOBALLY_UNIQUE_BUCKET \
  --project YOUR_PROJECT_ID --location us-central1 --uniform-bucket-level-access
```

## 1. Validate the seed application

```bash
cd poc/target_app
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
pytest
ruff check .
```

## 2. Create the disposable GitHub target

### One-command setup

You do not need to clone or check out the impact-analysis repository first.
Run the hosted bootstrap script directly:

```bash
curl -fsSL \
  https://raw.githubusercontent.com/DasBalvinderDas/impact-analysis/feat/poc-test-data/poc/scripts/bootstrap_poc.sh \
  | bash
```

The bootstrap script downloads this repository at `feat/poc-test-data`, then
runs the complete setup. It passes `POC_REPO_NAME` and
`POC_REPO_VISIBILITY` through to the setup script, so customization works with
the direct command:

```bash
curl -fsSL \
  https://raw.githubusercontent.com/DasBalvinderDas/impact-analysis/feat/poc-test-data/poc/scripts/bootstrap_poc.sh \
  | POC_REPO_NAME=my-impact-poc POC_REPO_VISIBILITY=private bash
```

The only local prerequisites are `git`, the GitHub CLI (`gh`), and an
authenticated GitHub CLI session (`gh auth login`).

### From an existing checkout

From the impact-analysis repository root:

```bash
./poc/scripts/setup_poc_repo.sh
```

The default repository is public and named `impact-analysis-poc-target` under
the authenticated GitHub user. Override either setting when necessary:

```bash
POC_REPO_NAME=my-impact-poc POC_REPO_VISIBILITY=private \
  ./poc/scripts/setup_poc_repo.sh
```

The script refuses to overwrite an existing repository. It prints the three
created issue URLs; retain their issue numbers for execution and validation.

## 3. Run the agent

Load the completed environment file using your preferred environment loader,
then start ADK from the impact-analysis repository root:

```bash
set -a
. change_impact_analysis_agent/.env
set +a
adk run change_impact_analysis_agent
```

Submit one prompt per issue:

```text
Analyze change impact for issue_number <LOW_NUMBER> in repo OWNER/REPO.
Analyze change impact for issue_number <MEDIUM_NUMBER> in repo OWNER/REPO.
Analyze change impact for issue_number <HIGH_NUMBER> in repo OWNER/REPO.
```

Run the scenarios separately because each execution publishes a comment and
overwrites `impact-reports/<issue_number>.pdf` for that issue.

## 4. Expected results

| Scenario | Risk | FinOps | Breaking | Human approval | Governance |
|---|---|---|---|---|---|
| Preferred locale | Low | Low (`<$50/mo`) | No | No | No high-risk label |
| Async export | Medium | Medium (`$50-$500/mo`) | No | Normally no | No high-risk label |
| Customer reference rename | High | Low unless migration resources are proposed | Yes | Yes | `impact:high-risk` plus `@tech-lead-review` |

Every issue should receive a `Change Impact Assessment` summary comment with a
PDF link, and every report should exist at
`gs://REPORTS_GCS_BUCKET/impact-reports/<issue_number>.pdf`.

## 5. Validate GitHub and GCS outputs

```bash
./poc/scripts/validate_poc.sh \
  OWNER/REPO LOW_NUMBER MEDIUM_NUMBER HIGH_NUMBER REPORTS_GCS_BUCKET
```

For manual inspection:

```bash
gh issue view HIGH_NUMBER --repo OWNER/REPO --comments
gh issue view HIGH_NUMBER --repo OWNER/REPO --json labels
gcloud storage ls -l gs://REPORTS_GCS_BUCKET/impact-reports/
gcloud storage cp gs://REPORTS_GCS_BUCKET/impact-reports/HIGH_NUMBER.pdf /tmp/high-risk.pdf
```

Delete the disposable target after testing with
`gh repo delete OWNER/REPO`; this is intentionally manual because deletion is
irreversible and should never be performed by the setup or validation scripts.
