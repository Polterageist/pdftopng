import pytest
import asyncio
from pathlib import Path
from pdftopng.convert import convert
from PIL import Image
import numpy as np
import pymupdf
import shutil
import re


test_dir = Path(__file__).parent / "boundary_tests_temp"
source = test_dir / "boundary_test.pdf"
destination_dir = test_dir / "output"


@pytest.fixture(autouse=True)
def cleanup_output_dirs():
    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)
    test_dir.mkdir(parents=True, exist_ok=True)
    yield


def generate_test_pdf(output_path, dimensions, tiles, codingmode="index"):
    """Generate a simple PDF file with a single page of specified dimensions and color-coded grid of tiles"""
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
                tr = (
                    (x + 1) * tile_width,
                    (y + 1) * tile_height,
                )
                rect = pymupdf.Rect(tl[0], tl[1], tr[0], tr[1])

                if codingmode == "index":
                    # Use tile index as color
                    index_bytes = tile_index.to_bytes(3, byteorder="big")
                    color = index_bytes
                else:
                    # Default to white
                    color = (255, 255, 255)

                # Convert color to pymupdf format
                pymupdf_color = [c / 255.0 for c in color]
                page.draw_rect(rect, color=pymupdf_color, fill=pymupdf_color)

        doc.save(str(output_path), garbage=4, deflate=True, clean=True)


def generate_line_pattern_pdf(output_path, dimensions, pattern="grid"):
    """Generate a PDF with line patterns to test boundary stitching"""
    doc = pymupdf.open()
    page = doc.new_page(width=dimensions[0], height=dimensions[1])

    width, height = dimensions

    if pattern == "grid":
        # Draw a grid pattern with lines every 10 units
        line_spacing = 10
        line_color = (0, 0, 0)  # Black lines
        line_width = 1
        
        # Vertical lines
        for x in range(0, int(width), line_spacing):
            start_point = pymupdf.Point(x, 0)
            end_point = pymupdf.Point(x, height)
            page.draw_line(
                start_point, end_point, 
                color=[c/255.0 for c in line_color], 
                width=line_width
            )
        
        # Horizontal lines
        for y in range(0, int(height), line_spacing):
            start_point = pymupdf.Point(0, y)
            end_point = pymupdf.Point(width, y)
            page.draw_line(
                start_point, end_point, 
                color=[c/255.0 for c in line_color], 
                width=line_width
            )    
    elif pattern == "diagonal":
        # Draw diagonal lines across the entire PDF
        line_color = (255, 0, 0)  # Red lines
        line_width = 2
        
        # Main diagonals
        page.draw_line(
            pymupdf.Point(0, 0),
            pymupdf.Point(width, height),
            color=[c/255.0 for c in line_color],
            width=line_width,
        )
        page.draw_line(
            pymupdf.Point(0, height),
            pymupdf.Point(width, 0),
            color=[c/255.0 for c in line_color],
            width=line_width,
        )

        # Additional diagonal lines
        for i in range(1, 5):
            offset = width * 0.2 * i
            if offset < width:
                page.draw_line(
                    pymupdf.Point(offset, 0),
                    pymupdf.Point(width, height - offset),
                    color=[c/255.0 for c in line_color],
                    width=line_width,
                )
                page.draw_line(
                    pymupdf.Point(0, offset),
                    pymupdf.Point(width - offset, height),
                    color=[c/255.0 for c in line_color],
                    width=line_width,
                )

    doc.save(str(output_path), garbage=4, deflate=True, clean=True)
    doc.close()


def is_image_filled_with(image, color, rect=None, tolerance=0.9):
    """Check if the image is filled with a specific color with tolerance for anti-aliasing"""
    start_x, start_y = 0, 0
    end_x, end_y = image.size
    if rect:
        start_x, start_y = rect[0]
        end_x, end_y = rect[1]

    total_pixels = 0
    matching_pixels = 0

    for x in range(start_x, end_x):
        for y in range(start_y, end_y):
            total_pixels += 1
            pixel_color = image.getpixel((x, y))
            if isinstance(pixel_color, int):  # Grayscale
                pixel_color = (pixel_color,)
            elif len(pixel_color) == 4:  # RGBA
                pixel_color = pixel_color[:3]  # Remove alpha

            expected_color = color
            if isinstance(expected_color, int):  # Grayscale
                expected_color = (expected_color,)
            elif len(expected_color) == 4:  # RGBA
                expected_color = expected_color[:3]  # Remove alpha

            if pixel_color == expected_color:
                matching_pixels += 1

    # Allow some tolerance for anti-aliasing effects
    match_ratio = matching_pixels / total_pixels if total_pixels > 0 else 0
    return match_ratio >= tolerance


def check_boundary_continuity(img1, img2, boundary_type="right", edge_width=3):
    """
    Check if two adjacent tiles have continuous boundaries

    Args:
        img1: First image (PIL Image)
        img2: Second image (PIL Image)
        boundary_type: "right" (img1 right edge vs img2 left edge) or "bottom"
        edge_width: Number of pixels to compare along the edge (default 3)

    Returns:
        dict with continuity analysis results
    """
    if boundary_type == "right":
        # Extract right edge of img1 and left edge of img2 (multiple pixels wide)
        edge1 = img1.crop((img1.width - edge_width, 0, img1.width, img1.height))
        edge2 = img2.crop((0, 0, edge_width, img2.height))
    elif boundary_type == "bottom":
        # Extract bottom edge of img1 and top edge of img2 (multiple pixels tall)
        edge1 = img1.crop((0, img1.height - edge_width, img1.width, img1.height))
        edge2 = img2.crop((0, 0, img2.width, edge_width))
    else:
        raise ValueError("boundary_type must be 'right' or 'bottom'")

    # Convert to numpy arrays for easier processing
    arr1 = np.array(edge1)
    arr2 = np.array(edge2)

    if arr1.shape != arr2.shape:
        return {"continuous": False, "reason": "Different edge shapes"}

    # Calculate pixel-wise differences
    if len(arr1.shape) == 3:  # Color images
        # Calculate mean difference across color channels
        diff = np.mean(np.abs(arr1.astype(float) - arr2.astype(float)), axis=2)
    else:  # Grayscale
        diff = np.abs(arr1.astype(float) - arr2.astype(float))    # Count matches with tolerance for anti-aliasing
    tolerance_threshold = 15  # Allow up to 15 units difference per channel
    exact_matches = np.sum(diff == 0)
    near_matches = np.sum(diff <= tolerance_threshold)
    total_pixels = diff.size

    exact_ratio = exact_matches / total_pixels if total_pixels > 0 else 0
    near_ratio = near_matches / total_pixels if total_pixels > 0 else 0

    return {
        "continuous": near_ratio >= 0.3,  # 30% of pixels should match closely (adjusted for fine grid patterns)
        "exact_match_ratio": exact_ratio,
        "near_match_ratio": near_ratio,
        "total_pixels": total_pixels,
        "exact_matches": exact_matches,
        "near_matches": near_matches,
        "mean_difference": np.mean(diff),
        "max_difference": np.max(diff)
    }


@pytest.mark.asyncio
async def test_convert_basic():
    """Basic test for convert function"""
    source_dimensions = (100, 100)
    tiles = (2, 2)
    tile_size = (50, 50)

    generate_test_pdf(source, source_dimensions, tiles)

    await asyncio.wait_for(
        convert(
            source,
            0,
            destination_dir,
            tile_size,
            tiles,
            preserve_aspect=False,
        ),
        timeout=60,
    )

    tile_files = list(destination_dir.glob("*.png"))
    assert len(tile_files) == 4

    for tile_file in tile_files:
        with Image.open(tile_file) as img:
            assert img.size == tile_size
            assert img.mode == "RGB"


@pytest.mark.asyncio
async def test_chunk_stitching_accuracy():
    """Test that tiles can be stitched back together accurately"""
    source_dimensions = (128, 128)
    tiles = (4, 4)
    tile_size = (32, 32)

    generate_test_pdf(source, source_dimensions, tiles, "index")

    await asyncio.wait_for(
        convert(
            source,
            0,
            destination_dir,
            tile_size,
            tiles,
            preserve_aspect=False,
        ),
        timeout=60,
    )

    # Verify all expected tiles exist
    tile_files = list(destination_dir.glob("*.png"))
    assert len(tile_files) == 16  # 4x4

    # Verify tile naming follows expected pattern
    pattern = re.compile(r".*-tile-(\d+)-(\d+)\.png")
    found_coordinates = set()

    for tile_file in tile_files:
        match = pattern.match(tile_file.name)
        assert match is not None

        x, y = int(match.group(1)), int(match.group(2))
        assert 0 <= x < 4
        assert 0 <= y < 4
        found_coordinates.add((x, y))

        # Verify tile content
        with Image.open(tile_file) as img:
            assert img.size == tile_size
            tile_index = x * tiles[1] + y
            index_bytes = tile_index.to_bytes(3, byteorder="big")
            expected_color = tuple(index_bytes)
            assert is_image_filled_with(img, expected_color)

    # Ensure all expected coordinates were found
    expected_coordinates = {(x, y) for x in range(4) for y in range(4)}
    assert found_coordinates == expected_coordinates


@pytest.mark.asyncio
async def test_boundary_stitching_grid_pattern():
    """Test that tiles with grid pattern stitch together correctly at boundaries"""
    source_dimensions = (200, 200)
    tiles = (4, 4)
    tile_size = (50, 50)

    # Generate PDF with grid pattern
    grid_pdf = test_dir / "grid_test.pdf"
    generate_line_pattern_pdf(grid_pdf, source_dimensions, "grid")

    await asyncio.wait_for(
        convert(
            grid_pdf,
            0,
            destination_dir,
            tile_size,
            tiles,
            preserve_aspect=False,
        ),
        timeout=60,
    )

    # Load all tiles
    tile_files = list(destination_dir.glob("*.png"))
    assert len(tile_files) == 16  # 4x4

    tiles_dict = {}
    pattern = re.compile(r".*-tile-(\d+)-(\d+)\.png")

    for tile_file in tile_files:
        match = pattern.match(tile_file.name)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            with Image.open(tile_file) as img:
                tiles_dict[(x, y)] = img.copy()

    # Test horizontal boundaries (right edge of tile vs left edge of adjacent tile)
    boundary_failures = []

    for x in range(3):  # 0, 1, 2 (testing with tiles 1, 2, 3)
        for y in range(4):  # 0, 1, 2, 3
            left_tile = tiles_dict[(x, y)]
            right_tile = tiles_dict[(x + 1, y)]

            continuity = check_boundary_continuity(left_tile, right_tile, "right")

            if not continuity["continuous"]:
                boundary_failures.append(
                    {
                        "boundary": f"({x},{y})-({x+1},{y}) horizontal",
                        "details": continuity,
                    }
                )

    # Test vertical boundaries (bottom edge of tile vs top edge of adjacent tile)
    for x in range(4):  # 0, 1, 2, 3
        for y in range(3):  # 0, 1, 2 (testing with tiles 1, 2, 3)
            top_tile = tiles_dict[(x, y)]
            bottom_tile = tiles_dict[(x, y + 1)]

            continuity = check_boundary_continuity(top_tile, bottom_tile, "bottom")

            if not continuity["continuous"]:
                boundary_failures.append(
                    {
                        "boundary": f"({x},{y})-({x},{y+1}) vertical",
                        "details": continuity,
                    }
                )

    # Report any failures
    if boundary_failures:
        failure_report = "\n".join(
            [
                f"Boundary {f['boundary']}: {f['details']['near_match_ratio']:.1%} continuity"
                for f in boundary_failures
            ]
        )
        pytest.fail(f"Boundary discontinuities found:\n{failure_report}")


@pytest.mark.asyncio
async def test_boundary_stitching_diagonal_pattern():
    """Test that tiles with diagonal lines stitch together correctly"""
    source_dimensions = (160, 160)
    tiles = (4, 4)
    tile_size = (40, 40)

    # Generate PDF with diagonal pattern
    diagonal_pdf = test_dir / "diagonal_test.pdf"
    generate_line_pattern_pdf(diagonal_pdf, source_dimensions, "diagonal")

    await asyncio.wait_for(
        convert(
            diagonal_pdf,
            0,
            destination_dir,
            tile_size,
            tiles,
            preserve_aspect=False,
        ),
        timeout=60,
    )

    # Load all tiles
    tile_files = list(destination_dir.glob("*.png"))
    assert len(tile_files) == 16  # 4x4

    tiles_dict = {}
    pattern = re.compile(r".*-tile-(\d+)-(\d+)\.png")

    for tile_file in tile_files:
        match = pattern.match(tile_file.name)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            with Image.open(tile_file) as img:
                tiles_dict[(x, y)] = img.copy()

    # Test some critical boundaries where diagonal lines should be continuous
    critical_boundaries = [
        ((0, 0), (1, 0), "right"),  # Top row
        ((1, 1), (2, 1), "right"),  # Middle row
        ((1, 0), (1, 1), "bottom"),  # Left column
        ((2, 1), (2, 2), "bottom"),  # Middle column
    ]

    boundary_failures = []

    for tile1_coord, tile2_coord, boundary_type in critical_boundaries:
        tile1 = tiles_dict[tile1_coord]
        tile2 = tiles_dict[tile2_coord]

        continuity = check_boundary_continuity(tile1, tile2, boundary_type)

        if not continuity["continuous"]:
            boundary_failures.append(
                {
                    "boundary": f"{tile1_coord}-{tile2_coord} {boundary_type}",
                    "details": continuity,
                }
            )

    # Report any failures
    if boundary_failures:
        failure_report = "\n".join(
            [
                f"Boundary {f['boundary']}: {f['details']['near_match_ratio']:.1%} continuity"
                for f in boundary_failures
            ]
        )
        pytest.fail(f"Diagonal line discontinuities found:\n{failure_report}")
