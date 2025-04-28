import pytest
from pdftopng.main import validate_dimensions


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
