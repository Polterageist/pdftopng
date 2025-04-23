import io
import pytest
import asyncio
from pathlib import Path
from pdftopng.convert import convert
from PIL import Image
import re
import shutil
import pymupdf


test_dir = Path(__file__).parent / "tests_temp"
source = test_dir / "test.pdf"
destination_dir = test_dir / "output"


@pytest.fixture(autouse=True)
def cleanup_output_dirs():
    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)
    test_dir.mkdir(parents=True, exist_ok=True)
    yield


def generate_test_pdf(output_path, dimensions, tiles) -> None:
    """
    Generate a simple PDF file with a single page of specified dimensions and colorcoded grid of tiles
    """
    with pymupdf.open() as doc:
        page = doc.new_page(width=dimensions[0], height=dimensions[1])

        width, height = dimensions
        tiles_x, tiles_y = tiles
        tile_width = width / tiles_x
        tile_height = height / tiles_y

        for x in range(tiles[0]):
            for y in range(tiles[1]):
                # Calculate the tile rect and color
                tile_index = x * tiles[1] + y
                tl = (
                    x * tile_width,
                    y * tile_height,
                )
                br = (
                    (x + 1) * tile_width,
                    (y + 1) * tile_height,
                )

                rect = pymupdf.Rect(tl[0], tl[1], br[0], br[1])

                index_bytes = tile_index.to_bytes(3, byteorder="big")
                color = tuple(index_bytes)  # RGB color from tile index
                with Image.new(
                    "RGB", (int(tile_width), int(tile_height)), color
                ) as img:
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format="PNG")
                    img_bytes.seek(0)
                page.insert_image(
                    rect,
                    stream=img_bytes.getvalue(),
                    keep_proportion=True,
                )

        doc.save(str(output_path), garbage=4, deflate=True, clean=True)


@pytest.mark.parametrize(
    "dimensions, tiles",
    [
        ((10, 10), (1, 1)),
        ((100, 100), (10, 10)),
        ((1000, 1000), (10, 10)),
    ],
)
def test_generate_test_pdf(dimensions, tiles):
    assert dimensions[0] % tiles[0] == 0 and dimensions[1] % tiles[1] == 0
    output_path = source
    generate_test_pdf(output_path, dimensions, tiles)

    assert output_path.exists()
    with pymupdf.open(str(output_path)) as doc:
        assert len(doc) == 1
        page = doc[0]
        rect = page.rect
        assert rect.width == dimensions[0]
        assert rect.height == dimensions[1]
        images = page.get_images(full=True)
        assert len(images) == tiles[0] * tiles[1]

        tile_x, tile_y = (0, 0)

        for img in images:
            rects = page.get_image_rects(img[0])
            assert len(rects) == 1
            rect = rects[0]
            assert rect.width == dimensions[0] / tiles[0]
            assert rect.height == dimensions[1] / tiles[1]
            assert rect.x0 == tile_x * (dimensions[0] / tiles[0])
            assert rect.y0 == tile_y * (dimensions[1] / tiles[1])
            assert rect.x1 == (tile_x + 1) * (dimensions[0] / tiles[0])
            assert rect.y1 == (tile_y + 1) * (dimensions[1] / tiles[1])

            base_image = doc.extract_image(img[0])
            image_bytes = base_image["image"]
            image = Image.open(io.BytesIO(image_bytes))
            assert image.format == "PNG"
            assert image.mode == "RGB"

            # Check if the image color matches the expected color
            tile_index = tile_x * tiles[1] + tile_y
            index_bytes = tile_index.to_bytes(3, byteorder="big")
            expected_color = tuple(index_bytes)
            for x in range(image.width):
                for y in range(image.height):
                    pixel = image.getpixel((x, y))
                    assert pixel == expected_color

            tile_y += 1
            if tile_y > tiles[1] - 1:
                tile_x += 1
                tile_y = 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_dimensions, target_dimensions, tiles",
    [
        ((100, 100), (1000, 1000), (10, 10)),
    ],
)
async def test_convert_output(source_dimensions, target_dimensions, tiles):
    generate_test_pdf(source, source_dimensions, tiles)
    await asyncio.wait_for(
        convert(source, destination_dir, target_dimensions, tiles), timeout=200
    )

    assert destination_dir.exists()
    base_name = source.stem
    actual_width, actual_height = 0, 0
    files = list(destination_dir.glob("*.png"))
    assert len(files) == tiles[0] * tiles[1]
    pattern = re.compile(rf"{base_name}-tile-(\\d+)-(\\d+).png")
    for file in files:
        match = pattern.fullmatch(file.name)
        assert match is not None
        with Image.open(file) as img:
            assert img.format == "PNG"
            assert img.mode == "RGB"

            actual_height += img.width
            actual_width += img.height

    assert actual_width == target_dimensions[0]
    assert actual_height == target_dimensions[1]
