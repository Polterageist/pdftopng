import io
import pytest
import asyncio
from pathlib import Path
from pdftopng.convert import convert, render_pdf_rect
from PIL import Image, ImageColor
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


def generate_test_pdf(output_path, dimensions, tiles, codingmode="index") -> None:
    """
    Generate a simple PDF file with a single page of specified dimensions and colorcoded grid of tiles
    Parameters:
        output_path (Path): Path to the output PDF file.
        dimensions (Tuple[int, int]): Dimensions of the PDF page (width, height).
        tiles (Tuple[int, int]): Number of tiles in the grid (columns, rows).
        codingmode (str): Color mode for the tiles. Default is "index", which uses colorcoding for tile index.
        Other options can be "checkerboard", which uses a checkerboard pattern.
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
                color = (
                    tuple(index_bytes)
                    if codingmode == "index"
                    else (
                        ImageColor.getrgb("black")
                        if (x + y) % 2 == 0
                        else ImageColor.getrgb("white")
                    )
                )
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


def is_image_filled_with(image, color):
    """
    Check if the image is filled with a specific color.
    Parameters:
        image (PIL.Image): The image to check.
        color (tuple): The color to check against (R, G, B).
    Returns:
        bool: True if the image is filled with the specified color, False otherwise.
    """
    for x in range(image.width):
        for y in range(image.height):
            if image.getpixel((x, y)) != color:
                return False
    return True


@pytest.mark.parametrize(
    "dimensions, tiles, colormode",
    [
        ((10, 10), (1, 1), "index"),
        ((10, 10), (1, 1), "checkerboard"),
        ((100, 100), (10, 10), "index"),
        ((100, 100), (10, 10), "checkerboard"),
    ],
)
def test_generate_test_pdf(dimensions, tiles, colormode):
    assert dimensions[0] % tiles[0] == 0 and dimensions[1] % tiles[1] == 0
    output_path = source
    generate_test_pdf(output_path, dimensions, tiles, colormode)

    assert output_path.exists()
    with pymupdf.open(str(output_path)) as doc:
        assert len(doc) == 1
        page = doc[0]
        rect = page.rect
        assert rect.width == dimensions[0]
        assert rect.height == dimensions[1]
        images = page.get_images(full=True)
        assert len(images) == tiles[0] * tiles[1]
        tile_width = dimensions[0] / tiles[0]
        tile_height = dimensions[1] / tiles[1]

        for img in images:
            rects = page.get_image_rects(img[0])
            for rect in rects:
                assert rect.width == tile_width
                assert rect.height == tile_height
                tile_x = int(rect.x0 / tile_width)
                tile_y = int(rect.y0 / tile_height)
                assert rect.x1 == (tile_x + 1) * tile_width
                assert rect.y1 == (tile_y + 1) * tile_height

                base_image = doc.extract_image(img[0])
                image_bytes = base_image["image"]
                with Image.open(io.BytesIO(image_bytes)) as image:
                    assert image.format == "PNG"
                    assert image.mode == "RGB"

                    # Check if the image color matches the expected color
                    tile_index = tile_x * tiles[1] + tile_y
                    index_bytes = tile_index.to_bytes(3, byteorder="big")
                    expected_color = (
                        tuple(index_bytes)
                        if colormode == "index"
                        else (
                            ImageColor.getcolor("black", image.mode)
                            if (tile_x + tile_y) % 2 == 0
                            else ImageColor.getcolor("white", image.mode)
                        )
                    )
                    assert is_image_filled_with(image, expected_color)


@pytest.mark.parametrize(
    "source_dimensions, tiles, target_dimensions, tile_pos, colorspace, target_format",
    [
        ((99, 99), (9, 9), (11, 11), (0, 0), "RGB", "PNG"),
        ((99, 99), (9, 9), (11, 11), (3, 3), "RGB", "PNG"),
        ((99, 99), (9, 9), (11, 11), (8, 8), "RGB", "PNG"),
        ((99, 99), (9, 9), (33, 33), (3, 3), "RGB", "PNG"),
        ((99, 99), (9, 9), (3, 3), (3, 3), "RGB", "PNG"),
        ((99, 99), (9, 9), (11, 11), (3, 3), "GRAY", "PNG"),
        ((99, 99), (9, 9), (11, 11), (3, 3), "RGB", "JPEG"),
    ],
)
def test_render_pdf_rect(
    source_dimensions, tiles, target_dimensions, tile_pos, colorspace, target_format
):
    colormode = "index" if colorspace == "RGB" else "checkerboard"
    generate_test_pdf(source, source_dimensions, tiles, colormode)
    assert source.exists()
    output_file_name = f"{source.stem}-{colorspace}-tile-{tile_pos[0]}-{tile_pos[1]}.{target_format.lower()}"
    source_rect = (
        (
            tile_pos[0] * source_dimensions[0] / tiles[0],
            tile_pos[1] * source_dimensions[1] / tiles[1],
        ),
        (
            (tile_pos[0] + 1) * source_dimensions[0] / tiles[0],
            (tile_pos[1] + 1) * source_dimensions[1] / tiles[1],
        ),
    )
    render_pdf_rect(
        source,
        0,
        destination_dir,
        output_file_name,
        source_rect,
        target_dimensions,
        colorspace=colorspace,
        target_format=target_format,
    )

    assert destination_dir.exists()
    file_path = destination_dir / output_file_name
    assert file_path.exists()
    with Image.open(file_path) as img:
        assert img.format == target_format.upper()
        assert img.mode == "RGB" if colorspace == "RGB" else "L"

        # Check if the image size matches the target dimensions
        assert img.size == target_dimensions

        # Check if the image color matches the expected color
        tile_index = tile_pos[0] * tiles[1] + tile_pos[1]
        index_bytes = tile_index.to_bytes(3, byteorder="big")
        expected_color = (
            tuple(index_bytes)
            if colormode == "index"
            else (
                ImageColor.getcolor("black", img.mode)
                if (tile_pos[0] + tile_pos[1]) % 2 == 0
                else ImageColor.getcolor("white", img.mode)
            )
        )
        assert is_image_filled_with(img, expected_color)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_dimensions, target_dimensions, tiles, preserve_aspect",
    [
        ((100, 100), (1000, 1000), (10, 10), False),
        ((100, 100), (1000, 100), (10, 10), True),
    ],
)
async def test_convert_output(source_dimensions, target_dimensions, tiles, preserve_aspect):
    generate_test_pdf(source, source_dimensions, tiles)
    await asyncio.wait_for(
        convert(source, 0, destination_dir, target_dimensions, tiles, preserve_aspect=preserve_aspect), timeout=60
    )

    assert destination_dir.exists()
    base_name = source.stem
    actual_width, actual_height = 0, 0

    expected_width = target_dimensions[0]
    expected_height = target_dimensions[1]
    if preserve_aspect:
        expected_height = int(
            expected_width * (source_dimensions[1] / source_dimensions[0])
        )

    expected_tile_width = expected_width / tiles[0]
    expected_tile_height = expected_height / tiles[1]

    files = list(destination_dir.glob("*.png"))
    assert len(files) == tiles[0] * tiles[1]

    pattern = re.compile(rf"{base_name}-tile-(\d+)-(\d+)\.png")
    max_tile_x = max_tile_y = -1
    for file in files:
        match = pattern.fullmatch(file.name)
        assert match is not None
        with Image.open(file) as img:
            assert img.format == "PNG"
            assert img.mode == "RGB"
            assert img.size == (expected_tile_width, expected_tile_height)

            # Check if the image color matches the expected color
            tile_x = int(match.group(1))
            tile_y = int(match.group(2))
            if tile_x > max_tile_x:
                actual_width = actual_width + img.width
                max_tile_x = tile_x
            
            if tile_y > max_tile_y:
                actual_height = actual_height + img.height
                max_tile_y = tile_y

            tile_index = tile_x * tiles[1] + tile_y
            index_bytes = tile_index.to_bytes(3, byteorder="big")
            expected_color = tuple(index_bytes)
            assert is_image_filled_with(img, expected_color)

    assert actual_width == expected_width
    assert actual_height == expected_height
