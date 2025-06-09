import pytest
import asyncio
from pathlib import Path
from pdftopng.convert import convert
from PIL import Image
import numpy as np
import pymupdf
import shutil


test_dir = Path(__file__).parent / "boundary_diagnostic_temp"
source = test_dir / "diagnostic.pdf"
destination_dir = test_dir / "output"


@pytest.fixture(autouse=True)
def cleanup_output_dirs():
    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)
    test_dir.mkdir(parents=True, exist_ok=True)
    yield


def create_simple_line_pdf(output_path, dimensions):
    """Create a PDF with simple horizontal and vertical lines"""
    doc = pymupdf.open()
    page = doc.new_page(width=dimensions[0], height=dimensions[1])
    
    width, height = dimensions
    
    # Draw one horizontal line across the middle
    y_middle = height / 2
    page.draw_line(
        pymupdf.Point(0, y_middle), 
        pymupdf.Point(width, y_middle),
        color=[0, 0, 0],  # Black
        width=2
    )
    
    # Draw one vertical line across the middle  
    x_middle = width / 2
    page.draw_line(
        pymupdf.Point(x_middle, 0), 
        pymupdf.Point(x_middle, height),
        color=[0, 0, 0],  # Black
        width=2
    )
    
    doc.save(str(output_path), garbage=4, deflate=True, clean=True)
    doc.close()


def save_boundary_debug_image(img1, img2, boundary_type, output_path):
    """Save a debug image showing the boundary comparison"""
    if boundary_type == "right":
        # Get the right edge of img1 and left edge of img2
        edge1 = img1.crop((img1.width - 5, 0, img1.width, img1.height))
        edge2 = img2.crop((0, 0, 5, img2.height))
        
        # Create side-by-side comparison
        combined_width = edge1.width + edge2.width + 10  # 10px gap
        combined_height = max(edge1.height, edge2.height)
        combined = Image.new('RGB', (combined_width, combined_height), (128, 128, 128))
        
        combined.paste(edge1, (0, 0))
        combined.paste(edge2, (edge1.width + 10, 0))
        
    elif boundary_type == "bottom":
        # Get the bottom edge of img1 and top edge of img2
        edge1 = img1.crop((0, img1.height - 5, img1.width, img1.height))
        edge2 = img2.crop((0, 0, img2.width, 5))
        
        # Create top-bottom comparison
        combined_width = max(edge1.width, edge2.width)
        combined_height = edge1.height + edge2.height + 10  # 10px gap
        combined = Image.new('RGB', (combined_width, combined_height), (128, 128, 128))
        
        combined.paste(edge1, (0, 0))
        combined.paste(edge2, (0, edge1.height + 10))
    
    combined.save(output_path)


@pytest.mark.asyncio
async def test_simple_boundary_diagnostic():
    """Diagnostic test to understand boundary alignment issues"""
    # Use simple dimensions that divide evenly
    source_dimensions = (100, 100)
    tiles = (2, 2)
    tile_size = (50, 50)

    # Create PDF with simple lines
    create_simple_line_pdf(source, source_dimensions)

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
    )    # Load tiles
    tiles_dict = {}
    import re
    pattern = re.compile(r".*-tile-(\d+)-(\d+)\.png")
    
    for tile_file in destination_dir.glob("*.png"):
        match = pattern.match(tile_file.name)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            with Image.open(tile_file) as img:
                tiles_dict[(x, y)] = img.copy()
                print(f"Loaded tile ({x},{y}): {img.size}")

    # Save individual tiles for inspection
    debug_dir = test_dir / "debug"
    debug_dir.mkdir(exist_ok=True)
    
    for (x, y), img in tiles_dict.items():
        img.save(debug_dir / f"tile_{x}_{y}.png")

    # Check horizontal boundary between (0,0) and (1,0)
    if (0, 0) in tiles_dict and (1, 0) in tiles_dict:
        tile1 = tiles_dict[(0, 0)]
        tile2 = tiles_dict[(1, 0)]
        
        # Save boundary debug image
        save_boundary_debug_image(tile1, tile2, "right", debug_dir / "boundary_horizontal_0_0_to_1_0.png")
        
        # Analyze the right edge of tile1 and left edge of tile2
        edge1 = tile1.crop((tile1.width - 1, 0, tile1.width, tile1.height))
        edge2 = tile2.crop((0, 0, 1, tile2.height))
        
        edge1.save(debug_dir / "edge1_right.png")
        edge2.save(debug_dir / "edge2_left.png")
        
        # Print pixel values for debugging
        pixels1 = list(edge1.getdata())
        pixels2 = list(edge2.getdata())
        
        print(f"Edge 1 (right of tile 0,0) pixels: {pixels1[:10]}...")
        print(f"Edge 2 (left of tile 1,0) pixels: {pixels2[:10]}...")
        
        # Count exact matches
        exact_matches = sum(1 for p1, p2 in zip(pixels1, pixels2) if p1 == p2)
        print(f"Exact matches: {exact_matches}/{len(pixels1)} ({exact_matches/len(pixels1)*100:.1f}%)")

    # Check vertical boundary between (0,0) and (0,1) 
    if (0, 0) in tiles_dict and (0, 1) in tiles_dict:
        tile1 = tiles_dict[(0, 0)]
        tile2 = tiles_dict[(0, 1)]
        
        # Save boundary debug image
        save_boundary_debug_image(tile1, tile2, "bottom", debug_dir / "boundary_vertical_0_0_to_0_1.png")
        
        # Analyze the bottom edge of tile1 and top edge of tile2
        edge1 = tile1.crop((0, tile1.height - 1, tile1.width, tile1.height))
        edge2 = tile2.crop((0, 0, tile2.width, 1))
        
        edge1.save(debug_dir / "edge1_bottom.png")
        edge2.save(debug_dir / "edge2_top.png")
        
        # Print pixel values for debugging
        pixels1 = list(edge1.getdata())
        pixels2 = list(edge2.getdata())
        
        print(f"Edge 1 (bottom of tile 0,0) pixels: {pixels1[:10]}...")
        print(f"Edge 2 (top of tile 0,1) pixels: {pixels2[:10]}...")
        
        # Count exact matches
        exact_matches = sum(1 for p1, p2 in zip(pixels1, pixels2) if p1 == p2)
        print(f"Exact matches: {exact_matches}/{len(pixels1)} ({exact_matches/len(pixels1)*100:.1f}%)")

    print(f"Debug images saved to: {debug_dir}")


if __name__ == "__main__":
    asyncio.run(test_simple_boundary_diagnostic())
