import typer
from typing_extensions import Annotated
from pathlib import Path
import re
import asyncio
from pdftopng.convert import convert
from rich.console import Console


def validate_dimensions(dimensions: str) -> tuple[int, int]:
    # Accepts x (latin), X (latin), х (cyrillic)
    match = re.fullmatch(
        r"(\d+)[xXх](\d+)", dimensions.replace(",", "").replace(" ", "")
    )
    if not match:
        raise typer.BadParameter(
            "Dimensions must be in the format WIDTHxHEIGHT, e.g., 1920x1080. Only digits and 'x' are allowed."
        )
    width, height = int(match.group(1)), int(match.group(2))
    if width <= 0 or height <= 0:
        raise typer.BadParameter("Dimensions must be positive integers.")
    return width, height


def main(
    source: Annotated[
        Path,
        typer.Argument(
            ...,
            help="Source pdf to be processed",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    destination_dir: Annotated[
        Path,
        typer.Argument(
            help="Destination directory to save the generated png files",
            exists=False,
            file_okay=False,
            dir_okay=True,
            writable=True,
            resolve_path=True,
        ),
    ],
    tiles: Annotated[str, typer.Argument(help="Num tiles NxM")],
    tile_size: Annotated[str, typer.Argument(help="Dimensions of the one tile XxY.")],
    preserve_aspect: Annotated[
        bool,
        typer.Option(
            help="Whether to preserve the aspect ratio of the source image. Default is True.",
        ),
    ] = True,
    page_index: Annotated[
        int,
        typer.Option(
            help="Page number to export the tile from. Default is 0 (first page).",
        ),
    ] = 0,
    colorspace: Annotated[
        str,
        typer.Option(
            help="Colorspace for the output image. Default is 'RGB'. Values can be 'RGB' or 'GRAY'.",
        ),
    ] = "RGB",
    target_format: Annotated[
        str,
        typer.Option(
            help="Format for the output image. Default is 'PNG'. Values can be 'PNG' or 'JPEG'.",
        ),
    ] = "PNG",
):
    """
    Convert a PDF file to PNG images with specified dimensions and tile size.

    Output:
        The output will be PNG files named as {source_name_without_extension}-tile-x-y.png,
        where x and y are tile indices. The number of PNG files and their resolutions
        will match the requested grid and dimensions.
    """
    tile_width, tile_height = validate_dimensions(tile_size)
    n_tiles, m_tiles = validate_dimensions(tiles)
    console = Console()
    console.print(
        f"Converting {source} to {destination_dir} with dimensions {tile_width}x{tile_height} "
        f"and tiles {n_tiles}x{m_tiles}."
    )
    asyncio.run(
        convert(
            source,
            page_index,
            destination_dir,
            (tile_width, tile_height),
            (n_tiles, m_tiles),
            preserve_aspect,
            colorspace,
            target_format,
            lambda i, tiles: console.print(f"Rendered {i + 1}/{tiles} tiles."),
        )
    )


if __name__ == "__main__":
    typer.run(main)
