"""Unit tests for the python_template_server.models module."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from python_template_server.models import (
    BaseResponse,
    CertificateConfigModel,
    GetHealthResponse,
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


class TestTemplateServerConfig:
    """Unit tests for the TemplateServerConfig class."""

    def test_model_dump(
        self,
        mock_template_server_config: TemplateServerConfig,
        mock_server_config_dict: dict,
        mock_security_config_dict: dict,
        mock_rate_limit_config_dict: dict,
        mock_certificate_config_dict: dict,
    ) -> None:
        """Test the model_dump method."""
        expected_dict = {
            "server": mock_server_config_dict,
            "security": mock_security_config_dict,
            "rate_limit": mock_rate_limit_config_dict,
            "certificate": mock_certificate_config_dict,
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
        assert config_file.read_text(encoding="utf-8") == mock_template_server_config.model_dump_json(indent=2)


# API Response Models
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
        config_dict: dict = {"code": ResponseCode.OK, "message": "Success", "timestamp": "2025-11-22T12:00:00Z"}
        response = BaseResponse(**config_dict)
        assert response.model_dump() == config_dict


class TestGetHealthResponse:
    """Unit tests for the GetHealthResponse class."""

    def test_model_dump(self) -> None:
        """Test the model_dump method."""
        config_dict: dict = {
            "code": ResponseCode.OK,
            "message": "Server is healthy",
            "timestamp": "2025-11-22T12:00:00Z",
            "status": ServerHealthStatus.HEALTHY,
        }
        response = GetHealthResponse(**config_dict)
        assert response.model_dump() == config_dict
