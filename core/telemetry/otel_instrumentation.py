"""
OpenTelemetry instrumentation for BuildRunner 3.2
Provides automatic tracing for all operations with Datadog backend
"""

import os
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
from contextlib import contextmanager
import time

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc import trace_exporter, metrics_exporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)


class TelemetryManager:
    """Manages OpenTelemetry instrumentation for BuildRunner"""

    def __init__(self):
        self.tracer: Optional[trace.Tracer] = None
        self.meter: Optional[metrics.Meter] = None
        self.initialized = False

        # Metrics collectors
        self.task_counter = None
        self.task_duration = None
        self.error_counter = None
        self.token_usage = None
        self.api_latency = None

    def initialize(self, service_name: str = "buildrunner") -> None:
        """Initialize OpenTelemetry with Datadog exporter"""
        if self.initialized:
            return

        try:
            # Get configuration from environment
            dd_site = os.getenv("DD_SITE", "us5.datadoghq.com")
            dd_api_key = os.getenv("DD_API_KEY")
            environment = os.getenv("DD_ENV", "development")
            version = os.getenv("DD_VERSION", "3.2.0")

            if not dd_api_key:
                logger.warning("DD_API_KEY not set, telemetry disabled")
                return

            # Create resource with service information
            resource = Resource.create(
                {
                    "service.name": service_name,
                    "service.version": version,
                    "deployment.environment": environment,
                    "service.namespace": "buildrunner",
                    "host.name": os.uname().nodename,
                }
            )

            # Setup trace provider
            trace_provider = TracerProvider(resource=resource)

            # Configure OTLP exporter for traces
            otlp_trace_exporter = trace_exporter.OTLPSpanExporter(
                endpoint="localhost:4317", insecure=True
            )

            # Add span processor
            span_processor = BatchSpanProcessor(otlp_trace_exporter)
            trace_provider.add_span_processor(span_processor)

            # Set global trace provider
            trace.set_tracer_provider(trace_provider)
            self.tracer = trace.get_tracer(__name__)

            # Setup metrics provider
            otlp_metrics_exporter = metrics_exporter.OTLPMetricExporter(
                endpoint="localhost:4317", insecure=True
            )

            metric_reader = PeriodicExportingMetricReader(
                exporter=otlp_metrics_exporter,
                export_interval_millis=10000,  # Export every 10 seconds
            )

            meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])

            # Set global meter provider
            metrics.set_meter_provider(meter_provider)
            self.meter = metrics.get_meter(__name__)

            # Create metrics instruments
            self._create_metrics()

            # Set up propagator for distributed tracing
            set_global_textmap(TraceContextTextMapPropagator())

            # Auto-instrument common libraries
            RequestsInstrumentor().instrument()
            LoggingInstrumentor().instrument(set_logging_format=True)

            self.initialized = True
            logger.info(f"Telemetry initialized for {service_name} v{version}")

        except Exception as e:
            logger.error(f"Failed to initialize telemetry: {e}")

    def _create_metrics(self) -> None:
        """Create metric instruments"""
        if not self.meter:
            return

        # Task metrics
        self.task_counter = self.meter.create_counter(
            name="buildrunner.tasks.total", description="Total number of tasks executed", unit="1"
        )

        self.task_duration = self.meter.create_histogram(
            name="buildrunner.task.duration", description="Task execution duration", unit="ms"
        )

        # Error tracking
        self.error_counter = self.meter.create_counter(
            name="buildrunner.errors.total", description="Total number of errors", unit="1"
        )

        # LLM metrics
        self.token_usage = self.meter.create_counter(
            name="buildrunner.llm.tokens", description="LLM token usage", unit="tokens"
        )

        # API metrics
        self.api_latency = self.meter.create_histogram(
            name="buildrunner.api.latency", description="API endpoint latency", unit="ms"
        )

    @contextmanager
    def span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Create a traced span context"""
        if not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            try:
                yield span
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    def trace_task(self, task_type: str):
        """Decorator to trace task execution"""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.tracer:
                    return func(*args, **kwargs)

                start_time = time.time()

                with self.span(
                    f"task.{task_type}",
                    attributes={
                        "task.type": task_type,
                        "task.name": func.__name__,
                    },
                ) as span:
                    try:
                        result = func(*args, **kwargs)

                        # Record metrics
                        if self.task_counter:
                            self.task_counter.add(1, {"task.type": task_type, "status": "success"})

                        if self.task_duration:
                            duration_ms = (time.time() - start_time) * 1000
                            self.task_duration.record(duration_ms, {"task.type": task_type})

                        return result

                    except Exception as e:
                        if self.task_counter:
                            self.task_counter.add(1, {"task.type": task_type, "status": "error"})

                        if self.error_counter:
                            self.error_counter.add(
                                1, {"task.type": task_type, "error.type": type(e).__name__}
                            )

                        raise

            return wrapper

        return decorator

    def trace_api(self, endpoint: str):
        """Decorator to trace API endpoints"""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.tracer:
                    return await func(*args, **kwargs)

                start_time = time.time()

                with self.span(
                    f"api.{endpoint}",
                    attributes={
                        "http.route": endpoint,
                        "http.method": kwargs.get("request", {}).get("method", "GET"),
                    },
                ) as span:
                    try:
                        result = await func(*args, **kwargs)

                        # Record latency
                        if self.api_latency:
                            latency_ms = (time.time() - start_time) * 1000
                            self.api_latency.record(latency_ms, {"endpoint": endpoint})

                        return result

                    except Exception as e:
                        if self.error_counter:
                            self.error_counter.add(
                                1, {"endpoint": endpoint, "error.type": type(e).__name__}
                            )
                        raise

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.tracer:
                    return func(*args, **kwargs)

                start_time = time.time()

                with self.span(
                    f"api.{endpoint}",
                    attributes={
                        "http.route": endpoint,
                    },
                ) as span:
                    try:
                        result = func(*args, **kwargs)

                        # Record latency
                        if self.api_latency:
                            latency_ms = (time.time() - start_time) * 1000
                            self.api_latency.record(latency_ms, {"endpoint": endpoint})

                        return result

                    except Exception as e:
                        if self.error_counter:
                            self.error_counter.add(
                                1, {"endpoint": endpoint, "error.type": type(e).__name__}
                            )
                        raise

            # Return appropriate wrapper based on function type
            import asyncio

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator

    def record_llm_usage(
        self, model: str, input_tokens: int, output_tokens: int, latency_ms: float
    ):
        """Record LLM token usage and performance"""
        if not self.initialized:
            return

        span = trace.get_current_span()
        if span:
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.input_tokens", input_tokens)
            span.set_attribute("llm.output_tokens", output_tokens)
            span.set_attribute("llm.total_tokens", input_tokens + output_tokens)
            span.set_attribute("llm.latency_ms", latency_ms)

        if self.token_usage:
            self.token_usage.add(input_tokens, {"model": model, "token.type": "input"})
            self.token_usage.add(output_tokens, {"model": model, "token.type": "output"})

    def record_custom_metric(
        self, name: str, value: float, attributes: Optional[Dict[str, Any]] = None
    ):
        """Record a custom metric"""
        if not self.meter:
            return

        # Create a gauge for the custom metric
        gauge = self.meter.create_gauge(
            name=f"buildrunner.custom.{name}", description=f"Custom metric: {name}", unit="1"
        )

        gauge.set(value, attributes or {})

    def shutdown(self):
        """Shutdown telemetry gracefully"""
        if not self.initialized:
            return

        try:
            # Force flush all pending spans and metrics
            if self.tracer:
                trace.get_tracer_provider().force_flush()

            if self.meter:
                metrics.get_meter_provider().force_flush()

            logger.info("Telemetry shutdown complete")

        except Exception as e:
            logger.error(f"Error during telemetry shutdown: {e}")


# Global instance
telemetry = TelemetryManager()


def initialize_telemetry():
    """Initialize global telemetry instance"""
    telemetry.initialize()


def get_telemetry() -> TelemetryManager:
    """Get the global telemetry instance"""
    return telemetry
