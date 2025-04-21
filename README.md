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
python main.py <source> <destination_dir> --dimensions <XxY> --tiles <NxM>
```

- `<source>`: Path to the source PDF file (required).
- `<destination_dir>`: Directory to save the generated PNG files (required).
- `--dimensions <XxY>`: Total resolution of the output image in pixels (default: 131,072x131,072).
- `--tiles <NxM>`: Grid of tiles in NxM format (default: 32x32).

**Example:**
```bash
python main.py Example.pdf output --dimensions 1920x1080 --tiles 4x3
```

This will convert `Example.pdf` into PNG tiles with a total resolution of 1920x1080 pixels, split into a 4x3 grid, and save them in the `output` directory.

## License
This project is proprietary