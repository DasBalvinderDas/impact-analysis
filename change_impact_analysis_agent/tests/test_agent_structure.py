"""Structural smoke tests: verify the pipeline wires up correctly without
requiring live GCP/GitHub credentials (secret/token resolution is lazy).
"""

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent

from change_impact_analysis_agent.agent import root_agent
from change_impact_analysis_agent.models.schemas import (
    ChangeIntent,
    DependencyMap,
    ImpactAssessment,
)


def test_root_agent_is_sequential_with_expected_steps():
    assert isinstance(root_agent, SequentialAgent)
    assert root_agent.name == "change_impact_analysis_pipeline"
    step_names = [a.name for a in root_agent.sub_agents]
    assert step_names == [
        "intent_extractor_agent",
        "context_retrieval_parallel",
        "dependency_mapper_agent",
        "impact_risk_evaluators_parallel",
        "report_synthesizer_agent",
        "publisher_governance_agent",
    ]


def test_context_retrieval_is_parallel_doc_and_code_search():
    context_retrieval = root_agent.sub_agents[1]
    assert isinstance(context_retrieval, ParallelAgent)
    names = {a.name for a in context_retrieval.sub_agents}
    assert names == {"doc_search_agent", "code_search_agent"}


def test_evaluators_are_parallel_app_code_testing():
    evaluators = root_agent.sub_agents[3]
    assert isinstance(evaluators, ParallelAgent)
    names = {a.name for a in evaluators.sub_agents}
    assert names == {"app_arch_eval_agent", "code_eval_agent", "testing_eval_agent"}


def test_output_schemas_wired_to_expected_state_keys():
    intent_extractor = root_agent.sub_agents[0]
    dependency_mapper = root_agent.sub_agents[2]
    report_synthesizer = root_agent.sub_agents[4]

    assert isinstance(intent_extractor, LlmAgent)
    assert intent_extractor.output_schema is ChangeIntent
    assert intent_extractor.output_key == "change_intent"

    assert dependency_mapper.output_schema is DependencyMap
    assert dependency_mapper.output_key == "dependency_map"

    assert report_synthesizer.output_schema is ImpactAssessment
    assert report_synthesizer.output_key == "impact_assessment"


def test_impact_assessment_hitl_flag_required_field():
    schema = ImpactAssessment.model_json_schema()
    assert "requires_human_approval" in schema["required"]
    assert "risk_level" in schema["required"]
