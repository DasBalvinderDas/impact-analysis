#!/usr/bin/env bash
set -euo pipefail

source_repository="${IMPACT_ANALYSIS_REPOSITORY:-https://github.com/DasBalvinderDas/impact-analysis.git}"
source_ref="${IMPACT_ANALYSIS_REF:-feat/poc-test-data}"

for command_name in git gh; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Required command '${command_name}' was not found." >&2
    exit 2
  fi
done

gh auth status >/dev/null

bootstrap_dir="$(mktemp -d "${TMPDIR:-/tmp}/impact-analysis-bootstrap.XXXXXX")"
trap 'rm -rf "${bootstrap_dir}"' EXIT

echo "Downloading POC setup from ${source_repository} at ${source_ref}..."
git clone --depth 1 --branch "${source_ref}" "${source_repository}" \
  "${bootstrap_dir}/impact-analysis"

echo "Creating the disposable target repository and test issues..."
bash "${bootstrap_dir}/impact-analysis/poc/scripts/setup_poc_repo.sh"
