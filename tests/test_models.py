"""Unit tests for the python_template_server.models module."""

from pathlib import Path

import pytest
from prometheus_client import Counter, Gauge
from pydantic import ValidationError

from python_template_server.models import (
    BaseMetricNames,
    BaseResponse,
    CertificateConfigModel,
    CustomJSONResponse,
    GetHealthResponse,
    JSONResponseConfigModel,
    MetricConfig,
    MetricTypes,
    PostLoginResponse,
    RateLimitConfigModel,
    ResponseCode,
    SecurityConfigModel,
    ServerConfigModel,
    ServerHealthStatus,
    TemplateServerConfig,
)


# Template Server Configuration Models
class TestServerConfigModel:
    """Unit tests for the ServerConfigModel class."""

    def test_model_dump(self, mock_server_config_dict: dict, mock_server_config: ServerConfigModel) -> None:
        """Test the model_dump method."""
        assert mock_server_config.model_dump() == mock_server_config_dict

    def test_address_property(self, mock_server_config: ServerConfigModel) -> None:
        """Test the address property."""
        assert mock_server_config.address == "localhost:8080"

    def test_url_property(self, mock_server_config: ServerConfigModel) -> None:
        """Test the url property."""
        assert mock_server_config.url == "https://localhost:8080"

    @pytest.mark.parametrize("port", [0, 70000])
    def test_port_field(self, mock_server_config_dict: dict, port: int) -> None:
        """Test the port field validation."""
        invalid_config_data = mock_server_config_dict.copy()
        invalid_config_data["port"] = port  # Invalid port number
        with pytest.raises(ValidationError):
            ServerConfigModel(**invalid_config_data)


class TestSecurityConfigModel:
    """Unit tests for the SecurityConfigModel class."""

    def test_model_dump(self, mock_security_config_dict: dict, mock_security_config: SecurityConfigModel) -> None:
        """Test the model_dump method."""
        assert mock_security_config.model_dump() == mock_security_config_dict


class TestRateLimitConfigModel:
    """Unit tests for the RateLimitConfigModel class."""

    def test_model_dump(self, mock_rate_limit_config_dict: dict, mock_rate_limit_config: RateLimitConfigModel) -> None:
        """Test the model_dump method."""
        assert mock_rate_limit_config.model_dump() == mock_rate_limit_config_dict


class TestCertificateConfigModel:
    """Unit tests for the CertificateConfigModel class."""

    def test_model_dump(
        self, mock_certificate_config_dict: dict, mock_certificate_config: CertificateConfigModel
    ) -> None:
        """Test the model_dump method."""
        assert mock_certificate_config.model_dump() == mock_certificate_config_dict

    def test_ssl_key_file_path_property(self, mock_certificate_config: CertificateConfigModel) -> None:
        """Test the ssl_key_file_path property."""
        assert mock_certificate_config.ssl_key_file_path == Path("/path/to/certs/key.pem")

    def test_ssl_cert_file_path_property(self, mock_certificate_config: CertificateConfigModel) -> None:
        """Test the ssl_cert_file_path property."""
        assert mock_certificate_config.ssl_cert_file_path == Path("/path/to/certs/cert.pem")

    def test_days_valid_field(
        self, mock_certificate_config_dict: dict, mock_certificate_config: CertificateConfigModel
    ) -> None:
        """Test the days_valid field."""
        invalid_config_data = mock_certificate_config_dict.copy()
        invalid_config_data["days_valid"] = -10  # Invalid value

        with pytest.raises(ValidationError):
            CertificateConfigModel(**invalid_config_data)


class TestJSONResponseConfigModel:
    """Unit tests for the JSONResponseConfigModel class."""

    def test_model_dump(
        self, mock_json_response_config_dict: dict, mock_json_response_config: JSONResponseConfigModel
    ) -> None:
        """Test the model_dump method."""
        assert mock_json_response_config.model_dump() == mock_json_response_config_dict


class TestTemplateServerConfig:
    """Unit tests for the TemplateServerConfig class."""

    def test_model_dump(
        self,
        mock_template_server_config: TemplateServerConfig,
        mock_server_config_dict: dict,
        mock_security_config_dict: dict,
        mock_rate_limit_config_dict: dict,
        mock_certificate_config_dict: dict,
        mock_json_response_config_dict: dict,
    ) -> None:
        """Test the model_dump method."""
        expected_dict = {
            "server": mock_server_config_dict,
            "security": mock_security_config_dict,
            "rate_limit": mock_rate_limit_config_dict,
            "certificate": mock_certificate_config_dict,
            "json_response": mock_json_response_config_dict,
        }
        assert mock_template_server_config.model_dump() == expected_dict

    def test_save_to_file(
        self,
        tmp_path: Path,
        mock_template_server_config: TemplateServerConfig,
    ) -> None:
        """Test the save_to_file method."""
        config_file = tmp_path / "config.json"
        mock_template_server_config.save_to_file(config_file)
        assert config_file.read_text(encoding="utf-8") == mock_template_server_config.model_dump_json(indent=2) + "\n"


# Prometheus Metric Models
class TestBaseMetricNames:
    """Unit tests for the BaseMetricNames enum."""

    @pytest.mark.parametrize(
        ("metric_name", "value"),
        [
            (BaseMetricNames.TOKEN_CONFIGURED, "token_configured"),
            (BaseMetricNames.AUTH_SUCCESS_TOTAL, "auth_success_total"),
            (BaseMetricNames.AUTH_FAILURE_TOTAL, "auth_failure_total"),
            (BaseMetricNames.RATE_LIMIT_EXCEEDED_TOTAL, "rate_limit_exceeded_total"),
        ],
    )
    def test_enum_values(self, metric_name: BaseMetricNames, value: str) -> None:
        """Test the enum values."""
        assert metric_name.value == value


class TestMetricTypes:
    """Unit tests for the MetricTypes enum."""

    @pytest.mark.parametrize(
        ("metric_type", "value"),
        [
            (MetricTypes.COUNTER, "counter"),
            (MetricTypes.GAUGE, "gauge"),
        ],
    )
    def test_enum_values(self, metric_type: MetricTypes, value: str) -> None:
        """Test the enum values."""
        assert metric_type.value == value

    def test_prometheus_class_property(self) -> None:
        """Test the prometheus_class property."""
        assert MetricTypes.COUNTER.prometheus_class == Counter
        assert MetricTypes.GAUGE.prometheus_class == Gauge


class TestMetricConfig:
    """Unit tests for the MetricConfig dataclass."""

    def test_metric_config_initialization(self) -> None:
        """Test initialization of MetricConfig."""
        metric_config = MetricConfig(
            name=BaseMetricNames.AUTH_SUCCESS_TOTAL,
            metric_type=MetricTypes.COUNTER,
            description="Total number of successful authentication attempts",
            labels=["user_id"],
        )

        assert metric_config.name == BaseMetricNames.AUTH_SUCCESS_TOTAL
        assert metric_config.metric_type == MetricTypes.COUNTER
        assert metric_config.description == "Total number of successful authentication attempts"
        assert metric_config.labels == ["user_id"]


# API Response Models
class TestCustomJSONResponse:
    """Unit tests for the CustomJSONResponse class."""

    def test_configure_method(self, mock_json_response_config: JSONResponseConfigModel) -> None:
        """Test the configure class method."""
        CustomJSONResponse.configure(mock_json_response_config)

        assert CustomJSONResponse._ensure_ascii == mock_json_response_config.ensure_ascii
        assert CustomJSONResponse._allow_nan == mock_json_response_config.allow_nan
        assert CustomJSONResponse._indent == mock_json_response_config.indent
        assert CustomJSONResponse.media_type == mock_json_response_config.media_type

    def test_render_with_unicode(self, mock_json_response_config: JSONResponseConfigModel) -> None:
        """Test rendering JSON with Unicode characters (emojis)."""
        CustomJSONResponse.configure(mock_json_response_config)
        response = CustomJSONResponse(content={"message": "Hello 👋 World 🌍"})

        rendered = response.render({"message": "Hello 👋 World 🌍"})
        assert b"Hello \\ud83d\\udc4b World" not in rendered  # Should NOT be escaped
        assert "👋".encode() in rendered  # Should preserve emoji
        assert "🌍".encode() in rendered

    def test_render_with_ensure_ascii_true(self) -> None:
        """Test rendering with ensure_ascii=True."""
        config = JSONResponseConfigModel(ensure_ascii=True)
        CustomJSONResponse.configure(config)
        response = CustomJSONResponse(content={"message": "Hello 👋"})

        rendered = response.render({"message": "Hello 👋"})
        # With ensure_ascii=True, Unicode should be escaped
        assert b"\\ud83d\\udc4b" in rendered or b"\\u" in rendered

    def test_render_with_indent(self) -> None:
        """Test rendering with indentation."""
        config = JSONResponseConfigModel(indent=2)
        CustomJSONResponse.configure(config)
        response = CustomJSONResponse(content={"key": "value"})

        rendered = response.render({"key": "value"})
        # With indent, output should have newlines and spaces
        assert b"\n" in rendered
        assert b"  " in rendered

    def test_render_compact(self, mock_json_response_config: JSONResponseConfigModel) -> None:
        """Test rendering in compact mode (no indent)."""
        CustomJSONResponse.configure(mock_json_response_config)
        response = CustomJSONResponse(content={"key": "value", "number": 42})

        rendered = response.render({"key": "value", "number": 42})
        # Compact mode should use "," separator without spaces after
        assert rendered == b'{"key":"value","number":42}'


class TestResponseCode:
    """Unit tests for the ResponseCode enum."""

    @pytest.mark.parametrize(
        ("response_code", "status_code"),
        [
            (ResponseCode.OK, 200),
            (ResponseCode.CREATED, 201),
            (ResponseCode.ACCEPTED, 202),
            (ResponseCode.NO_CONTENT, 204),
            (ResponseCode.BAD_REQUEST, 400),
            (ResponseCode.UNAUTHORIZED, 401),
            (ResponseCode.FORBIDDEN, 403),
            (ResponseCode.NOT_FOUND, 404),
            (ResponseCode.CONFLICT, 409),
            (ResponseCode.INTERNAL_SERVER_ERROR, 500),
            (ResponseCode.SERVICE_UNAVAILABLE, 503),
        ],
    )
    def test_enum_values(self, response_code: ResponseCode, status_code: int) -> None:
        """Test the enum values."""
        assert response_code.value == status_code


class TestServerHealthStatus:
    """Unit tests for the ServerHealthStatus enum."""

    @pytest.mark.parametrize(
        ("server_health_status", "status"),
        [
            (ServerHealthStatus.HEALTHY, "HEALTHY"),
            (ServerHealthStatus.DEGRADED, "DEGRADED"),
            (ServerHealthStatus.UNHEALTHY, "UNHEALTHY"),
        ],
    )
    def test_enum_values(self, server_health_status: ServerHealthStatus, status: str) -> None:
        """Test the enum values."""
        assert server_health_status.name == status


class TestBaseResponse:
    """Unit tests for the BaseResponse class."""

    def test_model_dump(self) -> None:
        """Test the model_dump method."""
        timestamp = BaseResponse.current_timestamp()
        config_dict: dict = {"code": ResponseCode.OK, "message": "Success", "timestamp": timestamp}
        response = BaseResponse(**config_dict)
        assert response.model_dump() == config_dict


class TestGetHealthResponse:
    """Unit tests for the GetHealthResponse class."""

    def test_model_dump(self) -> None:
        """Test the model_dump method."""
        timestamp = GetHealthResponse.current_timestamp()
        config_dict: dict = {
            "code": ResponseCode.OK,
            "message": "Server is healthy",
            "timestamp": timestamp,
            "status": ServerHealthStatus.HEALTHY,
        }
        response = GetHealthResponse(**config_dict)
        assert response.model_dump() == config_dict


class TestPostLoginResponse:
    """Unit tests for the PostLoginResponse class."""

    def test_model_dump(self) -> None:
        """Test the model_dump method."""
        timestamp = PostLoginResponse.current_timestamp()
        config_dict: dict = {
            "code": ResponseCode.OK,
            "message": "Login successful",
            "timestamp": timestamp,
        }
        response = PostLoginResponse(**config_dict)
        assert response.model_dump() == config_dict
