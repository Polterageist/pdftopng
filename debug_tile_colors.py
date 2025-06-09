#!/usr/bin/env python3
"""
Debug script to examine tile colors and understand the test failure
"""
import asyncio
from pathlib import Path
from pdftopng.convert import convert
from PIL import Image
import re
import shutil
import pymupdf


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
                
                print(f"PDF Tile ({x},{y}) index={tile_index}: color={color} rect={rect}")

        doc.save(str(output_path), garbage=4, deflate=True, clean=True)


async def debug_main():
    test_dir = Path("./debug_output")
    source = test_dir / "test.pdf"
    destination_dir = test_dir / "output"
    
    # Clean up
    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Test parameters
    source_dimensions = (128, 128)
    tiles = (4, 4)
    tile_size = (32, 32)

    # Generate test PDF
    print("Generating test PDF with colored tiles...")
    generate_test_pdf(source, source_dimensions, tiles, "index")

    # Convert to tiles
    print("\nConverting PDF to tiles...")
    await convert(
        source,
        0,
        destination_dir,
        tile_size,
        tiles,
        preserve_aspect=False,
    )

    # Analyze generated tiles
    print("\nAnalyzing generated tiles...")
    tile_files = list(destination_dir.glob("*.png"))
    pattern = re.compile(r".*-tile-(\d+)-(\d+)\.png")

    for tile_file in sorted(tile_files):
        match = pattern.match(tile_file.name)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            tile_index = x * tiles[1] + y
            expected_color = tuple(tile_index.to_bytes(3, byteorder="big"))
            
            with Image.open(tile_file) as img:
                # Get a sample of pixels to see what color we actually got
                pixels = list(img.getdata())
                unique_colors = list(set(pixels[:100]))  # Sample first 100 pixels
                
                print(f"Tile ({x},{y}) index={tile_index}:")
                print(f"  Expected color: {expected_color}")
                print(f"  Actual unique colors: {unique_colors[:5]}...")  # Show first 5 unique colors
                print(f"  Size: {img.size}")
                print()


if __name__ == "__main__":
    asyncio.run(debug_main())
