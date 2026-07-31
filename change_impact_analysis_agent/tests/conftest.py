"""Test-local credential stubs.

The GitHub PAT is resolved eagerly at module import time (see
``tools/github_tools.py``), matching the production shape where the process
fails fast if no secret is configured. These env vars let the structural
test suite import the full pipeline without a live GCP project / Secret
Manager access — they must be set before ``change_impact_analysis_agent``
is imported anywhere, hence this lives in ``conftest.py`` (collected before
test modules).
"""

import os

os.environ.setdefault("ADK_LOCAL_SECRETS", "1")
os.environ.setdefault("GITHUB_TOKEN", "test-placeholder-token")
