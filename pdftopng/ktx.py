import os
import platform
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict
import tempfile
import urllib.request
import zipfile
import tarfile


class KTX2Converter:
    """Cross-platform PNG -> KTX2 converter with automatic binary download"""

    # URLs for downloading binaries (latest version of KTX-Software)
    DOWNLOAD_URLS = {
        "windows": "https://github.com/KhronosGroup/KTX-Software/releases/latest/download/KTX-Software-Windows.zip",
        "linux": "https://github.com/KhronosGroup/KTX-Software/releases/latest/download/KTX-Software-Linux.tar.gz",
        "darwin": "https://github.com/KhronosGroup/KTX-Software/releases/latest/download/KTX-Software-macOS.tar.gz",
    }

    def __init__(self, binaries_dir: Optional[str] = None):
        """
        Initialize the converter

        Args:
            binaries_dir: Path to the binaries directory. If None, uses ./ktx_binaries
        """
        self.system = platform.system().lower()
        self.binaries_dir = Path(binaries_dir or "./ktx_binaries")
        self.executable_name = self._get_executable_name()
        self.executable_path = self.binaries_dir / self.executable_name

    def _get_executable_name(self) -> str:
        """Gets the executable name for the current platform"""
        if self.system == "windows":
            return "toktx.exe"
        else:
            return "toktx"

    def _get_download_url(self) -> str:
        """Gets the download URL for binaries for the current platform"""
        system_map = {"windows": "windows", "linux": "linux", "darwin": "darwin"}

        if self.system not in system_map:
            raise RuntimeError(f"Unsupported platform: {self.system}")

        return self.DOWNLOAD_URLS[system_map[self.system]]

    def download_binaries(self, force: bool = False) -> bool:
        """
        Downloads and installs toktx binaries

        Args:
            force: Force download even if files already exist        Returns:
            True if download was successful
        """
        if self.executable_path.exists() and not force:
            print(f"Binaries already installed: {self.executable_path}")
            return True

        print(f"Downloading binaries for {self.system}...")

        # Create directory for binaries
        self.binaries_dir.mkdir(parents=True, exist_ok=True)

        try:
            download_url = self._get_download_url()

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)                
                # Determine archive type by URL
                if download_url.endswith(".zip"):
                    archive_path = temp_path / "ktx_software.zip"
                    extract_func = self._extract_zip
                else:
                    archive_path = temp_path / "ktx_software.tar.gz"
                    extract_func = self._extract_tar

                # Download archive
                print(f"Downloading from {download_url}")
                urllib.request.urlretrieve(download_url, archive_path)

                # Extract binaries
                extract_func(archive_path, temp_path)

                # Find and copy toktx
                toktx_found = False
                for file_path in temp_path.rglob(self.executable_name):
                    shutil.copy2(file_path, self.executable_path)
                    toktx_found = True
                    break

                if not toktx_found:
                    raise FileNotFoundError(
                        f"{self.executable_name} not found in archive"
                    )

                # Make executable (for Unix systems)
                if self.system != "windows":
                    os.chmod(self.executable_path, 0o755)

                print(f"Binaries installed: {self.executable_path}")
                return True

        except Exception as e:
            print(f"Error downloading binaries: {e}")
            return False

    def _extract_zip(self, archive_path: Path, extract_to: Path):
        """Extracts ZIP archive"""
        with zipfile.ZipFile(archive_path, "r") as zip_file:
            zip_file.extractall(extract_to)

    def _extract_tar(self, archive_path: Path, extract_to: Path):
        """Extracts TAR.GZ archive"""
        with tarfile.open(archive_path, "r:gz") as tar_file:
            tar_file.extractall(extract_to)

    def is_available(self) -> bool:
        """Checks toktx availability"""
        return self.executable_path.exists() and self.executable_path.is_file()

    def ensure_available(self) -> bool:
        """Ensures toktx is available, downloads if necessary"""
        if self.is_available():
            return True
        return self.download_binaries()

    def convert(
        self,
        input_path: str,
        output_path: str,
        generate_mipmaps: bool = True,
        compression: Optional[str] = None,
        quality: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """
        Converts PNG to KTX2

        Args:
            input_path: Path to input PNG file
            output_path: Path to output KTX2 file
            generate_mipmaps: Generate mipmaps
            compression: Compression type ('etc1s', 'uastc', None)
            quality: Compression quality for ETC1S (0-255)
            **kwargs: Additional arguments for toktx

        Returns:
            True if conversion was successful
        """
        if not self.ensure_available():
            raise RuntimeError("toktx is not available")

        # Check input file
        if not Path(input_path).exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Create directory for output file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Build command
        cmd = [str(self.executable_path)]        # Add flag for KTX2
        cmd.append("--t2")

        # Generate mipmaps
        if generate_mipmaps:
            cmd.append("--genmipmap")

        # Compression
        if compression:
            if compression.lower() == "etc1s":
                cmd.append("--encode")
                cmd.append("etc1s")
                if quality is not None:
                    cmd.extend(["--qlevel", str(quality)])
            elif compression.lower() == "uastc":
                cmd.append("--encode")
                cmd.append("uastc")
            elif compression.lower() == "zstd":
                cmd.append("--zstd")
            elif compression.lower() == "zlib":
                cmd.append("--zlib")

        # Additional arguments
        for key, value in kwargs.items():
            if key.startswith("--"):
                cmd.append(key)
                if value is not None and value is not True:
                    cmd.append(str(value))
            else:
                cmd.extend([f"--{key}", str(value)])        # Add file paths
        cmd.extend([output_path, input_path])

        try:
            print(f"Executing: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("Conversion completed successfully")
            if result.stdout:
                print(f"Output: {result.stdout}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"Conversion error: {e}")
            if e.stderr:
                print(f"Error: {e.stderr}")
            return False

    def batch_convert(
        self, input_dir: str, output_dir: str, pattern: str = "*.png", **convert_kwargs
    ) -> Dict[str, bool]:
        """
        Batch conversion of files

        Args:
            input_dir: Input directory
            output_dir: Output directory
            pattern: Pattern for finding files
            **convert_kwargs: Arguments for convert()

        Returns:
            Dictionary {filename: success}
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)

        results = {}

        for file_path in input_path.glob(pattern):
            relative_path = file_path.relative_to(input_path)
            output_file = output_path / relative_path.with_suffix(".ktx2")

            print(f"Converting: {file_path} -> {output_file}")
            success = self.convert(str(file_path), str(output_file), **convert_kwargs)
            results[str(relative_path)] = success

        return results
