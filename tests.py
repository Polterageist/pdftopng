from main import validate_dimensions, validate_tiles
import pytest
import sys
import os
from pathlib import Path
from convert import convert
import shutil
from PIL import Image
import re

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


@pytest.fixture(autouse=True)
def cleanup_output_dirs(tmp_path):
    output_dir = tmp_path / "output"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    yield
    if output_dir.exists():
        shutil.rmtree(output_dir)


@pytest.mark.parametrize(
    "dimensions",
    [
        "1920x1080",
        "131072x131072",
        "800x600",
        "1000x2000",
        "1920х1080",  # cyrillic x
        "1920X1080",  # uppercase X
        "1920 x 1080",  # spaces
        "1,920x1,080",  # commas
    ],
)
def test_validate_dimensions_valid(dimensions):
    width, height = validate_dimensions(dimensions)
    assert width > 0 and height > 0


@pytest.mark.parametrize(
    "dimensions",
    [
        "1920-1080",
        "1920",
        "x1080",
        "1920x0",
        "0x1080",
        "-1920x1080",
        "1920x-1080",
        "abcxdef",
        "",
    ],
)
def test_validate_dimensions_invalid(dimensions):
    with pytest.raises(Exception):
        validate_dimensions(dimensions)


@pytest.mark.parametrize(
    "tiles",
    [
        "4x3",
        "32x32",
        "1x1",
        "10x20",
        "4х3",  # cyrillic x
        "4X3",  # uppercase X
        "4 x 3",  # spaces
    ],
)
def test_validate_tiles_valid(tiles):
    n, m = validate_tiles(tiles)
    assert n > 0 and m > 0


@pytest.mark.parametrize(
    "tiles",
    [
        "4-3",
        "4",
        "x3",
        "0x3",
        "4x0",
        "-4x3",
        "4x-3",
        "abcxdef",
        "",
    ],
)
def test_validate_tiles_invalid(tiles):
    with pytest.raises(Exception):
        validate_tiles(tiles)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source, destination_dir, dimensions, tiles",
    [
        (Path("test_data/example.pdf"), Path("test_output"), (1920, 1080), (4, 3)),
        (Path("test_data/example.pdf"), Path("test_output"), (131072, 131072), (32, 32)),
    ],
)
async def test_convert_runs_without_error(source, destination_dir, dimensions, tiles):
    await convert(source, destination_dir, dimensions, tiles)


@pytest.mark.asyncio
async def test_convert_output(tmp_path):
    source = Path("test_data/example.pdf")
    destination_dir = Path("test_output")
    dimensions = (192, 96)
    tiles = (3, 2)
    await convert(source, destination_dir, dimensions, tiles)
    base_name = source.stem
    tile_w = dimensions[0] // tiles[0]
    tile_h = dimensions[1] // tiles[1]
    files = list(destination_dir.glob("*.png"))
    assert len(files) == tiles[0] * tiles[1]
    pattern = re.compile(rf"{base_name}-tile-(\\d+)-(\\d+).png")
    for file in files:
        match = pattern.fullmatch(file.name)
        assert match is not None
        img = Image.open(file)
        assert img.size == (tile_w, tile_h)
