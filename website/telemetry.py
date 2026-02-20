from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
import os

opentel_app_servicename = os.environ.get("SERVICE_NAME")
opentel_app_version = os.environ.get("APP_VERSION")
opentel_endpoint = os.environ.get("OPENTEL_ENDPOINT")

def setup_telemetry(app):

    resource = Resource.create({
        "service.name": opentel_app_servicename,
        "service.version": opentel_app_version,
    })

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    exporter = OTLPSpanExporter(
        endpoint=opentel_endpoint,
        insecure=True,
    )

    provider.add_span_processor(
        BatchSpanProcessor(exporter)
    )

    # AUTO INSTRUMENTATIONS
    FlaskInstrumentor().instrument_app(app)
    RequestsInstrumentor().instrument()
    SQLite3Instrumentor().instrument()