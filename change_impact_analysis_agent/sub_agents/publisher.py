"""Publisher & Governance Agent.

Renders the final `impact_assessment` (+ upstream context) into a Markdown
report, converts it to a styled PDF, uploads it to GCS, posts the summary +
PDF link as a GitHub issue comment, and — deterministically, not left to LLM
discretion — applies the `impact:high-risk` HITL label and tech-lead
mention whenever `impact_assessment.requires_human_approval` is True.
"""

from __future__ import annotations

import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, ToolContext

from ..tools.github_tools import (
    apply_high_risk_governance,
    post_impact_summary_comment,
)
from ..utils.pdf_export import publish_report_pdf
from ..utils.telemetry import audit_event, get_logger

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")


def _render_markdown_report(tool_context: ToolContext) -> str:
    """Build the Markdown report body from `impact_assessment` in session state."""
    ia = tool_context.state.get("impact_assessment") or {}
    intent = tool_context.state.get("change_intent") or {}
    dep = tool_context.state.get("dependency_map") or {}

    def _bullets(items):
        items = items or []
        return "\n".join(f"- {item}" for item in items) or "- None identified"

    app_impact = ia.get("application_impact", {}) or {}
    code_impact = ia.get("code_impact", {}) or {}
    finops = ia.get("finops_cost_impact", {}) or {}
    testing = ia.get("testing_recommendations", {}) or {}

    lines = [
        f"# Change Impact Assessment — Issue #{intent.get('issue_number', 'N/A')}",
        "",
        f"**Risk Level:** {ia.get('risk_level', 'Unknown')}  ",
        f"**Requires Human Approval:** {ia.get('requires_human_approval', False)}  ",
        f"**FinOps Cost Tier:** {finops.get('cost_tier', 'Unknown')}",
        "",
        "## Summary",
        ia.get("summary", ""),
        "",
        "## Blast Radius",
        ia.get("blast_radius") or "Not specified.",
        "",
        "## Application Impact",
        "**Modified services:**", _bullets(app_impact.get("modified_services")),
        "**Domain entity changes:**", _bullets(app_impact.get("domain_entity_changes")),
        "**API boundary impacts:**", _bullets(app_impact.get("api_boundary_impacts")),
        "",
        "## Code Impact",
        "**Repositories:**", _bullets(code_impact.get("repositories")),
        "**Files:**", _bullets(code_impact.get("files")),
        "**Breaking changes:**", _bullets(code_impact.get("breaking_changes")),
        "",
        "## Dependency Map",
        "**Upstream calling services:**", _bullets(dep.get("upstream_calling_services")),
        "**Downstream dependencies:**", _bullets(dep.get("downstream_dependencies")),
        "**Database tables affected:**", _bullets(dep.get("database_tables_affected")),
        "**API contracts modified:**", _bullets(dep.get("api_contracts_modified")),
        "",
        "## FinOps Cost Impact",
        f"**Tier:** {finops.get('cost_tier', 'Unknown')}",
        "",
        finops.get("rationale", ""),
        "",
        "## Risk Rationale",
        ia.get("risk_rationale", ""),
        "",
        "## Testing Recommendations",
        "**Integration tests:**", _bullets(testing.get("integration_tests")),
        "**Regression tests:**", _bullets(testing.get("regression_tests")),
        "**Contract tests:**", _bullets(testing.get("contract_tests")),
        "",
        "## Open Questions",
        _bullets(ia.get("open_questions")),
    ]
    return "\n".join(lines)


def publish_impact_report(
    repo_owner: str,
    repo_name: str,
    tool_context: ToolContext,
) -> dict:
    """Render, PDF-export, upload, and post the Change Impact Assessment; enforce HITL governance.

    Args:
        repo_owner: GitHub organization/user that owns the repository.
        repo_name: GitHub repository name.
        tool_context: Injected automatically by the ADK runtime; used to read
            `impact_assessment` / `change_intent` from session state.

    Returns:
        A dict summarizing what was published: pdf_url, comment posted, and
        whether HITL governance (high-risk label + tech-lead mention) fired.
    """
    logger = get_logger()
    ia = tool_context.state.get("impact_assessment") or {}
    intent = tool_context.state.get("change_intent") or {}
    issue_number = intent.get("issue_number")
    if issue_number is None:
        raise ValueError("change_intent.issue_number missing from session state; cannot publish.")

    markdown_report = _render_markdown_report(tool_context)
    pdf_url = publish_report_pdf(
        markdown_report,
        issue_number=issue_number,
        title=f"Change Impact Assessment — Issue #{issue_number}",
    )
    audit_event("report_published", issue_number=issue_number, pdf_url=pdf_url)

    comment = post_impact_summary_comment(
        repo_owner=repo_owner,
        repo_name=repo_name,
        issue_number=issue_number,
        summary_markdown=ia.get("summary", ""),
        pdf_url=pdf_url,
    )

    governance_result = None
    if ia.get("requires_human_approval"):
        governance_result = apply_high_risk_governance(
            repo_owner=repo_owner,
            repo_name=repo_name,
            issue_number=issue_number,
            pdf_url=pdf_url,
            risk_rationale=ia.get("risk_rationale", ""),
        )
        logger.info("HITL governance triggered for issue #%s", issue_number)

    return {
        "pdf_url": pdf_url,
        "comment_id": comment.get("id"),
        "hitl_governance_applied": governance_result is not None,
        "governance_result": governance_result,
    }


publish_impact_report_tool = FunctionTool(func=publish_impact_report)

_INSTRUCTION = """\
You are the Publisher & Governance Agent, the final step of the Change
Impact Analysis pipeline. `impact_assessment` is already finalized in
session state.

Call `publish_impact_report` exactly once, passing `repo_owner` and
`repo_name` for the repository the triggering issue lives in (read these
from the user's message or session state — if not explicitly given, use the
repository the triggering issue/PR belongs to). This single tool call:
- renders the assessment to Markdown and a styled PDF,
- uploads the PDF to GCS,
- posts the summary + PDF link as an issue comment,
- and — automatically, only when `impact_assessment.requires_human_approval`
  is True — applies the `impact:high-risk` label and requests tech-lead
  sign-off. You do not need to (and should not try to) apply the label or
  mention the tech lead yourself; the tool enforces that governance step.

After the tool call, reply with a short confirmation: the PDF URL, whether
the comment was posted, and whether HITL governance was triggered.
"""

publisher_governance_agent = LlmAgent(
    name="publisher_governance_agent",
    model=MODEL,
    description="Publishes the impact report (PDF + GitHub comment) and enforces HITL governance for high-risk changes.",
    instruction=_INSTRUCTION,
    tools=[publish_impact_report_tool],
)
