import logging
import os

from fastapi import APIRouter, Depends
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import get_tracer_provider, set_tracer_provider

from dependencies import get_token_header

otlp_exporter = OTLPSpanExporter(endpoint=f"http://{os.getenv('OTEL_COLLECTOR_SVC')}:4317", insecure=True)
resource = Resource.create(
    {
        "service.name": "ckc-badge-api",
    }
)

traceProvider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(otlp_exporter)
traceProvider.add_span_processor(processor)
set_tracer_provider(traceProvider)
tracer = get_tracer_provider().get_tracer(__name__)

router = APIRouter(
    tags=["tests"],
    dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger("s3logger")


@router.get("/trace-ping")
def ping():
    response = {"status": "SUCCESS", "data": "trace ping"}
    logger.info(response)
    logger.info("TEST trace ping")
    return response
