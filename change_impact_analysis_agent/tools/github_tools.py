"""GitHub MCP Server wiring + deterministic HITL governance actions.

Two integration paths are provided:

1. ``build_github_mcp_toolset`` — connects the agents to the GitHub MCP
   Server (stdio or Streamable HTTP) so LlmAgents can call ``get_issue`` /
   ``issue_read``, ``search_code``, ``get_file_contents``,
   ``add_issue_comment`` / ``create_issue_comment``, and issue-label tools
   directly, as the design calls for in section 6 ("Ticket system
   read/write tool", "GitHub code search tool").

2. ``apply_high_risk_governance`` — a plain REST helper (not routed through
   the LLM) that deterministically applies the ``impact:high-risk`` label
   and tags ``@tech-lead-review`` whenever
   ``ImpactAssessment.requires_human_approval`` is True. HITL enforcement is
   a compliance guardrail, so it must not depend on the LLM remembering to
   call the right tool — the Publisher agent's callback invokes this
   directly against session state.
"""

from __future__ import annotations

import os
from typing import Optional

import requests

from ..utils.secrets import get_github_token
from ..utils.telemetry import audit_event, get_logger

GITHUB_API_ROOT = "https://api.github.com"
HIGH_RISK_LABEL = "impact:high-risk"
TECH_LEAD_MENTION = "@tech-lead-review"


def _resolve_token() -> str:
    """Prefer Secret Manager; fall back to GITHUB_TOKEN env var for local dev."""
    try:
        return get_github_token()
    except Exception:  # noqa: BLE001
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        if token:
            return token
        raise


def _lazy_auth_header(_readonly_context=None) -> dict:
    """Resolved at MCP-session-connect time, not at toolset-construction time.

    Keeps module import (and therefore agent construction / eval-set loading)
    working even when Secret Manager / GITHUB_TOKEN aren't configured yet —
    the token is only required once an agent actually calls a GitHub tool.
    """
    return {"Authorization": f"Bearer {_resolve_token()}"}


def build_github_mcp_toolset(tool_filter: Optional[list[str]] = None):
    """Build an McpToolset connected to the GitHub MCP server.

    Transport is selected via ``GITHUB_MCP_TRANSPORT`` (``http`` default, or
    ``stdio`` to launch the local ``github-mcp-server`` binary). The auth
    token is resolved from GCP Secret Manager (``github-token``) per the
    security guardrail, with an env-var fallback for local development. For
    the default HTTP transport, resolution is deferred to session-connect
    time via ``header_provider`` so importing this module never requires
    credentials to be present.
    """
    from google.adk.tools.mcp_tool.mcp_session_manager import (
        StdioConnectionParams,
        StreamableHTTPConnectionParams,
    )
    from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
    from mcp import StdioServerParameters

    transport = os.environ.get("GITHUB_MCP_TRANSPORT", "http")

    if transport == "stdio":
        # Stdio env vars must be fixed at process-launch time, so the token
        # is resolved eagerly here; stdio is an opt-in transport (not the
        # default), so this does not affect ordinary module import.
        connection_params = StdioConnectionParams(
            server_params=StdioServerParameters(
                command="docker",
                args=[
                    "run", "-i", "--rm",
                    "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
                    "ghcr.io/github/github-mcp-server",
                ],
                env={"GITHUB_PERSONAL_ACCESS_TOKEN": _resolve_token()},
            ),
            timeout=30,
        )
        return McpToolset(connection_params=connection_params, tool_filter=tool_filter)

    connection_params = StreamableHTTPConnectionParams(
        url=os.environ.get("GITHUB_MCP_URL", "https://api.github.com/mcp"),
        timeout=30,
    )
    return McpToolset(
        connection_params=connection_params,
        tool_filter=tool_filter,
        header_provider=_lazy_auth_header,
    )


def build_intake_toolset():
    """Read-only tools for the Intent Extractor Agent: reading the triggering issue."""
    return build_github_mcp_toolset(
        tool_filter=["get_issue", "issue_read", "list_issue_fields"]
    )


def build_code_search_toolset():
    """Read-only tools for the Context Retrieval / Dependency Mapper agents."""
    return build_github_mcp_toolset(
        tool_filter=["search_code", "get_file_contents", "list_commits"]
    )


def build_publisher_toolset():
    """Write tools for the Publisher & Governance Agent."""
    return build_github_mcp_toolset(
        tool_filter=[
            "create_issue_comment",
            "add_issue_comment",
            "issue_write",
            "get_label",
        ]
    )


def apply_high_risk_governance(
    repo_owner: str,
    repo_name: str,
    issue_number: int,
    pdf_url: str,
    risk_rationale: str,
) -> dict:
    """Deterministically apply the high-risk HITL label + review request.

    Called from the Publisher agent's callback (not left to LLM discretion)
    whenever ``requires_human_approval`` is True, so the guardrail always
    fires regardless of what the model decided to do with its tools.
    """
    logger = get_logger()
    token = _resolve_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    label_resp = requests.post(
        f"{GITHUB_API_ROOT}/repos/{repo_owner}/{repo_name}/issues/{issue_number}/labels",
        headers=headers,
        json={"labels": [HIGH_RISK_LABEL]},
        timeout=30,
    )
    label_resp.raise_for_status()

    comment_body = (
        f"### \U0001f6a8 High-Risk Change Detected\n\n"
        f"This change has been flagged **High Risk** by the Change Impact "
        f"Analysis Agent and requires manual sign-off before development "
        f"starts.\n\n**Rationale:** {risk_rationale}\n\n"
        f"Full report: {pdf_url}\n\n"
        f"{TECH_LEAD_MENTION} please review and approve before implementation begins."
    )
    comment_resp = requests.post(
        f"{GITHUB_API_ROOT}/repos/{repo_owner}/{repo_name}/issues/{issue_number}/comments",
        headers=headers,
        json={"body": comment_body},
        timeout=30,
    )
    comment_resp.raise_for_status()

    audit_event(
        "hitl_governance_applied",
        repo=f"{repo_owner}/{repo_name}",
        issue_number=issue_number,
        label=HIGH_RISK_LABEL,
    )
    logger.info(
        "Applied '%s' label and tech-lead review request to %s/%s#%d",
        HIGH_RISK_LABEL, repo_owner, repo_name, issue_number,
    )
    return {"label_applied": HIGH_RISK_LABEL, "comment_id": comment_resp.json().get("id")}


def post_impact_summary_comment(
    repo_owner: str,
    repo_name: str,
    issue_number: int,
    summary_markdown: str,
    pdf_url: str,
) -> dict:
    """Post the final impact summary + PDF link as an issue comment."""
    logger = get_logger()
    token = _resolve_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    body = (
        f"## \U0001f4cb Change Impact Assessment\n\n{summary_markdown}\n\n"
        f"---\n\U0001f4c4 [Download full report (PDF)]({pdf_url})\n\n"
        f"_Generated automatically by the Change Impact Analysis Agent._"
    )
    resp = requests.post(
        f"{GITHUB_API_ROOT}/repos/{repo_owner}/{repo_name}/issues/{issue_number}/comments",
        headers=headers,
        json={"body": body},
        timeout=30,
    )
    resp.raise_for_status()
    audit_event("impact_summary_posted", repo=f"{repo_owner}/{repo_name}", issue_number=issue_number)
    logger.info("Posted impact summary comment to %s/%s#%d", repo_owner, repo_name, issue_number)
    return resp.json()
