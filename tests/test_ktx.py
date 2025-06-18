import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from pdftopng.ktx import KTX2Converter, generate_mips
from PIL import Image
from math import log2


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_png(temp_dir):
    """Create a sample PNG file for testing"""
    img = Image.new("RGB", (100, 100), color="red")
    png_path = temp_dir / "test.png"
    img.save(png_path, "PNG")
    return png_path


class TestConvert:
    """Tests for convert method"""

    def test_convert_success(self, sample_png, tmp_path, monkeypatch):
        # Mock pyktx and PIL
        mock_texture = MagicMock()
        monkeypatch.setattr(
            "pdftopng.ktx.Image.open", lambda path: Image.new("RGB", (10, 10))
        )
        monkeypatch.setattr("pdftopng.ktx.KtxTextureCreateInfo", MagicMock)
        monkeypatch.setattr(
            "pdftopng.ktx.KtxTexture2.create", MagicMock(return_value=mock_texture)
        )
        monkeypatch.setattr("pdftopng.ktx.KtxTextureCreateStorage", MagicMock())
        monkeypatch.setattr("pdftopng.ktx.VkFormat", MagicMock())
        mock_texture.set_image_from_memory.return_value = None
        mock_texture.write_to_named_file.return_value = None

        converter = KTX2Converter()
        out_path = tmp_path / "out.ktx2"
        result = converter.convert(str(sample_png), str(out_path))
        assert result is True
        mock_texture.set_image_from_memory.assert_called()
        mock_texture.write_to_named_file.assert_called_with(str(out_path))

    def test_convert_failure(self, tmp_path, monkeypatch):
        # Simulate PIL open failure
        monkeypatch.setattr(
            "pdftopng.ktx.Image.open", MagicMock(side_effect=OSError("fail"))
        )
        converter = KTX2Converter()
        result = converter.convert("bad.png", str(tmp_path / "fail.ktx2"))
        assert result is False

    def test_batch_convert_success(self, tmp_path, monkeypatch):
        # Prepare fake PNGs
        in_dir = tmp_path / "in"
        out_dir = tmp_path / "out"
        in_dir.mkdir()
        (in_dir / "a.png").write_bytes(b"fake")
        (in_dir / "b.png").write_bytes(b"fake")
        # Patch convert to always True
        monkeypatch.setattr(KTX2Converter, "convert", MagicMock(return_value=True))
        converter = KTX2Converter()
        results = converter.batch_convert(str(in_dir), str(out_dir))
        assert results == {"a.png": True, "b.png": True}

    def test_batch_convert_partial_failure(self, tmp_path, monkeypatch):
        in_dir = tmp_path / "in"
        out_dir = tmp_path / "out"
        in_dir.mkdir()
        (in_dir / "a.png").write_bytes(b"fake")
        (in_dir / "b.png").write_bytes(b"fake")

        # Patch convert to fail for b.png
        def fake_convert(self, input_path, output_path, *args, **kwargs):
            return "b.png" not in input_path

        monkeypatch.setattr(KTX2Converter, "convert", fake_convert)
        converter = KTX2Converter()
        results = converter.batch_convert(str(in_dir), str(out_dir))
        assert results == {"a.png": True, "b.png": False}

    def test_convert_creates_ktx2_with_mips(self, sample_png, tmp_path):
        from pyktx import KtxTexture2
        converter = KTX2Converter()
        out_path = tmp_path / "out.ktx2"
        result = converter.convert(str(sample_png), str(out_path))
        assert result is True
        assert out_path.exists(), "ktx2 файл не создан"

        tex = KtxTexture2.create_from_named_file(str(out_path))
        # Количество мипов должно совпадать с log2(max(width, height)) + 1
        img = Image.open(sample_png)
        expected_mips = int(log2(max(img.width, img.height))) + 1
        assert tex.num_levels == expected_mips, f"Ожидалось мипов: {expected_mips}, а в файле: {tex.num_levels}"
        # Проверяем размеры каждого мипа
        for level in range(tex.num_levels):
            w = max(1, img.width // (2 ** level))
            h = max(1, img.height // (2 ** level))
            assert tex.base_width // (2 ** level) == w
            assert tex.base_height // (2 ** level) == h


class TestGenerateMips:
    """Tests for generate_mips function"""

    def test_generate_mips_sizes(self):
        img = Image.new("RGB", (64, 32), color="blue")
        mips = generate_mips(img)
        # Количество уровней: log2(max(64,32))+1 = 7, всего 7 уровней
        assert len(mips) == 7
        expected_sizes = [(64, 32)]
        w, h = 64, 32
        for _ in range(6):
            w, h = max(1, w // 2), max(1, h // 2)
            expected_sizes.append((w, h))
        sizes = [mip.size for mip in mips]
        assert sizes == expected_sizes

    def test_generate_mips_minimum(self):
        img = Image.new("RGB", (1, 1), color="green")
        mips = generate_mips(img)
        assert len(mips) == 1
        assert mips[0].size == (1, 1)

    def test_generate_mips_square(self):
        img = Image.new("RGB", (8, 8), color="red")
        mips = generate_mips(img)
        assert len(mips) == 4  # 8,4,2,1
        sizes = [mip.size for mip in mips]
        assert sizes == [(8, 8), (4, 4), (2, 2), (1, 1)]
