"""GCP Secret Manager helper.

Retrieves runtime secrets (e.g. the GitHub access token used by the GitHub
MCP toolset) from Secret Manager instead of plaintext environment variables,
per the security guardrail in the design doc.
"""

from __future__ import annotations

import functools
import os


class SecretResolutionError(RuntimeError):
    """Raised when a secret cannot be resolved from Secret Manager or env fallback."""


@functools.lru_cache(maxsize=32)
def get_secret(secret_id: str, project_id: str | None = None, version: str = "latest") -> str:
    """Fetch a secret payload from GCP Secret Manager.

    Resolves ``projects/{project_id}/secrets/{secret_id}/versions/{version}``.
    Falls back to an environment variable named ``{SECRET_ID}`` (upper-cased,
    hyphens -> underscores) when ``ADK_LOCAL_SECRETS=1`` is set, so the agent
    can be exercised locally without a live GCP project.

    Results are cached in-process (``lru_cache``) since Secret Manager reads
    are billed per-access and secrets are effectively static for the process
    lifetime.
    """
    project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")

    if os.environ.get("ADK_LOCAL_SECRETS") == "1":
        env_name = secret_id.upper().replace("-", "_")
        value = os.environ.get(env_name)
        if value:
            return value
        raise SecretResolutionError(
            f"ADK_LOCAL_SECRETS=1 but no {env_name} environment variable is set."
        )

    if not project_id:
        raise SecretResolutionError(
            "GOOGLE_CLOUD_PROJECT is not set and ADK_LOCAL_SECRETS is not enabled; "
            "cannot resolve secret '%s'." % secret_id
        )

    try:
        from google.cloud import secretmanager
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise SecretResolutionError(
            "google-cloud-secret-manager is not installed. Run "
            "`pip install google-cloud-secret-manager` or set ADK_LOCAL_SECRETS=1 for local dev."
        ) from exc

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
    try:
        response = client.access_secret_version(request={"name": name})
    except Exception as exc:  # noqa: BLE001 - surface as SecretResolutionError
        raise SecretResolutionError(f"Failed to access secret '{name}': {exc}") from exc

    return response.payload.data.decode("UTF-8")


def get_github_token(project_id: str | None = None) -> str:
    """Convenience wrapper for the GitHub MCP access token secret."""
    return get_secret("github-token", project_id=project_id)
