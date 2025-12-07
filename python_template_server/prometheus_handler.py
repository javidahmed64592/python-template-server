"""Prometheus metrics handler."""

from fastapi import FastAPI
from prometheus_client import Counter, Gauge
from prometheus_fastapi_instrumentator import Instrumentator

from python_template_server.models import BaseMetricNames, MetricConfig, MetricTypes

BASE_METRICS_CONFIG = [
    MetricConfig(
        name=BaseMetricNames.TOKEN_CONFIGURED,
        metric_type=MetricTypes.GAUGE,
        description="Whether API token is properly configured (1=configured, 0=not configured)",
    ),
    MetricConfig(
        name=BaseMetricNames.AUTH_SUCCESS_TOTAL,
        metric_type=MetricTypes.COUNTER,
        description="Total number of successful authentication attempts",
    ),
    MetricConfig(
        name=BaseMetricNames.AUTH_FAILURE_TOTAL,
        metric_type=MetricTypes.COUNTER,
        description="Total number of failed authentication attempts",
        labels=["reason"],
    ),
    MetricConfig(
        name=BaseMetricNames.RATE_LIMIT_EXCEEDED_TOTAL,
        metric_type=MetricTypes.COUNTER,
        description="Total number of requests that exceeded rate limits",
        labels=["endpoint"],
    ),
]


class PrometheusHandler:
    """Prometheus metrics handler."""

    def __init__(self, app: FastAPI) -> None:
        """Initialize PrometheusHandler with FastAPI app.

        :param FastAPI app: FastAPI application instance
        """
        self.instrumentator = Instrumentator()
        self.instrumentator.instrument(app).expose(app, endpoint="/metrics")

        self.metrics: dict[BaseMetricNames, Counter | Gauge] = {}
        self._initialize_metrics()

    def _initialize_metrics(self) -> None:
        """Initialize metrics based on the base configuration."""
        for metric_config in BASE_METRICS_CONFIG:
            self.metrics[metric_config.name] = metric_config.metric_type.prometheus_class(
                metric_config.name.value,
                metric_config.description,
                metric_config.labels or [],
            )

    def get_metric(self, name: BaseMetricNames) -> Counter | Gauge:
        """Get a specific metric by name."""
        if not (metric := self.metrics.get(name)):
            msg = f"Metric '{name}' not found."
            raise ValueError(msg)
        return metric

    def increment_counter(self, name: BaseMetricNames, labels: dict[str, str] | None = None) -> None:
        """Increment a counter metric.

        :param BaseMetricNames name: Name of the metric to increment
        :param dict[str, str] | None labels: Optional label key-value pairs for the metric
        """
        counter = self.get_metric(name)
        if not isinstance(counter, Counter):
            msg = f"Metric '{name}' is not a Counter."
            raise TypeError(msg)
        if labels:
            counter = counter.labels(**labels)
        counter.inc()

    def set_gauge(self, name: BaseMetricNames, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge metric.

        :param BaseMetricNames name: Name of the metric to set
        :param float value: Value to set the gauge to
        :param dict[str, str] | None labels: Optional label key-value pairs for the metric
        """
        gauge = self.get_metric(name)
        if not isinstance(gauge, Gauge):
            msg = f"Metric '{name}' is not a Gauge."
            raise TypeError(msg)
        if labels:
            gauge = gauge.labels(**labels)
        gauge.set(value)
