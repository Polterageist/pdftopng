import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import asyncio
import math
from pathlib import Path
from typing import Tuple
import fitz  # PyMuPDF
from PIL import Image
from rich.console import Console
import aiofiles

console = Console()


async def convert(
    source: Path,
    destination_dir: Path,
    dimensions: Tuple[int, int],
    tiles: Tuple[int, int],
    progress_callback=None,
) -> None:
    """
    Asynchronously convert a PDF file to PNG tiles.

    Args:
        source (Path): Path to the source PDF file.
        destination_dir (Path): Directory to save the generated PNG files.
        dimensions (Tuple[int, int]): Dimensions of the whole image (width, height).
        tiles (Tuple[int, int]): Number of tiles (n, m).
        progress_callback (Callable, optional): Callback to report progress.
    """
    destination_dir.mkdir(parents=True, exist_ok=True)
    base_name = source.stem
    width, height = dimensions
    n_tiles, m_tiles = tiles
    tile_w = width // n_tiles
    tile_h = height // m_tiles

    doc = fitz.open(str(source))
    if len(doc) > 1:
        console.print(
            f"Warning: PDF contains {len(doc)} pages. Only the first page will be processed.",
            style="yellow",
        )
    page = doc[0]
    pdf_width, pdf_height = page.rect.width, page.rect.height
    if (int(pdf_width) != width) or (int(pdf_height) != height):
        console.print(
            f"Warning: PDF page size is {int(pdf_width)}x{int(pdf_height)}, but requested output is {width}x{height}.",
            style="yellow",
        )
    pdf_aspect = pdf_width / pdf_height
    req_aspect = width / height
    if not math.isclose(pdf_aspect, req_aspect, rel_tol=1e-3):
        console.print(
            f"Warning: Aspect ratio mismatch. PDF aspect ratio is {pdf_aspect:.4f}, requested is {req_aspect:.4f}.",
            style="yellow",
        )

    total_tiles = n_tiles * m_tiles
    processed = 0
    for x in range(n_tiles):
        for y in range(m_tiles):
            tile_str = f"Rendering tile ({x}, {y})..."
            console.print(tile_str, end="", highlight=False, soft_wrap=True)
            left_pdf = x * pdf_width / n_tiles
            right_pdf = (x + 1) * pdf_width / n_tiles if x < n_tiles - 1 else pdf_width
            top_pdf = y * pdf_height / m_tiles
            bottom_pdf = (
                (y + 1) * pdf_height / m_tiles if y < m_tiles - 1 else pdf_height
            )
            clip = fitz.Rect(left_pdf, top_pdf, right_pdf, bottom_pdf)
            zoom_x = tile_w / (right_pdf - left_pdf)
            zoom_y = tile_h / (bottom_pdf - top_pdf)
            mat = fitz.Matrix(zoom_x, zoom_y)
            pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
            out_path = destination_dir / f"{base_name}-tile-{x}-{y}.png"
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            import io
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            await buf.drain() if hasattr(buf, 'drain') else None
            buf.seek(0)
            data = buf.read()
            buf.close()
            async with aiofiles.open(out_path, "wb") as f:
                await f.write(data)
            term_width = console.size.width
            done_str = "done"
            pad = max(0, term_width - len(tile_str) - len(done_str))
            console.print(f"\r{tile_str}{' ' * pad}{done_str}", end="\n", highlight=False, soft_wrap=True)
            processed += 1
            if progress_callback:
                await progress_callback(processed, total_tiles)
            await asyncio.sleep(0)
    doc.close()
