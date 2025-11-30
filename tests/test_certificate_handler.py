"""Unit tests for the python_template_server.certificate_handler module."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa

from python_template_server.certificate_handler import (
    CertificateHandler,
    generate_self_signed_certificate,
)
from python_template_server.models import CertificateConfigModel, TemplateServerConfig

RSA_KEY_SIZE = 4096


@pytest.fixture
def mock_example_server(
    tmp_path: Path, mock_template_server_config: TemplateServerConfig
) -> Generator[MagicMock, None, None]:
    """Mock the ExampleServer class."""
    with patch("python_template_server.certificate_handler.ExampleServer") as mock_server:
        cert_dir = tmp_path / "certs"
        mock_template_server_config.certificate.directory = str(cert_dir)
        mock_server.return_value.config = mock_template_server_config
        yield mock_server


class TestCertificateHandler:
    """Unit tests for the CertificateHandler class."""

    def test_init(self, mock_certificate_config: CertificateConfigModel) -> None:
        """Test CertificateHandler initialization."""
        handler = CertificateHandler(mock_certificate_config)

        assert handler.cert_dir == mock_certificate_config.directory
        assert handler.cert_file == mock_certificate_config.ssl_cert_file_path
        assert handler.key_file == mock_certificate_config.ssl_key_file_path
        assert handler.days_valid == mock_certificate_config.days_valid

    def test_certificate_subject(self, mock_certificate_config: CertificateConfigModel) -> None:
        """Test certificate_subject property returns correct x509.Name."""
        handler = CertificateHandler(mock_certificate_config)
        subject = handler.certificate_subject

        assert isinstance(subject, x509.Name)
        # Verify some key attributes
        attrs = {attr.oid._name: attr.value for attr in subject}
        assert attrs["countryName"] == "UK"
        assert attrs["commonName"] == "localhost"

    def test_new_private_key(self, mock_certificate_config: CertificateConfigModel) -> None:
        """Test new_private_key generates an RSA private key."""
        handler = CertificateHandler(mock_certificate_config)
        private_key = handler.new_private_key()

        assert isinstance(private_key, rsa.RSAPrivateKey)
        assert private_key.key_size == RSA_KEY_SIZE

    def test_write_to_file(self, mock_certificate_config: CertificateConfigModel, tmp_path: Path) -> None:
        """Test _write_to_file writes data to a file."""
        handler = CertificateHandler(mock_certificate_config)
        test_file = tmp_path / "test_file.txt"
        test_data = b"test data"

        handler._write_to_file(test_file, test_data)

        assert test_file.exists()
        assert test_file.read_bytes() == test_data

    def test_write_to_key_file(self, mock_certificate_config: CertificateConfigModel, tmp_path: Path) -> None:
        """Test write_to_key_file writes to the correct key file."""
        cert_dir = tmp_path / "certs"
        cert_dir.mkdir()
        mock_certificate_config.directory = str(cert_dir)
        handler = CertificateHandler(mock_certificate_config)
        test_data = b"key data"

        handler.write_to_key_file(test_data)

        assert handler.key_file.exists()
        assert handler.key_file.read_bytes() == test_data

    def test_write_to_cert_file(self, mock_certificate_config: CertificateConfigModel, tmp_path: Path) -> None:
        """Test write_to_cert_file writes to the correct cert file."""
        cert_dir = tmp_path / "certs"
        cert_dir.mkdir()
        mock_certificate_config.directory = str(cert_dir)
        handler = CertificateHandler(mock_certificate_config)
        test_data = b"cert data"

        handler.write_to_cert_file(test_data)

        assert handler.cert_file.exists()
        assert handler.cert_file.read_bytes() == test_data

    def test_generate_self_signed_cert_success(
        self, mock_certificate_config: CertificateConfigModel, tmp_path: Path
    ) -> None:
        """Test successful generation of self-signed certificate."""
        cert_dir = tmp_path / "certs"
        mock_certificate_config.directory = str(cert_dir)
        handler = CertificateHandler(mock_certificate_config)
        handler.generate_self_signed_cert()

        # Verify files were created
        assert handler.key_file.exists()
        assert handler.cert_file.exists()

        # Verify files contain PEM data
        assert b"BEGIN RSA PRIVATE KEY" in handler.key_file.read_bytes()
        assert b"BEGIN CERTIFICATE" in handler.cert_file.read_bytes()

    def test_generate_self_signed_cert_directory_creation_fails(
        self,
        mock_certificate_config: CertificateConfigModel,
        mock_mkdir: MagicMock,
        mock_open_file: MagicMock,
        mock_exists: MagicMock,
        mock_sys_exit: MagicMock,
    ) -> None:
        """Test certificate generation when directory creation fails."""
        mock_exists.return_value = False
        mock_mkdir.return_value = None

        handler = CertificateHandler(mock_certificate_config)

        with pytest.raises(SystemExit):
            handler.generate_self_signed_cert()

        mock_sys_exit.assert_called_once_with(1)

    def test_generate_self_signed_cert_permission_error(
        self, mock_certificate_config: CertificateConfigModel, tmp_path: Path
    ) -> None:
        """Test certificate generation handles PermissionError."""
        cert_dir = tmp_path / "certs"
        cert_dir.mkdir()
        mock_certificate_config.directory = str(cert_dir)

        handler = CertificateHandler(mock_certificate_config)

        # Mock write_to_key_file to raise PermissionError
        with patch.object(handler, "write_to_key_file", side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError, match="Permission denied"):
                handler.generate_self_signed_cert()

    def test_generate_self_signed_cert_os_error(
        self, mock_certificate_config: CertificateConfigModel, tmp_path: Path
    ) -> None:
        """Test certificate generation handles OSError."""
        cert_dir = tmp_path / "certs"
        cert_dir.mkdir()
        mock_certificate_config.directory = str(cert_dir)

        handler = CertificateHandler(mock_certificate_config)

        # Mock write_to_cert_file to raise OSError
        with patch.object(handler, "write_to_cert_file", side_effect=OSError("Disk full")):
            with pytest.raises(OSError, match="Disk full"):
                handler.generate_self_signed_cert()


class TestGenerateSelfSignedCertificate:
    """Unit tests for the generate_self_signed_certificate function."""

    def test_generate_self_signed_certificate_success(
        self, mock_example_server: MagicMock, mock_template_server_config: TemplateServerConfig, tmp_path: Path
    ) -> None:
        """Test successful certificate generation via wrapper function."""
        with (
            patch.object(CertificateHandler, "write_to_key_file") as mock_write_key,
            patch.object(CertificateHandler, "write_to_cert_file") as mock_write_cert,
        ):
            generate_self_signed_certificate()

            # Verify write methods were called with PEM-encoded data
            mock_write_key.assert_called_once()
            key_data = mock_write_key.call_args[0][0]
            assert b"BEGIN RSA PRIVATE KEY" in key_data

            mock_write_cert.assert_called_once()
            cert_data = mock_write_cert.call_args[0][0]
            assert b"BEGIN CERTIFICATE" in cert_data

    def test_generate_self_signed_certificate_os_error(
        self,
        mock_example_server: MagicMock,
        mock_template_server_config: TemplateServerConfig,
        mock_sys_exit: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test certificate generation wrapper handles OSError."""
        with patch(
            "python_template_server.certificate_handler.CertificateHandler.generate_self_signed_cert",
            side_effect=OSError("Disk error"),
        ):
            with pytest.raises(SystemExit):
                generate_self_signed_certificate()

        mock_sys_exit.assert_called_once_with(1)

    def test_generate_self_signed_certificate_permission_error(
        self,
        mock_example_server: MagicMock,
        mock_template_server_config: TemplateServerConfig,
        mock_sys_exit: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test certificate generation wrapper handles PermissionError."""
        with patch(
            "python_template_server.certificate_handler.CertificateHandler.generate_self_signed_cert",
            side_effect=PermissionError("No permission"),
        ):
            with pytest.raises(SystemExit):
                generate_self_signed_certificate()

        mock_sys_exit.assert_called_once_with(1)

    def test_generate_self_signed_certificate_unexpected_error(
        self,
        mock_example_server: MagicMock,
        mock_template_server_config: TemplateServerConfig,
        mock_sys_exit: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test certificate generation wrapper handles unexpected exceptions."""
        with patch(
            "python_template_server.certificate_handler.CertificateHandler.generate_self_signed_cert",
            side_effect=RuntimeError("Unexpected error"),
        ):
            with pytest.raises(SystemExit):
                generate_self_signed_certificate()

        mock_sys_exit.assert_called_once_with(1)
