#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
  echo "Usage: $0 OWNER/REPO LOW_ISSUE MEDIUM_ISSUE HIGH_ISSUE REPORTS_GCS_BUCKET" >&2
  exit 2
fi

repository="$1"
low_issue="$2"
medium_issue="$3"
high_issue="$4"
reports_bucket="${5#gs://}"

for command_name in gh gcloud; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Required command '${command_name}' was not found." >&2
    exit 2
  fi
done

for issue_number in "${low_issue}" "${medium_issue}" "${high_issue}"; do
  comment_count="$(gh api "repos/${repository}/issues/${issue_number}/comments" \
    --jq '[.[] | select(.body | contains("Change Impact Assessment"))] | length')"
  if [[ "${comment_count}" -lt 1 ]]; then
    echo "Issue #${issue_number}: missing Change Impact Assessment comment." >&2
    exit 1
  fi

  gcloud storage ls "gs://${reports_bucket}/impact-reports/${issue_number}.pdf" >/dev/null
  echo "Issue #${issue_number}: comment and PDF found."
done

high_labels="$(gh issue view "${high_issue}" --repo "${repository}" --json labels \
  --jq '.labels[].name')"
if ! grep -Fxq "impact:high-risk" <<<"${high_labels}"; then
  echo "Issue #${high_issue}: impact:high-risk label is missing." >&2
  exit 1
fi

for issue_number in "${low_issue}" "${medium_issue}"; do
  labels="$(gh issue view "${issue_number}" --repo "${repository}" --json labels \
    --jq '.labels[].name')"
  if grep -Fxq "impact:high-risk" <<<"${labels}"; then
    echo "Issue #${issue_number}: unexpected impact:high-risk label." >&2
    exit 1
  fi
done

high_mentions="$(gh api "repos/${repository}/issues/${high_issue}/comments" \
  --jq '[.[] | select(.body | contains("@tech-lead-review"))] | length')"
if [[ "${high_mentions}" -lt 1 ]]; then
  echo "Issue #${high_issue}: missing @tech-lead-review governance comment." >&2
  exit 1
fi

echo "POC validation passed: all comments and PDFs exist, and governance labels are correct."
