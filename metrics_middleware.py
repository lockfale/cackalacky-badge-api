import logging
import os
import socket
import time
from typing import Callable

from fastapi import Header, HTTPException, Request
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Get the host name of the machine
host_name = socket.gethostname()

# Setup OpenTelemetry
resource = Resource.create(
    {
        "service.name": "ckc-badge-api",
    }
)
exporter = OTLPMetricExporter(endpoint=f"http://{os.getenv('OTEL_COLLECTOR_SVC')}:4317", insecure=True)
metric_reader = PeriodicExportingMetricReader(exporter)
provider = MeterProvider(metric_readers=[metric_reader], resource=resource)

# Sets the global default meter provider
metrics.set_meter_provider(provider)

# Creates a meter from the global meter provider
meter = metrics.get_meter("my.meter.name")


# A simple counter metric
request_counter = meter.create_counter(
    "http_requests",
    description="Number of HTTP requests",
)

requests_latency = meter.create_histogram("http_request_latency_seconds", description="HTTP request latencies in seconds")

active_requests = meter.create_up_down_counter("http_active_requests", description="Number of active HTTP requests")

request_errors = meter.create_counter("http_request_error", description="Number of HTTP requests that resulted in an error")

path_requests_count = meter.create_counter("http_requests_paths", description="Count of HTTP requests by path")

logger = logging.getLogger("s3logger")


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        start_time = time.time()
        active_requests.add(1, {"host": host_name})
        try:
            response = await call_next(request)
        except HTTPException as http_exc:
            request_errors.add(1, {"host": host_name, "path": path, "status_code": http_exc.status_code})
            logger.info(http_exc.status_code)
            logger.info(http_exc.detail)
            response = Response(content=http_exc.detail, status_code=http_exc.status_code)
        except Exception as exc:
            request_errors.add(1, {"host": host_name, "path": path, "status_code": 500})
            logger.info(exc)
            response = Response(content=str(exc), status_code=500)
        finally:
            elapsed_time = time.time() - start_time
            requests_latency.record(elapsed_time, {"host": host_name})
            request_counter.add(1, {"host": host_name})
            path_requests_count.add(1, {"host": host_name, "path": path})
            active_requests.add(-1, {"host": host_name})

        return response
