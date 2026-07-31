"""Observability, audit, and telemetry wiring.

Enables OpenTelemetry tracing and structured logging to Google Cloud
Logging / Vertex Telemetry so every agent reasoning step, state transition,
and tool call in the pipeline is recorded for compliance review.

Call ``configure_telemetry()`` once at process startup (``agent.py`` does
this on import). It is safe to call multiple times; only the first call
takes effect.
"""

from __future__ import annotations

import logging
import os

_CONFIGURED = False
_LOGGER_NAME = "change_impact_analysis_agent"


def configure_telemetry() -> logging.Logger:
    """Configure OpenTelemetry tracing + Cloud Logging, idempotently.

    Falls back to local structured logging (stdlib ``logging``) when
    ``GOOGLE_CLOUD_PROJECT`` is unset or the Cloud Logging/OTel exporters
    are unavailable, so the pipeline still runs (and is still auditable via
    stdout) in local/dev environments.
    """
    global _CONFIGURED
    logger = logging.getLogger(_LOGGER_NAME)

    if _CONFIGURED:
        return logger

    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                '{"time": "%(asctime)s", "level": "%(levelname)s", '
                '"agent": "%(name)s", "message": %(message)r}'
            )
        )
        logger.addHandler(handler)

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project_id:
        try:
            import google.cloud.logging as cloud_logging

            cloud_logging_client = cloud_logging.Client(project=project_id)
            cloud_logging_client.setup_logging(log_level=logging.INFO)
            logger.info("Google Cloud Logging attached for project %s", project_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cloud Logging unavailable, using local logging only: %s", exc)

        try:
            from opentelemetry import trace
            from opentelemetry.sdk.resources import SERVICE_NAME, Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

            resource = Resource.create({SERVICE_NAME: "change-impact-analysis-agent"})
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(
                BatchSpanProcessor(CloudTraceSpanExporter(project_id=project_id))
            )
            trace.set_tracer_provider(provider)
            logger.info("OpenTelemetry Cloud Trace exporter configured.")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cloud Trace exporter unavailable, tracing disabled: %s", exc)
    else:
        logger.info("GOOGLE_CLOUD_PROJECT unset; running with local logging only (no Cloud Logging/Trace).")

    _CONFIGURED = True
    return logger


def get_logger() -> logging.Logger:
    return configure_telemetry()


def audit_event(event: str, **fields: object) -> None:
    """Emit a structured audit log line for a pipeline step / tool call / state transition."""
    logger = get_logger()
    payload = {"event": event, **fields}
    logger.info("%s", payload)
