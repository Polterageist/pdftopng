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

## Usage

Run the CLI tool with the following command:
```bash
python cli_tool.py --input Example.pdf --output output_folder --resolution 1920x1080 --tiles 4x3
```

- `--input`: Path to the input PDF file.
- `--output`: Path to the output folder for PNG tiles.
- `--resolution`: Total resolution of the output image in pixels (e.g., 1920x1080).
- `--tiles`: Grid of tiles in NxM format (e.g., 4x3).

## License
This project is proprietary