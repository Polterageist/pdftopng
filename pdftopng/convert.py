import asyncio
import math
from pathlib import Path
from typing import Tuple
import pymupdf
from PIL import Image
from rich.console import Console
import aiofiles
import io

console = Console()


async def convert(
    source: Path,
    destination_dir: Path,
    dimensions: Tuple[int, int],
    tiles: Tuple[int, int]
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
    if width % n_tiles != 0 or height % m_tiles != 0:
        console.print(
            f"Warning: Requested dimensions {width}x{height} are not divisible by the number of tiles "
            "{n_tiles}x{m_tiles}. Rightmost and bottommost tiles will have empty space.",
            style="yellow",
        )

    tile_w = (width + (n_tiles - width % n_tiles)) // n_tiles
    tile_h = (height + (m_tiles - height % m_tiles)) // m_tiles

    doc = pymupdf.open(str(source))
    if len(doc) > 1:
        console.print(
            f"Warning: PDF contains {len(doc)} pages. Only the first page will be processed.",
            style="yellow",
        )
    page = doc[0]
    pdf_width, pdf_height = page.rect.width, page.rect.height
    if (int(pdf_width) != width) or (int(pdf_height) != height):
        console.print(
            f"Warning: PDF page size is {int(pdf_width)}x{int(pdf_height)}, but requested output is {width}x{height}. "
            "Images will be scaled.",
            style="yellow",
        )
    pdf_aspect = pdf_width / pdf_height
    req_aspect = width / height
    if not math.isclose(pdf_aspect, req_aspect, rel_tol=1e-3):
        console.print(
            f"Warning: Aspect ratio mismatch. PDF aspect ratio is {pdf_aspect:.4f}, requested is {req_aspect:.4f}.",
            style="yellow",
        )

    frame_w = (pdf_width + (n_tiles - pdf_width % n_tiles)) / n_tiles
    frame_h = (pdf_height + (m_tiles - pdf_height % m_tiles)) / m_tiles
    scale_w, scale_h = tile_w / frame_w, tile_h / frame_h
    total_tiles = n_tiles * m_tiles

    console.print(
        f"Converting {source} to {n_tiles}x{m_tiles}={total_tiles} PNG tiles "
        "of size {tile_w}x{tile_h} with {n_tiles}x{m_tiles} tiles "
        "with scale {scale_w}x{scale_h}...",
        highlight=False,
        soft_wrap=True,
    )

    processed = 0
    for x in range(n_tiles):
        for y in range(m_tiles):
            tile_str = f"[{processed}/{total_tiles}]: Rendering tile ({x}, {y})..."
            console.print(tile_str, end="", highlight=False, soft_wrap=True)

            # Calculate the PDF coordinates for the tile
            left_corner = x * frame_w
            right_corner = (x + 1) * frame_w if x < n_tiles - 1 else pdf_width
            top_corner = y * frame_h
            bottom_corner = (
                (y + 1) * pdf_height / m_tiles if y < m_tiles - 1 else pdf_height
            )

            clip = pymupdf.Rect(left_corner, top_corner, right_corner, bottom_corner)
            mat = pymupdf.Matrix(scale_w, scale_h)
            pix = await asyncio.to_thread(
                page.get_pixmap,
                matrix=mat,
                clip=clip,
                alpha=False,
                colorspace=pymupdf.csRGB,
            )

            if pix is None:
                console.print(
                    f"Error: Failed to render tile ({x}, {y}). Skipping...",
                    style="red",
                    highlight=False,
                    soft_wrap=True,
                )
                continue

            img = pix.pil_image()
            if img is None:
                console.print(
                    f"Error: Failed to convert tile ({x}, {y}) to PIL image. Skipping...",
                    style="red",
                    highlight=False,
                    soft_wrap=True,
                )
                continue

            # Expand the image to the tile size if necessary
            if img.size != (tile_w, tile_h):
                new_img = Image.new("RGB", (tile_w, tile_h), (255, 255, 255))
                new_img.paste(img, (0, 0))
                img = new_img

            # Save the image to the temp buffer
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            await buf.drain() if hasattr(buf, "drain") else None
            buf.seek(0)
            data = buf.read()
            buf.close()

            # Save the image to the output directory
            out_path = destination_dir / f"{base_name}-tile-{x}-{y}.png"
            async with aiofiles.open(out_path, "wb") as f:
                await f.write(data)

            # Pretty print the progress
            term_width = console.size.width
            done_str = "done"
            pad = max(0, term_width - len(tile_str) - len(done_str))
            console.print(
                f"\r{tile_str}{' ' * pad}{done_str}",
                end="\n",
                highlight=False,
                soft_wrap=True,
            )
            processed += 1

            await asyncio.sleep(0)
    doc.close()
