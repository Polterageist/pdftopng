from main import validate_dimensions, validate_tiles
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


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
