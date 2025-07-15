"""
OpenTelemetry instrumentation for observability
"""

import os
from typing import Optional
from contextlib import contextmanager

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from config import Settings


class TelemetryManager:
    """Manages OpenTelemetry configuration and instrumentation"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.tracer = None
        self.meter = None
        self.enabled = settings.enable_telemetry and settings.otel_endpoint
        
        if self.enabled:
            self._setup_telemetry()
    
    def _setup_telemetry(self):
        """Configure OpenTelemetry providers and exporters"""
        # Create resource
        resource = Resource.create({
            "service.name": "tiny-backspace-api",
            "service.version": "1.0.0",
            "deployment.environment": "production" if not self.settings.debug else "development"
        })
        
        # Setup tracing
        trace_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(trace_provider)
        
        if self.settings.otel_endpoint:
            otlp_exporter = OTLPSpanExporter(
                endpoint=self.settings.otel_endpoint,
                insecure=True  # Use False in production with proper certs
            )
            span_processor = BatchSpanProcessor(otlp_exporter)
            trace_provider.add_span_processor(span_processor)
        
        self.tracer = trace.get_tracer(__name__)
        
        # Setup metrics
        if self.settings.otel_endpoint:
            metric_reader = PeriodicExportingMetricReader(
                exporter=OTLPMetricExporter(
                    endpoint=self.settings.otel_endpoint,
                    insecure=True
                ),
                export_interval_millis=60000  # Export every minute
            )
            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[metric_reader]
            )
            metrics.set_meter_provider(meter_provider)
        
        self.meter = metrics.get_meter(__name__)
        
        # Create metrics
        self._create_metrics()
    
    def _create_metrics(self):
        """Create application metrics"""
        if not self.meter:
            return
        
        # Request counter
        self.request_counter = self.meter.create_counter(
            "tinybackspace_requests_total",
            description="Total number of code generation requests",
            unit="1"
        )
        
        # Success counter
        self.success_counter = self.meter.create_counter(
            "tinybackspace_pr_created_total",
            description="Total number of successfully created PRs",
            unit="1"
        )
        
        # Error counter
        self.error_counter = self.meter.create_counter(
            "tinybackspace_errors_total",
            description="Total number of errors",
            unit="1"
        )
        
        # Duration histogram
        self.duration_histogram = self.meter.create_histogram(
            "tinybackspace_request_duration_seconds",
            description="Request processing duration",
            unit="s"
        )
        
        # Active requests gauge
        self.active_requests = self.meter.create_up_down_counter(
            "tinybackspace_active_requests",
            description="Number of active requests being processed",
            unit="1"
        )
    
    def instrument_app(self, app):
        """Instrument FastAPI application"""
        if self.enabled:
            FastAPIInstrumentor.instrument_app(app)
            HTTPXClientInstrumentor().instrument()
    
    @contextmanager
    def trace_operation(self, name: str, attributes: dict = None):
        """Context manager for tracing operations"""
        if not self.enabled or not self.tracer:
            yield None
            return
        
        with self.tracer.start_as_current_span(name) as span:
            if attributes:
                span.set_attributes(attributes)
            
            try:
                yield span
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
    
    def record_request(self, repo_url: str, prompt_length: int):
        """Record a new request"""
        if not self.enabled:
            return
        
        self.request_counter.add(1, {
            "repo_host": "github.com",
            "prompt_size_category": self._categorize_prompt_size(prompt_length)
        })
        self.active_requests.add(1)
    
    def record_success(self, repo_url: str, files_changed: int, duration: float):
        """Record successful PR creation"""
        if not self.enabled:
            return
        
        self.success_counter.add(1, {
            "repo_host": "github.com",
            "files_changed_category": self._categorize_files_changed(files_changed)
        })
        self.duration_histogram.record(duration, {
            "status": "success",
            "repo_host": "github.com"
        })
        self.active_requests.add(-1)
    
    def record_error(self, error_type: str, duration: float):
        """Record an error"""
        if not self.enabled:
            return
        
        self.error_counter.add(1, {
            "error_type": error_type
        })
        self.duration_histogram.record(duration, {
            "status": "error",
            "error_type": error_type
        })
        self.active_requests.add(-1)
    
    def _categorize_prompt_size(self, length: int) -> str:
        """Categorize prompt size for metrics"""
        if length < 50:
            return "small"
        elif length < 200:
            return "medium"
        else:
            return "large"
    
    def _categorize_files_changed(self, count: int) -> str:
        """Categorize number of files changed"""
        if count == 0:
            return "none"
        elif count == 1:
            return "single"
        elif count < 5:
            return "few"
        else:
            return "many"
    
    def create_trace_id(self) -> str:
        """Create a new trace ID"""
        if not self.enabled:
            return ""
        
        span = trace.get_current_span()
        if span:
            return format(span.get_span_context().trace_id, '032x')
        return ""
    
    def inject_trace_context(self, headers: dict) -> dict:
        """Inject trace context into headers for distributed tracing"""
        if not self.enabled:
            return headers
        
        propagator = TraceContextTextMapPropagator()
        propagator.inject(headers)
        return headers


# Singleton instance
_telemetry_manager: Optional[TelemetryManager] = None


def get_telemetry_manager(settings: Settings) -> TelemetryManager:
    """Get or create telemetry manager singleton"""
    global _telemetry_manager
    
    if _telemetry_manager is None:
        _telemetry_manager = TelemetryManager(settings)
    
    return _telemetry_manager