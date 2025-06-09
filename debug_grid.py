import asyncio
from pathlib import Path
from pdftopng.convert import convert
from PIL import Image
import numpy as np
import pymupdf
import re


async def debug_grid_pattern():
    """Debug the grid pattern boundary issue"""
    test_dir = Path("d:/Work/Freelance/pdftopng/tests/grid_debug_temp")
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)
    test_dir.mkdir(parents=True, exist_ok=True)
    
    source_dimensions = (200, 200)
    tiles = (4, 4)
    tile_size = (50, 50)
    
    # Generate simple grid PDF
    grid_pdf = test_dir / "grid_test.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=source_dimensions[0], height=source_dimensions[1])
    
    width, height = source_dimensions
    
    # Draw a simple grid with lines every 50 pixels (exactly at tile boundaries)
    line_color = [1, 0, 0]  # Red lines in PyMuPDF format (0-1 range)
    line_width = 2
    
    # Vertical lines at x = 50, 100, 150
    for x in [50, 100, 150]:
        page.draw_line(
            pymupdf.Point(x, 0), 
            pymupdf.Point(x, height),
            color=line_color, 
            width=line_width
        )
    
    # Horizontal lines at y = 50, 100, 150
    for y in [50, 100, 150]:
        page.draw_line(
            pymupdf.Point(0, y), 
            pymupdf.Point(width, y),
            color=line_color, 
            width=line_width
        )
    
    doc.save(str(grid_pdf), garbage=4, deflate=True, clean=True)
    doc.close()
    
    # Convert to tiles
    destination_dir = test_dir / "output"
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
    
    # Load tiles and save debug images
    tiles_dict = {}
    pattern = re.compile(r".*-tile-(\d+)-(\d+)\.png")
    
    for tile_file in destination_dir.glob("*.png"):
        match = pattern.match(tile_file.name)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            with Image.open(tile_file) as img:
                tiles_dict[(x, y)] = img.copy()
                # Save each tile
                img.save(test_dir / f"tile_{x}_{y}.png")
    
    print(f"Generated {len(tiles_dict)} tiles")
    
    # Check one specific boundary: between tile (0,0) and (1,0)
    if (0, 0) in tiles_dict and (1, 0) in tiles_dict:
        left_tile = tiles_dict[(0, 0)]
        right_tile = tiles_dict[(1, 0)]
        
        # Extract edges (1 pixel wide for precision)
        left_edge = left_tile.crop((left_tile.width - 1, 0, left_tile.width, left_tile.height))
        right_edge = right_tile.crop((0, 0, 1, right_tile.height))
        
        # Save edges
        left_edge.save(test_dir / "left_edge.png")
        right_edge.save(test_dir / "right_edge.png")
        
        # Analyze pixel by pixel
        left_pixels = list(left_edge.getdata())
        right_pixels = list(right_edge.getdata())
        
        print(f"Left edge pixels (last column of tile 0,0): {left_pixels}")
        print(f"Right edge pixels (first column of tile 1,0): {right_pixels}")
        
        # Count matches
        exact_matches = sum(1 for p1, p2 in zip(left_pixels, right_pixels) if p1 == p2)
        print(f"Exact matches: {exact_matches}/{len(left_pixels)} ({exact_matches/len(left_pixels)*100:.1f}%)")
        
        # Check for red pixels (should be present if grid line crosses boundary)
        red_in_left = sum(1 for p in left_pixels if p[0] > 100 and p[1] < 50 and p[2] < 50)
        red_in_right = sum(1 for p in right_pixels if p[0] > 100 and p[1] < 50 and p[2] < 50)
        
        print(f"Red pixels in left edge: {red_in_left}")
        print(f"Red pixels in right edge: {red_in_right}")

    print(f"Debug files saved to: {test_dir}")


if __name__ == "__main__":
    asyncio.run(debug_grid_pattern())
