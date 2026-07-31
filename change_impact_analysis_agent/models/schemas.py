"""Pydantic state schemas shared across the Change Impact Analysis pipeline.

These models double as ADK ``output_schema`` contracts for the agents that
produce them (Intent Extractor -> ChangeIntent, Dependency Mapper ->
DependencyMap, Report Synthesizer -> ImpactAssessment) and as the shape of
the corresponding session-state keys (``change_intent``, ``dependency_map``,
``impact_assessment``).
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class CostTier(str, Enum):
    LOW = "Low (<$50/mo)"
    MEDIUM = "Medium ($50-$500/mo)"
    HIGH = "High (>$500/mo)"


class ChangeIntent(BaseModel):
    """Structured technical intent extracted from the triggering CR/issue."""

    issue_number: int = Field(..., description="GitHub issue/PR number that triggered the analysis.")
    summary: str = Field(..., description="One-paragraph plain-language summary of the requested change.")
    requested_features: List[str] = Field(
        default_factory=list,
        description="Discrete features or behavior changes requested in the ticket.",
    )
    target_modules: List[str] = Field(
        default_factory=list,
        description="Modules, services, or components the requester believes are implicated.",
    )
    data_model_changes: List[str] = Field(
        default_factory=list,
        description="Any explicit data model / schema changes called out in the ticket.",
    )
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="Explicit acceptance criteria stated in the ticket, if any.",
    )


class DependencyMap(BaseModel):
    """Upstream/downstream dependency graph for the implicated code paths."""

    upstream_calling_services: List[str] = Field(
        default_factory=list,
        description="Services, jobs, or UI components that call into the affected code.",
    )
    downstream_dependencies: List[str] = Field(
        default_factory=list,
        description="Services, APIs, or shared libraries the affected code calls out to.",
    )
    database_tables_affected: List[str] = Field(
        default_factory=list,
        description="Database tables/collections touched by the change.",
    )
    api_contracts_modified: List[str] = Field(
        default_factory=list,
        description="API endpoints or contracts that would change shape or behavior.",
    )


class ApplicationImpact(BaseModel):
    modified_services: List[str] = Field(default_factory=list)
    domain_entity_changes: List[str] = Field(default_factory=list)
    api_boundary_impacts: List[str] = Field(default_factory=list)


class CodeImpact(BaseModel):
    repositories: List[str] = Field(default_factory=list)
    files: List[str] = Field(default_factory=list)
    breaking_changes: List[str] = Field(default_factory=list)


class FinOpsCostImpact(BaseModel):
    cost_tier: CostTier
    rationale: str = Field(..., description="Why this cost tier was assigned, referencing new/scaled cloud resources.")


class TestingRecommendations(BaseModel):
    integration_tests: List[str] = Field(default_factory=list)
    regression_tests: List[str] = Field(default_factory=list)
    contract_tests: List[str] = Field(default_factory=list)


class ImpactAssessment(BaseModel):
    """Final structured Change Impact Assessment, the Report Synthesizer's output_schema."""

    summary: str = Field(..., description="High-level plain-language overview of the CR.")
    application_impact: ApplicationImpact
    code_impact: CodeImpact
    finops_cost_impact: FinOpsCostImpact
    risk_level: RiskLevel
    risk_rationale: str = Field(..., description="Technical rationale behind the assigned risk level.")
    requires_human_approval: bool = Field(
        ...,
        description="True when risk_level is High or a breaking API/schema change is present.",
    )
    testing_recommendations: TestingRecommendations
    blast_radius: Optional[str] = Field(
        default=None,
        description="Proxy for how far the change could ripple (how many other modules/teams touch the affected code).",
    )
    open_questions: List[str] = Field(
        default_factory=list,
        description="Anything ambiguous worth resolving with the requester before development starts.",
    )
