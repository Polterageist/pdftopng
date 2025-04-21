import typer
from typing_extensions import Annotated
from pathlib import Path
from typing import Optional
import re
import asyncio
from pdftopng.convert import convert


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


def validate_tiles(tiles: str) -> tuple[int, int]:
    # Accepts x (latin), X (latin), х (cyrillic)
    match = re.fullmatch(r"(\d+)[xXх](\d+)", tiles.replace(" ", ""))
    if not match:
        raise typer.BadParameter(
            "Tiles must be in the format NxM, e.g., 4x3. Only digits and 'x' are allowed."
        )
    n, m = int(match.group(1)), int(match.group(2))
    if n <= 0 or m <= 0:
        raise typer.BadParameter("Tiles must be positive integers.")
    return n, m


def main(
    source: Annotated[
        Optional[Path],
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
        Optional[Path],
        typer.Argument(
            help="Destination directory to save the generated png files",
            exists=False,
            file_okay=False,
            dir_okay=True,
            writable=True,
            resolve_path=True,
        ),
    ] = "outptut",
    dimensions: Annotated[
        str, typer.Option(help="Dimensions of the whole image XxY")
    ] = "131072x131072",
    tiles: Annotated[str, typer.Option(help="Num tiles nxm")] = "32x32",
):
    """
    Convert a PDF file to PNG images with specified dimensions and tile size.

    Args:
        source (str): Path to the source PDF file.
        destination_dir (str): Directory where the PNG images will be saved.
        dimensions (str): Dimensions of the whole image in format "widthxheight".
        tiles (str): Number of tiles in format "widthxheight".
    Output:
        The output will be PNG files named as {source_name_without_extension}-tile-x-y.png,
        where x and y are tile indices. The number of PNG files and their resolutions
        will match the requested grid and dimensions.
    """
    width, height = validate_dimensions(dimensions)
    n_tiles, m_tiles = validate_tiles(tiles)
    asyncio.run(convert(source, destination_dir, (width, height), (n_tiles, m_tiles)))


if __name__ == "__main__":
    typer.run(main)
