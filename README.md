# PDF to PNG Converter

This project is a Command-Line Interface (CLI) tool for converting a PDF file containing a very large image into PNG format. The output PNG is divided into a grid of tiles (NxM) with a specified total resolution (XxY pixels).

## Features
- Converts PDF files with large images into PNG format.
- Allows specifying the total resolution of the output image in pixels (XxY).
- Divides the output PNG into a grid of tiles (NxM).
- Built using Python with the FastCLI framework.

## Technology Stack
- **Python 3.12**: Programming language used for the project.
- **Typer**: Framework for building the CLI tool.
- **Libraries for PDF and PNG processing**: Libraries such as PyMuPDF (for PDF processing) and Pillow (for image manipulation).

## Installation

1. Clone the repository or download the project files.
2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
3. Activate the virtual environment:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## How to Run

To run the script, use the following command:

```bash
python -m pdftopng.main <source> <tiles> <dimensions> <destination_dir> [options]
```

- `<source>`: Path to the source PDF file (required).
- `<tiles>`: Grid of tiles in NxM format (required, e.g., 32x32).
- `<dimensions>`: Total resolution of the output image in pixels (required, e.g., 131072x131072).
- `<destination_dir>`: Directory to save the generated PNG files (required).
- `--page-index`: Page number to export from (default: 0).
- `--preserve-aspect`: Preserve aspect ratio (default: True).
- `--colorspace`: Output colorspace, 'RGB' or 'GRAY' (default: 'RGB').
- `--target-format`: Output format, 'PNG' or 'JPEG' (default: 'PNG').

**Example:**
```bash
python -m pdftopng.main example.pdf 4x3 1920x1080 output
```

This will convert `Example.pdf` into PNG tiles with a total resolution of 1920x1080 pixels, split into a 4x3 grid, and save them in the `output` directory.

## Running Tests

To run the tests, make sure you have the development dependencies installed:

```bash
pip install -r dev-requirements.txt
```

Then run the tests using pytest:

```bash
pytest tests.py
```

## License
This project is proprietary