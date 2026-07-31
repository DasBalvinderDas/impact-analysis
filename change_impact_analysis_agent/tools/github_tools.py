"""GitHub MCP Server wiring + deterministic HITL governance actions.

Two integration paths are provided:

1. ``build_github_mcp_toolset`` — connects the agents to the GitHub MCP
   server (Copilot's hosted Streamable HTTP endpoint by default, or a local
   stdio server) so LlmAgents can call ``get_issue``, ``search_code``,
   ``get_file_contents``, ``create_issue_comment``, ``create_branch``,
   ``push_files``, ``create_pull_request``, etc. directly, per the design's
   "Ticket system read/write tool" and "GitHub code search tool"
   requirements (Section 6).

   The GitHub PAT is read from GCP Secret Manager **once at module import**
   (mirroring the reference implementation) rather than resolved lazily per
   request — this is the intended production shape: the process either has
   a valid secret at startup or fails fast. Set ``ADK_LOCAL_SECRETS=1`` +
   ``GITHUB_TOKEN=...`` to run/import this module without a live GCP project
   (used by the test suite; see ``tests/conftest.py``).

2. ``apply_high_risk_governance`` — a plain REST helper (not routed through
   the LLM) that deterministically applies the ``impact:high-risk`` label
   and tags ``@tech-lead-review`` whenever
   ``ImpactAssessment.requires_human_approval`` is True. HITL enforcement is
   a compliance guardrail, so it must not depend on the LLM remembering to
   call the right tool — the Publisher agent's tool invokes this directly
   against session state.
"""

from __future__ import annotations

import os
from typing import Optional

import requests

from ..utils.secrets import get_github_token
from ..utils.telemetry import audit_event, get_logger

# --- Version-tolerant MCP imports -------------------------------------------------
# ADK renamed MCPToolset -> McpToolset and StreamableHTTPServerParams ->
# StreamableHTTPConnectionParams; both old names remain as aliases in recent
# releases but that isn't guaranteed across versions, so prefer the current
# names and fall back to the older ones.
try:
    from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
except ImportError:  # pragma: no cover - older ADK releases
    from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset as McpToolset

try:
    from google.adk.tools.mcp_tool.mcp_session_manager import (
        StreamableHTTPConnectionParams as StreamableHTTPServerParams,
    )
except ImportError:  # pragma: no cover - older ADK releases
    from google.adk.tools.mcp_tool.mcp_session_manager import (
        StreamableHTTPServerParams,
    )
# -----------------------------------------------------------------------------------

GITHUB_API_ROOT = "https://api.github.com"
HIGH_RISK_LABEL = "impact:high-risk"
TECH_LEAD_MENTION = "@tech-lead-review"

# GitHub's hosted Copilot coding-agent MCP endpoint (Streamable HTTP). Override
# with GITHUB_MCP_URL to point at a self-hosted github-mcp-server instead.
DEFAULT_GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"


def _resolve_token() -> str:
    """Read the GitHub PAT from Secret Manager; fall back to an env var for local dev.

    ``get_github_token`` (``utils/secrets.py``) reads
    ``projects/{PROJECT_ID}/secrets/github-token/versions/latest`` and is
    process-lifetime cached, so repeated calls here are cheap — this fetches
    once regardless of how many toolsets/agents call it.
    """
    try:
        return get_github_token()
    except Exception:  # noqa: BLE001
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        if token:
            return token
        raise


# Fetched once at module load, mirroring the reference implementation: the
# process either has a valid GitHub PAT at startup, or fails fast rather than
# failing deep inside a tool call mid-pipeline.
GITHUB_PAT = _resolve_token()


def build_github_mcp_toolset(tool_filter: Optional[list[str]] = None) -> McpToolset:
    """Build an McpToolset connected to the GitHub MCP server.

    Transport is selected via ``GITHUB_MCP_TRANSPORT`` (``http`` default —
    GitHub's hosted Copilot MCP endpoint — or ``stdio`` to launch the local
    ``github-mcp-server`` container). Both paths use the ``GITHUB_PAT``
    resolved at module import.
    """
    transport = os.environ.get("GITHUB_MCP_TRANSPORT", "http")

    if transport == "stdio":
        from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
        from mcp import StdioServerParameters

        connection_params = StdioConnectionParams(
            server_params=StdioServerParameters(
                command="docker",
                args=[
                    "run", "-i", "--rm",
                    "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
                    "ghcr.io/github/github-mcp-server",
                ],
                env={"GITHUB_PERSONAL_ACCESS_TOKEN": GITHUB_PAT},
            ),
            timeout=30,
        )
        return McpToolset(connection_params=connection_params, tool_filter=tool_filter)

    connection_params = StreamableHTTPServerParams(
        url=os.environ.get("GITHUB_MCP_URL", DEFAULT_GITHUB_MCP_URL),
        headers={"Authorization": f"Bearer {GITHUB_PAT}"},
    )
    return McpToolset(connection_params=connection_params, tool_filter=tool_filter)


def build_intake_toolset() -> McpToolset:
    """Read-only tools for the Intent Extractor Agent: reading the triggering issue."""
    return build_github_mcp_toolset(
        tool_filter=["get_issue", "list_issues", "get_repository"]
    )


def build_code_search_toolset() -> McpToolset:
    """Read-only tools for the Context Retrieval / Dependency Mapper agents."""
    return build_github_mcp_toolset(
        tool_filter=["search_code", "get_file_contents", "get_pull_request", "list_pull_requests"]
    )


def build_publisher_toolset() -> McpToolset:
    """Write tools for the Publisher & Governance Agent."""
    return build_github_mcp_toolset(
        tool_filter=[
            "create_issue_comment",
            "create_branch",
            "create_or_update_file",
            "push_files",
            "create_pull_request",
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

    Called from the Publisher agent's tool (not left to LLM discretion)
    whenever ``requires_human_approval`` is True, so the guardrail always
    fires regardless of what the model decided to do with its tools.
    """
    logger = get_logger()
    headers = {
        "Authorization": f"Bearer {GITHUB_PAT}",
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
    headers = {
        "Authorization": f"Bearer {GITHUB_PAT}",
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
