import typer
from typing_extensions import Annotated
from pathlib import Path
from typing import Optional


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
        )] = "outptut",
    dimensions: Annotated[
        str, typer.Option(help="Dimensions of the whole image XxY")
    ] = "131,072х131,072",
    tiles: Annotated[str, typer.Option(help="Num tiles nxm")] = "32x32",
):
    """
    Convert a PDF file to PNG images with specified dimensions and tile size.

    Args:
        source (str): Path to the source PDF file.
        destination_dir (str): Directory where the PNG images will be saved.
        dimensions (str): Dimensions of the whole image in format "widthxheight".
        tiles (str): Number of tiles in format "widthxheight".
    """
    # @TODO: Implement the PDF to PNG conversion logic here
    pass


if __name__ == "__main__":
    typer.run(main)
