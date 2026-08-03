#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
poc_dir="$(cd "${script_dir}/.." && pwd)"
seed_dir="${poc_dir}/target_app"
repo_name="${POC_REPO_NAME:-impact-analysis-poc-target}"
visibility="${POC_REPO_VISIBILITY:-public}"

if [[ "${visibility}" != "public" && "${visibility}" != "private" ]]; then
  echo "POC_REPO_VISIBILITY must be 'public' or 'private'." >&2
  exit 2
fi

for command_name in git gh; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Required command '${command_name}' was not found." >&2
    exit 2
  fi
done

gh auth status >/dev/null
owner="$(gh api user --jq .login)"
repository="${owner}/${repo_name}"

if gh repo view "${repository}" >/dev/null 2>&1; then
  echo "Repository ${repository} already exists; choose another POC_REPO_NAME." >&2
  exit 1
fi

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/impact-analysis-poc.XXXXXX")"
trap 'rm -rf "${work_dir}"' EXIT
cp -R "${seed_dir}/." "${work_dir}/"

git -C "${work_dir}" init -b main
git -C "${work_dir}" add .
git -C "${work_dir}" -c user.name="Impact Analysis POC" \
  -c user.email="impact-analysis-poc@example.invalid" \
  commit -m "Add disposable billing application for impact-analysis POC"

gh repo create "${repository}" "--${visibility}" \
  --description "Disposable target repository for the Change Impact Analysis Agent POC" \
  --source "${work_dir}" --remote origin --push

gh label create "impact:high-risk" --repo "${repository}" \
  --color B60205 --description "Requires technical-lead impact review" --force

low_url="$(gh issue create --repo "${repository}" \
  --title "[Low risk] Add preferred locale to notification preferences" \
  --body-file "${poc_dir}/issues/low-risk-preferred-locale.md")"
medium_url="$(gh issue create --repo "${repository}" \
  --title "[Medium risk] Add asynchronous invoice exports" \
  --body-file "${poc_dir}/issues/medium-risk-async-export.md")"
high_url="$(gh issue create --repo "${repository}" \
  --title "[High risk] Replace legacy_customer_id with customer_ref" \
  --body-file "${poc_dir}/issues/high-risk-customer-ref.md")"

echo "POC repository: https://github.com/${repository}"
echo "Low-risk issue: ${low_url}"
echo "Medium-risk issue: ${medium_url}"
echo "High-risk issue: ${high_url}"
echo
echo "Run the agent once per issue using:"
echo "Analyze change impact for issue_number <NUMBER> in repo ${repository}."
