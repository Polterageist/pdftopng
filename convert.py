import asyncio
from pathlib import Path
from typing import Tuple


async def convert(
    source: Path,
    destination_dir: Path,
    dimensions: Tuple[int, int],
    tiles: Tuple[int, int],
) -> None:
    """
    Asynchronously convert a PDF file to PNG tiles.

    Args:
        source (Path): Path to the source PDF file.
        destination_dir (Path): Directory to save the generated PNG files.
        dimensions (Tuple[int, int]): Dimensions of the whole image (width, height).
        tiles (Tuple[int, int]): Number of tiles (n, m).
    """
    # TODO: Implement the conversion logic
    pass
