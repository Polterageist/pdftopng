import asyncio
import math
from pathlib import Path
from typing import Tuple
import pymupdf
from rich.console import Console

console = Console()


def render_pdf_rect(
    source: Path,
    page_number: int,
    destination_dir: Path,
    file_name: str,
    source_rect: Tuple[Tuple[float, float], Tuple[float, float]],
    target_dimensions: Tuple[int, int],
    oob_color: Tuple[int, int, int] | Tuple[int] = (255, 255, 255),
    colorspace: str = "RGB",
    target_format: str = "PNG",
):
    """
    Export a tile from a PDF page to an image file.
    Paramters:
        source (Path): Path to the source PDF file. Should exists
        page_number (int): Page number to export the tile from.
        destination_dir (Path): Directory to save the generated image files.
        file_name (str): Bame for the output image file.
        source_rect (Tuple[Tuple[float, float], Tuple[float, float]]): Coordinates of the rectangle to export.
        Should be in the format ((x0, y0), (x1, y1)).
        If out of bounds, extending part of image will be filled with oob_color.
        oob_color (Tuple[int, int, int] | Tuple[int]): Color to fill the out of bounds area.
        Default is (255, 255, 255). Amount of values should be 3 or 1 depending on colorspace.
        target_dimensions (Tuple[int, int]): Dimensions of the output image (width, height).
        colorspace (str): Colorspace for the output image. Default is "RGB". Values can be "RGB" or "GRAY".
        target_format (str): Format for the output image. Default is "PNG".
    """
    if not source.exists():
        raise FileNotFoundError(f"Source file {source} does not exist.")

    if not source.is_file():
        raise ValueError(f"Source {source} is not a file.")

    if not source.suffix.lower() == ".pdf":
        raise ValueError(f"Source {source} is not a PDF file.")

    if not destination_dir.exists():
        destination_dir.mkdir(parents=True, exist_ok=True)

    source_rect = pymupdf.Rect(
        source_rect[0][0], source_rect[0][1], source_rect[1][0], source_rect[1][1]
    )

    mupdfcs = pymupdf.csRGB
    if colorspace == "RGB":
        mupdfcs = pymupdf.csRGB
    elif colorspace == "GRAY":
        mupdfcs = pymupdf.csGRAY
    else:
        raise ValueError(
            f"Invalid colorspace {colorspace}. Supported values are 'RGB', 'GRAY'"
        )

    img = None
    with open(source, "rb") as f:
        doc = pymupdf.open(f)
        if page_number >= len(doc) or page_number < 0:
            raise ValueError(f"Page number {page_number} is out of range.")

        page = doc[page_number]

        if source_rect.x0 < 0 or source_rect.y0 < 0:
            raise ValueError(
                f"Source rectangle {source_rect} has negative coordinates."
            )

        if source_rect.x1 > page.rect.width or source_rect.y1 > page.rect.height:
            raise ValueError(
                f"Source rectangle {source_rect} is out of bounds for page {page_number}."
            )

        matrix = pymupdf.Matrix(
            target_dimensions[0] / (source_rect.x1 - source_rect.x0),
            target_dimensions[1] / (source_rect.y1 - source_rect.y0),
        )
        pix = page.get_pixmap(
            clip=source_rect,
            matrix=matrix,
            colorspace=mupdfcs,
            alpha=False,
        )

        if pix is None:
            raise ValueError(
                f"Failed to render tile from page {page_number} with rectangle {source_rect}."
            )

        img = pix.pil_image()
        if img is None:
            raise ValueError(
                f"Failed to convert tile from page {page_number} with rectangle {source_rect} to PIL image."
            )

        if img.size != target_dimensions:
            # Resize the image to the target dimensions to be sure
            img = img.resize(target_dimensions)

        doc.close()
    img.save(destination_dir / file_name, format=target_format)


async def convert(
    source: Path,
    page_index: int,
    destination_dir: Path,
    tile_size: Tuple[int, int],
    tiles: Tuple[int, int],
    preserve_aspect: bool = True,
    colorspace: str = "RGB",
    target_format: str = "PNG",
    progress_callback: callable = None,
    **kwarg: dict,
) -> None:
    """
    Asynchronously convert a PDF file to PNG tiles.

    Args:
        source (Path): Path to the source PDF file.
        page_index(int): Page number to export the tile from.
        destination_dir (Path): Directory to save the generated PNG files.
        target_dimensions (Tuple[int, int]): Dimensions of the whole image (width, height).
        tiles (Tuple[int, int]): Number of tiles (n, m).
        preserve_aspect (bool): Whether to preserve the aspect ratio of the source image.
        colorspace (str): Colorspace for the output image. Default is "RGB".
            Values can be "RGB" or "GRAY".
        target_format (str): Format for the output image. Default is "PNG".
        progress_callback (callable): Optional callback function to report progress. Should accept
            three arguments: current tile index, total number of tiles, and any additional keyword arguments.
        kwarg (dict): Optional arguments to pass to the progress callback.
    """
    if (not source.exists() or not source.is_file()) or source.suffix.lower() != ".pdf":
        raise ValueError(f"Source {source} is not a valid PDF file.")

    if tiles[0] <= 0 or tiles[1] <= 0:
        raise ValueError(f"Invalid number of tiles {tiles}. Must be positive integers.")

    if tile_size[0] <= 0 or tile_size[1] <= 0:
        raise ValueError(
            f"Invalid target dimensions {tile_size}. Must be positive integers."
        )

    if colorspace not in ["RGB", "GRAY"]:
        raise ValueError(
            f"Invalid colorspace {colorspace}. Supported values are 'RGB', 'GRAY'"
        )

    if target_format not in ["PNG", "JPEG", "BMP", "TIFF"]:
        raise ValueError(
            f"Invalid target format {target_format}. Supported values are 'PNG', 'JPEG', 'BMP', 'TIFF'"
        )

    source_dimensions = None
    with open(source, "rb") as f:
        doc = pymupdf.open(f)
        if page_index >= len(doc) or page_index < 0:
            raise ValueError(f"Page number {page_index} is out of range.")
        page = doc[page_index]
        source_dimensions = (page.rect.width, page.rect.height)
        doc.close()

    if source_dimensions is None:
        raise ValueError(f"Failed to get dimensions of page {page_index} in {source}.")

    tile_w, tile_h = tile_size
    n_tiles, m_tiles = tiles
    total_width, total_height = tile_w * n_tiles, tile_h * m_tiles
    scale_w = total_width / source_dimensions[0]
    scale_h = total_height / source_dimensions[1]

    if not math.isclose(scale_w, scale_h, rel_tol=1e-3) and preserve_aspect:
        if scale_w < scale_h:
            scale_h = scale_w
            total_height = int(source_dimensions[1] * scale_w)
            m_tiles = math.ceil(total_height / tile_h)
        else:
            scale_w = scale_h
            total_width = int(source_dimensions[0] * scale_h)
            n_tiles = math.ceil(total_width / tile_w)

    source_tile_w = source_dimensions[0] / n_tiles
    source_tile_h = source_dimensions[1] / m_tiles

    base_name = source.stem
    total_tiles = n_tiles * m_tiles

    for x in range(n_tiles):
        for y in range(m_tiles):
            x0 = int(x * source_tile_w)
            y0 = int(y * source_tile_h)
            x1 = int((x + 1) * source_tile_w)
            y1 = int((y + 1) * source_tile_h)

            file_name = f"{base_name}-tile-{x}-{y}.{target_format.lower()}"
            tile_index = x * m_tiles + y
            await asyncio.to_thread(
                render_pdf_rect,
                source,
                page_index,
                destination_dir,
                file_name,
                ((x0, y0), (x1, y1)),
                (tile_w, tile_h),
                colorspace=colorspace,
                target_format=target_format,
            )

            if progress_callback:
                progress_callback(tile_index, total_tiles, **kwarg)
