import platform
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from pdftopng.ktx import KTX2Converter
import subprocess
import zipfile
import tarfile
from PIL import Image


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def converter(temp_dir):
    """Create a KTX2Converter instance with temporary directory"""
    return KTX2Converter(binaries_dir=str(temp_dir / "ktx_binaries"))


@pytest.fixture
def sample_png(temp_dir):
    """Create a sample PNG file for testing"""
    img = Image.new("RGB", (100, 100), color="red")
    png_path = temp_dir / "test.png"
    img.save(png_path, "PNG")
    return png_path


class TestKTX2ConverterInit:
    """Tests for KTX2Converter initialization"""

    def test_init_default_binaries_dir(self):
        """Test initialization with default binaries directory"""
        converter = KTX2Converter()
        assert converter.binaries_dir == Path("./ktx_binaries")
        assert converter.system == platform.system().lower()

    def test_init_custom_binaries_dir(self, temp_dir):
        """Test initialization with custom binaries directory"""
        custom_dir = temp_dir / "custom_ktx"
        converter = KTX2Converter(binaries_dir=str(custom_dir))
        assert converter.binaries_dir == custom_dir

    @patch("platform.system")
    def test_init_windows_system(self, mock_system, temp_dir):
        """Test initialization on Windows"""
        mock_system.return_value = "Windows"
        converter = KTX2Converter(binaries_dir=str(temp_dir))
        assert converter.system == "windows"
        assert converter.executable_name == "toktx.exe"

    @patch("platform.system")
    def test_init_linux_system(self, mock_system, temp_dir):
        """Test initialization on Linux"""
        mock_system.return_value = "Linux"
        converter = KTX2Converter(binaries_dir=str(temp_dir))
        assert converter.system == "linux"
        assert converter.executable_name == "toktx"

    @patch("platform.system")
    def test_init_macos_system(self, mock_system, temp_dir):
        """Test initialization on macOS"""
        mock_system.return_value = "Darwin"
        converter = KTX2Converter(binaries_dir=str(temp_dir))
        assert converter.system == "darwin"
        assert converter.executable_name == "toktx"


class TestExecutableName:
    """Tests for _get_executable_name method"""

    @patch("platform.system")
    def test_get_executable_name_windows(self, mock_system, temp_dir):
        """Test executable name for Windows"""
        mock_system.return_value = "Windows"
        converter = KTX2Converter(binaries_dir=str(temp_dir))
        assert converter._get_executable_name() == "toktx.exe"

    @patch("platform.system")
    def test_get_executable_name_unix(self, mock_system, temp_dir):
        """Test executable name for Unix-like systems"""
        for system_name in ["Linux", "Darwin"]:
            mock_system.return_value = system_name
            converter = KTX2Converter(binaries_dir=str(temp_dir))
            assert converter._get_executable_name() == "toktx"


class TestDownloadUrl:
    """Tests for _get_download_url method"""

    @patch("platform.system")
    def test_get_download_url_windows(self, mock_system, temp_dir):
        """Test download URL for Windows"""
        mock_system.return_value = "Windows"
        converter = KTX2Converter(binaries_dir=str(temp_dir))
        url = converter._get_download_url()
        assert "Windows.zip" in url

    @patch("platform.system")
    def test_get_download_url_linux(self, mock_system, temp_dir):
        """Test download URL for Linux"""
        mock_system.return_value = "Linux"
        converter = KTX2Converter(binaries_dir=str(temp_dir))
        url = converter._get_download_url()
        assert "Linux.tar.gz" in url

    @patch("platform.system")
    def test_get_download_url_macos(self, mock_system, temp_dir):
        """Test download URL for macOS"""
        mock_system.return_value = "Darwin"
        converter = KTX2Converter(binaries_dir=str(temp_dir))
        url = converter._get_download_url()
        assert "macOS.tar.gz" in url

    @patch("platform.system")
    def test_get_download_url_unsupported_platform(self, mock_system, temp_dir):
        """Test download URL for unsupported platform"""
        mock_system.return_value = "UnsupportedOS"
        converter = KTX2Converter(binaries_dir=str(temp_dir))
        with pytest.raises(RuntimeError, match="Unsupported platform"):
            converter._get_download_url()


class TestAvailability:
    """Tests for availability checking methods"""

    def test_is_available_false_when_not_exists(self, converter):
        """Test is_available returns False when executable doesn't exist"""
        assert not converter.is_available()

    def test_is_available_true_when_exists(self, converter, temp_dir):
        """Test is_available returns True when executable exists"""
        # Create the binaries directory and executable file
        converter.binaries_dir.mkdir(parents=True, exist_ok=True)
        converter.executable_path.touch()
        assert converter.is_available()

    def test_ensure_available_when_already_available(self, converter, temp_dir):
        """Test ensure_available when already available"""
        converter.binaries_dir.mkdir(parents=True, exist_ok=True)
        converter.executable_path.touch()

        with patch.object(converter, "download_binaries") as mock_download:
            result = converter.ensure_available()
            assert result is True
            mock_download.assert_not_called()

    def test_ensure_available_when_not_available(self, converter):
        """Test ensure_available when not available"""
        with patch.object(
            converter, "download_binaries", return_value=True
        ) as mock_download:
            result = converter.ensure_available()
            assert result is True
            mock_download.assert_called_once()


class TestDownloadBinaries:
    """Tests for download_binaries method"""

    def test_download_binaries_already_exists_no_force(self, converter, temp_dir):
        """Test download_binaries when executable already exists and force=False"""
        converter.binaries_dir.mkdir(parents=True, exist_ok=True)
        converter.executable_path.touch()

        result = converter.download_binaries(force=False)
        assert result is True

    @patch("urllib.request.urlretrieve")
    @patch("tempfile.TemporaryDirectory")
    def test_download_binaries_success_zip(
        self, mock_temp_dir, mock_urlretrieve, converter, temp_dir
    ):
        """Test successful binary download for ZIP archive"""
        # Setup temporary directory mock
        temp_path = temp_dir / "temp"
        temp_path.mkdir()
        mock_temp_dir.return_value.__enter__.return_value = str(temp_path)

        # Create a mock ZIP file with toktx executable
        zip_path = temp_path / "ktx_software.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("bin/toktx.exe", "fake executable content")

        # Mock the download URL to return a .zip URL
        with patch.object(
            converter, "_get_download_url", return_value="https://example.com/test.zip"
        ):
            with patch.object(converter, "_extract_zip") as mock_extract:
                # Create the executable in the temp directory for the search
                (temp_path / "toktx.exe").touch()

                result = converter.download_binaries()

                assert result is True
                mock_urlretrieve.assert_called_once()
                mock_extract.assert_called_once()

    @patch("urllib.request.urlretrieve")
    @patch("tempfile.TemporaryDirectory")
    def test_download_binaries_success_tar(
        self, mock_temp_dir, mock_urlretrieve, converter, temp_dir
    ):
        """Test successful binary download for TAR.GZ archive"""
        # Setup temporary directory mock
        temp_path = temp_dir / "temp"
        temp_path.mkdir()
        mock_temp_dir.return_value.__enter__.return_value = str(temp_path)
        # Mock the download URL to return a .tar.gz URL
        with patch.object(
            converter,
            "_get_download_url",
            return_value="https://example.com/test.tar.gz",
        ):
            with patch.object(converter, "_extract_tar") as mock_extract:
                # Create the executable in the temp directory for the search
                (temp_path / converter.executable_name).touch()

                result = converter.download_binaries()

                assert result is True
                mock_urlretrieve.assert_called_once()
                mock_extract.assert_called_once()

    @patch("urllib.request.urlretrieve")
    @patch("tempfile.TemporaryDirectory")
    def test_download_binaries_executable_not_found(
        self, mock_temp_dir, mock_urlretrieve, converter, temp_dir
    ):
        """Test download_binaries when executable is not found in archive"""
        temp_path = temp_dir / "temp"
        temp_path.mkdir()
        mock_temp_dir.return_value.__enter__.return_value = str(temp_path)

        with patch.object(
            converter, "_get_download_url", return_value="https://example.com/test.zip"
        ):
            with patch.object(converter, "_extract_zip"):
                # Don't create the executable file
                result = converter.download_binaries()

                assert result is False

    @patch("urllib.request.urlretrieve", side_effect=Exception("Download failed"))
    def test_download_binaries_download_error(self, mock_urlretrieve, converter):
        """Test download_binaries when download fails"""
        result = converter.download_binaries()
        assert result is False


class TestArchiveExtraction:
    """Tests for archive extraction methods"""

    def test_extract_zip(self, converter, temp_dir):
        """Test ZIP archive extraction"""
        # Create a test ZIP file
        zip_path = temp_dir / "test.zip"
        extract_to = temp_dir / "extracted"
        extract_to.mkdir()

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test_file.txt", "test content")

        converter._extract_zip(zip_path, extract_to)

        assert (extract_to / "test_file.txt").exists()
        assert (extract_to / "test_file.txt").read_text() == "test content"

    def test_extract_tar(self, converter, temp_dir):
        """Test TAR.GZ archive extraction"""
        # Create a test TAR.GZ file
        tar_path = temp_dir / "test.tar.gz"
        extract_to = temp_dir / "extracted"
        extract_to.mkdir()

        # Create a file to add to the tar
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test content")

        with tarfile.open(tar_path, "w:gz") as tf:
            tf.add(test_file, arcname="test_file.txt")

        converter._extract_tar(tar_path, extract_to)

        assert (extract_to / "test_file.txt").exists()
        assert (extract_to / "test_file.txt").read_text() == "test content"


class TestConvert:
    """Tests for convert method"""

    def test_convert_toktx_not_available(self, converter, sample_png, temp_dir):
        """Test convert when toktx is not available"""
        output_path = temp_dir / "output.ktx2"

        with patch.object(converter, "ensure_available", return_value=False):
            with pytest.raises(RuntimeError, match="toktx is not available"):
                converter.convert(str(sample_png), str(output_path))

    def test_convert_input_file_not_found(self, converter, temp_dir):
        """Test convert when input file doesn't exist"""
        input_path = temp_dir / "nonexistent.png"
        output_path = temp_dir / "output.ktx2"

        with patch.object(converter, "ensure_available", return_value=True):
            with pytest.raises(FileNotFoundError, match="Input file not found"):
                converter.convert(str(input_path), str(output_path))

    @patch("subprocess.run")
    def test_convert_success_basic(self, mock_run, converter, sample_png, temp_dir):
        """Test successful basic conversion"""
        output_path = temp_dir / "output.ktx2"
        mock_run.return_value = Mock(stdout="Success", stderr="")

        with patch.object(converter, "ensure_available", return_value=True):
            result = converter.convert(str(sample_png), str(output_path))

            assert result is True
            mock_run.assert_called_once()

            # Verify command structure
            args, kwargs = mock_run.call_args
            cmd = args[0]
            assert str(converter.executable_path) in cmd
            assert "--t2" in cmd
            assert "--genmipmap" in cmd
            assert str(output_path) in cmd
            assert str(sample_png) in cmd

    @patch("subprocess.run")
    def test_convert_success_with_compression(
        self, mock_run, converter, sample_png, temp_dir
    ):
        """Test successful conversion with compression options"""
        output_path = temp_dir / "output.ktx2"
        mock_run.return_value = Mock(stdout="Success", stderr="")

        with patch.object(converter, "ensure_available", return_value=True):
            result = converter.convert(
                str(sample_png), str(output_path), compression="etc1s", quality="128"
            )

            assert result is True
            args, kwargs = mock_run.call_args
            cmd = args[0]
            assert "--encode" in cmd
            assert "etc1s" in cmd
            assert "--qlevel" in cmd
            assert "128" in cmd

    @patch("subprocess.run")
    def test_convert_success_uastc_compression(
        self, mock_run, converter, sample_png, temp_dir
    ):
        """Test successful conversion with UASTC compression"""
        output_path = temp_dir / "output.ktx2"
        mock_run.return_value = Mock(stdout="Success", stderr="")

        with patch.object(converter, "ensure_available", return_value=True):
            result = converter.convert(
                str(sample_png), str(output_path), compression="uastc"
            )

            assert result is True
            args, kwargs = mock_run.call_args
            cmd = args[0]
            assert "--encode" in cmd
            assert "uastc" in cmd

    @patch("subprocess.run")
    def test_convert_success_no_mipmaps(
        self, mock_run, converter, sample_png, temp_dir
    ):
        """Test successful conversion without mipmaps"""
        output_path = temp_dir / "output.ktx2"
        mock_run.return_value = Mock(stdout="Success", stderr="")

        with patch.object(converter, "ensure_available", return_value=True):
            result = converter.convert(
                str(sample_png), str(output_path), generate_mipmaps=False
            )

            assert result is True
            args, kwargs = mock_run.call_args
            cmd = args[0]
            assert "--genmipmap" not in cmd

    @patch("subprocess.run")
    def test_convert_with_additional_args(
        self, mock_run, converter, sample_png, temp_dir
    ):
        """Test conversion with additional keyword arguments"""
        output_path = temp_dir / "output.ktx2"
        mock_run.return_value = Mock(stdout="Success", stderr="")

        with patch.object(converter, "ensure_available", return_value=True):
            result = converter.convert(
                str(sample_png),
                str(output_path),
                custom_arg="value",
                **{"--flag": True, "--option": "test"},
            )

            assert result is True
            args, kwargs = mock_run.call_args
            cmd = args[0]
            assert "--custom_arg" in cmd
            assert "value" in cmd
            assert "--flag" in cmd
            assert "--option" in cmd
            assert "test" in cmd

    @patch("subprocess.run")
    def test_convert_subprocess_error(self, mock_run, converter, sample_png, temp_dir):
        """Test convert when subprocess fails"""
        output_path = temp_dir / "output.ktx2"
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "cmd", stderr="Error occurred"
        )

        with patch.object(converter, "ensure_available", return_value=True):
            result = converter.convert(str(sample_png), str(output_path))

            assert result is False

    def test_convert_creates_output_directory(self, converter, sample_png, temp_dir):
        """Test that convert creates output directory if it doesn't exist"""
        output_path = temp_dir / "subdir" / "another" / "output.ktx2"

        with patch.object(converter, "ensure_available", return_value=True):
            with patch("subprocess.run", return_value=Mock(stdout="", stderr="")):
                converter.convert(str(sample_png), str(output_path))

                assert output_path.parent.exists()


class TestBatchConvert:
    """Tests for batch_convert method"""

    def test_batch_convert_success(self, converter, temp_dir):
        """Test successful batch conversion"""
        # Create input directory with PNG files
        input_dir = temp_dir / "input"
        output_dir = temp_dir / "output"
        input_dir.mkdir()

        # Create test PNG files
        for i in range(3):
            img = Image.new("RGB", (50, 50), color="blue")
            img.save(input_dir / f"test_{i}.png", "PNG")

        with patch.object(converter, "convert", return_value=True) as mock_convert:
            results = converter.batch_convert(str(input_dir), str(output_dir))

            assert len(results) == 3
            assert all(success for success in results.values())
            assert mock_convert.call_count == 3

            # Verify correct file paths were used
            for call_args in mock_convert.call_args_list:
                input_path, output_path = call_args[0]
                assert input_path.endswith(".png")
                assert output_path.endswith(".ktx2")

    def test_batch_convert_custom_pattern(self, converter, temp_dir):
        """Test batch conversion with custom file pattern"""
        input_dir = temp_dir / "input"
        output_dir = temp_dir / "output"
        input_dir.mkdir()
        # Create files with different extensions
        for ext, format_name in [("png", "PNG"), ("jpg", "JPEG"), ("gif", "GIF")]:
            img = Image.new("RGB", (50, 50), color="green")
            img.save(input_dir / f"test.{ext}", format_name)

        with patch.object(converter, "convert", return_value=True) as mock_convert:
            results = converter.batch_convert(
                str(input_dir), str(output_dir), pattern="*.jpg"
            )

            assert len(results) == 1
            assert mock_convert.call_count == 1

            # Verify only JPG file was processed
            call_args = mock_convert.call_args_list[0]
            input_path = call_args[0][0]
            assert input_path.endswith("test.jpg")

    def test_batch_convert_with_convert_kwargs(self, converter, temp_dir):
        """Test batch conversion with conversion arguments"""
        input_dir = temp_dir / "input"
        output_dir = temp_dir / "output"
        input_dir.mkdir()

        img = Image.new("RGB", (50, 50), color="yellow")
        img.save(input_dir / "test.png", "PNG")

        with patch.object(converter, "convert", return_value=True) as mock_convert:
            results = converter.batch_convert(
                str(input_dir), str(output_dir), compression="etc1s", quality="100"
            )

            assert len(results) == 1
            call_args, call_kwargs = mock_convert.call_args
            assert call_kwargs["compression"] == "etc1s"
            assert call_kwargs["quality"] == "100"

    def test_batch_convert_mixed_results(self, converter, temp_dir):
        """Test batch conversion with mixed success/failure results"""
        input_dir = temp_dir / "input"
        output_dir = temp_dir / "output"
        input_dir.mkdir()

        # Create test files
        for i in range(3):
            img = Image.new("RGB", (50, 50), color="red")
            img.save(input_dir / f"test_{i}.png", "PNG")

        # Mock convert to return different results
        def mock_convert_side_effect(*args, **kwargs):
            filename = Path(args[0]).name
            return filename != "test_1.png"  # Fail for test_1.png

        with patch.object(converter, "convert", side_effect=mock_convert_side_effect):
            results = converter.batch_convert(str(input_dir), str(output_dir))

            assert len(results) == 3
            assert results["test_0.png"] is True
            assert results["test_1.png"] is False
            assert results["test_2.png"] is True


class TestIntegration:
    """Integration tests combining multiple components"""

    def test_full_workflow_mock(self, temp_dir):
        """Test full workflow with mocked dependencies"""
        # Create converter with temporary directory
        converter = KTX2Converter(binaries_dir=str(temp_dir / "ktx_binaries"))

        # Create sample PNG
        img = Image.new("RGB", (100, 100), color="purple")
        input_png = temp_dir / "input.png"
        img.save(input_png, "PNG")

        output_ktx = temp_dir / "output.ktx2"

        # Mock all external dependencies
        with patch.object(converter, "download_binaries", return_value=True):
            with patch(
                "subprocess.run", return_value=Mock(stdout="Success", stderr="")
            ):
                # Simulate executable exists
                converter.binaries_dir.mkdir(parents=True, exist_ok=True)
                converter.executable_path.touch()

                # Test the conversion
                result = converter.convert(
                    str(input_png), str(output_ktx), compression="etc1s", quality="128"
                )

                assert result is True

    @patch("platform.system")
    def test_cross_platform_initialization(self, mock_system, temp_dir):
        """Test that converter works across different platforms"""
        platforms = [
            ("Windows", "toktx.exe", "Windows.zip"),
            ("Linux", "toktx", "Linux.tar.gz"),
            ("Darwin", "toktx", "macOS.tar.gz"),
        ]

        for platform_name, expected_exe, expected_url_part in platforms:
            mock_system.return_value = platform_name
            converter = KTX2Converter(binaries_dir=str(temp_dir))

            assert converter.executable_name == expected_exe
            assert expected_url_part in converter._get_download_url()
