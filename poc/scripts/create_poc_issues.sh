#!/usr/bin/env bash
set -euo pipefail

repository="${1:-${POC_TARGET_REPO:-}}"
source_ref="${2:-${POC_SOURCE_REF:-main}}"
app_root="${3:-${POC_APP_ROOT:-poc/target_app}}"
template_root="${POC_TEMPLATE_ROOT:-https://raw.githubusercontent.com/DasBalvinderDas/impact-analysis/feat/poc-test-data/poc/issues}"

if [[ -z "${repository}" ]]; then
  echo "Usage: $0 OWNER/REPO [SOURCE_REF] [APP_ROOT]" >&2
  echo "Or set POC_TARGET_REPO, POC_SOURCE_REF, and POC_APP_ROOT." >&2
  exit 2
fi

if [[ ! "${repository}" =~ ^[^/[:space:]]+/[^/[:space:]]+$ ]]; then
  echo "Repository must use the OWNER/REPO format: ${repository}" >&2
  exit 2
fi

for command_name in curl gh; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Required command '${command_name}' was not found." >&2
    exit 2
  fi
done

if [[ -z "${GH_TOKEN:-}" && -z "${GITHUB_TOKEN:-}" ]]; then
  echo "Set GH_TOKEN or GITHUB_TOKEN to your enterprise GitHub credential." >&2
  exit 2
fi

gh api user >/dev/null
gh repo view "${repository}" >/dev/null

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/impact-analysis-issues.XXXXXX")"
trap 'rm -rf "${work_dir}"' EXIT

gh label create "impact:high-risk" --repo "${repository}" \
  --color B60205 --description "Requires technical-lead impact review" --force

create_issue() {
  local title="$1"
  local template_name="$2"
  local template_file="${work_dir}/${template_name}"
  local body_file="${work_dir}/body-${template_name}"
  local existing_url

  existing_url="$(gh issue list --repo "${repository}" --state all --limit 1000 \
    --json title,url --jq ".[] | select(.title == \"${title}\") | .url" | head -n 1)"
  if [[ -n "${existing_url}" ]]; then
    echo "Existing issue reused: ${existing_url}"
    return
  fi

  curl -fsSL "${template_root}/${template_name}" -o "${template_file}"
  {
    echo "## POC source location"
    echo
    echo "Analyze code from branch \`${source_ref}\` in repository \`${repository}\`."
    echo "The disposable target application starts at \`${app_root}/\`."
    echo "When fetching files, use Git ref \`${source_ref}\` rather than assuming another branch."
    echo
    echo "---"
    echo
    cat "${template_file}"
  } >"${body_file}"

  gh issue create --repo "${repository}" --title "${title}" --body-file "${body_file}"
}

create_issue \
  "[POC Low risk] Add preferred locale to notification preferences" \
  "low-risk-preferred-locale.md"
create_issue \
  "[POC Medium risk] Add asynchronous invoice exports" \
  "medium-risk-async-export.md"
create_issue \
  "[POC High risk] Replace legacy_customer_id with customer_ref" \
  "high-risk-customer-ref.md"

echo
echo "POC issues are ready in https://github.com/${repository}/issues"
echo "Run your agent with:"
echo "Analyze change impact for issue_number <NUMBER> in repo ${repository}. Use branch ${source_ref}."
