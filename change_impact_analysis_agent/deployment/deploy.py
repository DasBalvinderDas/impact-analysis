"""Agent Runtime deployment entrypoint.

Wraps `root_agent` in `vertexai.preview.reasoning_engines.AdkApp` and deploys
it to Vertex AI Agent Engine (Google Cloud Agent Runtime). Run with:

    python -m change_impact_analysis_agent.deployment.deploy \\
        --project your-gcp-project-id \\
        --location us-central1 \\
        --staging-bucket gs://your-staging-bucket

Requires `google-cloud-aiplatform[adk,agent_engines]` in addition to the
base requirements.
"""

from __future__ import annotations

import argparse

from change_impact_analysis_agent.agent import root_agent


def build_adk_app():
    from vertexai.preview import reasoning_engines

    return reasoning_engines.AdkApp(
        agent=root_agent,
        enable_tracing=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy the Change Impact Analysis Agent to Agent Runtime.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--location", default="us-central1")
    parser.add_argument("--staging-bucket", required=True, help="gs://bucket for staging build artifacts")
    parser.add_argument(
        "--requirements-file",
        default="change_impact_analysis_agent/requirements.txt",
    )
    parser.add_argument(
        "--display-name",
        default="change-impact-analysis-agent",
    )
    args = parser.parse_args()

    import vertexai
    from vertexai.preview import reasoning_engines

    vertexai.init(
        project=args.project,
        location=args.location,
        staging_bucket=args.staging_bucket,
    )

    app = build_adk_app()

    with open(args.requirements_file) as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    remote_app = reasoning_engines.ReasoningEngine.create(
        app,
        requirements=requirements,
        display_name=args.display_name,
        extra_packages=["change_impact_analysis_agent"],
    )
    print(f"Deployed. Resource name: {remote_app.resource_name}")


if __name__ == "__main__":
    main()
