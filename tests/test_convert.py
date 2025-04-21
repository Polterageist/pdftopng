import pytest
import asyncio
from pathlib import Path
from pdftopng.convert import convert
from PIL import Image
import re
import shutil


@pytest.fixture(autouse=True)
def cleanup_output_dirs():
    output_dir = Path("test_output")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    yield
    if output_dir.exists():
        shutil.rmtree(output_dir)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source, destination_dir, dimensions, tiles",
    [
        (Path("test_data/example.pdf"), Path("test_output"), (1920, 1080), (4, 3)),
        (Path("test_data/example.pdf"), Path("test_output"), (192, 96), (3, 2)),
    ],
)
async def test_convert_runs_without_error(source, destination_dir, dimensions, tiles):
    await asyncio.wait_for(
        convert(source, destination_dir, dimensions, tiles), timeout=30
    )


@pytest.mark.asyncio
async def test_convert_output():
    source = Path("test_data/example.pdf")
    destination_dir = Path("test_output")
    dimensions = (192, 96)
    tiles = (3, 2)
    await asyncio.wait_for(
        convert(source, destination_dir, dimensions, tiles), timeout=30
    )
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


@pytest.mark.asyncio
async def test_convert_progress_reporting():
    source = Path("test_data/example.pdf")
    destination_dir = Path("test_output")
    dimensions = (192, 96)
    tiles = (3, 2)
    progress_calls = []

    async def progress_callback(processed, total):
        progress_calls.append((processed, total))

    await asyncio.wait_for(
        convert(
            source,
            destination_dir,
            dimensions,
            tiles,
            progress_callback=progress_callback,
        ),
        timeout=30,
    )
    assert progress_calls[0] == (1, 6)
    assert progress_calls[-1] == (6, 6)
    assert all(1 <= p[0] <= 6 and p[1] == 6 for p in progress_calls)
    assert len(progress_calls) == 6
