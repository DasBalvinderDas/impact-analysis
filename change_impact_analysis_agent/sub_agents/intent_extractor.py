"""Intent Extractor Agent.

Reads the triggering GitHub Issue (CR / Feature Request) via the GitHub MCP
toolset and extracts structured technical intent into session state under
``change_intent``.
"""

from __future__ import annotations

import os

from google.adk.agents import LlmAgent

from ..models.schemas import ChangeIntent
from ..tools.github_tools import build_intake_toolset

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

_INSTRUCTION = """\
You are the Intent Extractor Agent in a Change Impact Analysis pipeline.

Your job:
1. Read the GitHub issue referenced by `issue_number` in the user's message
   (or in session state) using the issue-read tool available to you
   (e.g. `get_issue` / `issue_read`).
2. Extract the underlying technical intent of the Change Request / Feature
   Request: what is being asked for, which modules/services/features the
   requester believes are involved, any explicit data model or schema
   changes mentioned, and any stated acceptance criteria.
3. Do not guess at implementation details not present in the ticket — if the
   ticket is vague about which modules are affected, leave `target_modules`
   based only on what is stated or strongly implied by the ticket title/body/
   labels, and let downstream agents (code/doc search) do the discovery.

Output strictly as the `ChangeIntent` schema.
"""

intent_extractor_agent = LlmAgent(
    name="intent_extractor_agent",
    model=MODEL,
    description="Extracts structured technical intent from the triggering GitHub issue/CR.",
    instruction=_INSTRUCTION,
    tools=[build_intake_toolset()],
    output_schema=ChangeIntent,
    output_key="change_intent",
)
