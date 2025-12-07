"""Unit tests for the python_template_server.prometheus_handler module."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI

from python_template_server.models import BaseMetricNames
from python_template_server.prometheus_handler import BASE_METRICS_CONFIG, PrometheusHandler


@pytest.fixture
def mock_prometheus_handler() -> PrometheusHandler:
    """Fixture to create a PrometheusHandler instance with a mocked FastAPI app."""
    mock_fastapi_app = MagicMock(spec=FastAPI)
    return PrometheusHandler(app=mock_fastapi_app)


class TestPrometheusHandler:
    """Unit tests for the PrometheusHandler class."""

    def test_initialize_metrics(self, mock_prometheus_handler: PrometheusHandler) -> None:
        """Test that metrics are initialized correctly."""
        assert len(mock_prometheus_handler.metrics) == len(BASE_METRICS_CONFIG)

        for metric, config in zip(
            mock_prometheus_handler.metrics.values(),
            BASE_METRICS_CONFIG,
            strict=False,
        ):
            assert isinstance(metric, config.metric_type.prometheus_class)

    def test_get_metric_valid_name(self, mock_prometheus_handler: PrometheusHandler) -> None:
        """Test that getting a metric by a valid name works."""
        for config in BASE_METRICS_CONFIG:
            metric = mock_prometheus_handler.get_metric(config.name)
            assert isinstance(metric, config.metric_type.prometheus_class)

    def test_get_metric_invalid_name(self, mock_prometheus_handler: PrometheusHandler) -> None:
        """Test that getting a metric with an invalid name raises a KeyError."""
        invalid_name = MagicMock("invalid_metric_name")
        with pytest.raises(ValueError, match=f"Metric '{invalid_name}' not found"):
            mock_prometheus_handler.get_metric(invalid_name)

    def test_increment_counter(self, mock_prometheus_handler: PrometheusHandler) -> None:
        """Test incrementing a counter metric."""
        auth_success_metric = mock_prometheus_handler.get_metric(BaseMetricNames.AUTH_SUCCESS_TOTAL)
        initial_value = auth_success_metric._value.get()  # Accessing protected member for testing

        mock_prometheus_handler.increment_counter(BaseMetricNames.AUTH_SUCCESS_TOTAL)

        updated_value = auth_success_metric._value.get()
        assert updated_value == initial_value + 1

    def test_increment_counter_with_labels(self, mock_prometheus_handler: PrometheusHandler) -> None:
        """Test incrementing a counter metric with labels."""
        auth_failure_metric = mock_prometheus_handler.get_metric(BaseMetricNames.AUTH_FAILURE_TOTAL)
        initial_value = auth_failure_metric.labels(
            reason="invalid_token"
        )._value.get()  # Accessing protected member for testing

        mock_prometheus_handler.increment_counter(
            BaseMetricNames.AUTH_FAILURE_TOTAL,
            labels={"reason": "invalid_token"},
        )

        updated_value = auth_failure_metric.labels(reason="invalid_token")._value.get()
        assert updated_value == initial_value + 1

    def test_increment_counter_invalid_type(self, mock_prometheus_handler: PrometheusHandler) -> None:
        """Test that incrementing a non-counter metric raises a TypeError."""
        with pytest.raises(TypeError, match=f"Metric '{BaseMetricNames.TOKEN_CONFIGURED}' is not a Counter"):
            mock_prometheus_handler.increment_counter(BaseMetricNames.TOKEN_CONFIGURED)

    def test_set_gauge(self, mock_prometheus_handler: PrometheusHandler) -> None:
        """Test setting a gauge metric."""
        token_configured_metric = mock_prometheus_handler.get_metric(BaseMetricNames.TOKEN_CONFIGURED)

        mock_prometheus_handler.set_gauge(BaseMetricNames.TOKEN_CONFIGURED, 1)

        updated_value = token_configured_metric._value.get()
        assert updated_value == 1

    def test_set_gauge_invalid_type(self, mock_prometheus_handler: PrometheusHandler) -> None:
        """Test that setting a non-gauge metric raises a TypeError."""
        with pytest.raises(TypeError, match=f"Metric '{BaseMetricNames.AUTH_SUCCESS_TOTAL}' is not a Gauge"):
            mock_prometheus_handler.set_gauge(BaseMetricNames.AUTH_SUCCESS_TOTAL, 10)
