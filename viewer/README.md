# Tile Viewer

A powerful web-based tile viewer built with Three.js for viewing PDF-to-PNG conversion results and KTX texture files.

## Features

- **Multi-format Support**: PNG, KTX, and KTX2 texture files
- **Interactive Navigation**: Pan, zoom, and rotate functionality
- **2D/3D Viewing Modes**: Switch between map-like 2D view and 3D perspective
- **Directory Selection**: Load entire directories of tile files
- **Progressive Loading**: Tiles load in batches with progress indication
- **Auto-detection**: Automatically detects grid size and file formats
- **Keyboard Shortcuts**: Full keyboard navigation support

## Usage

1. Open `index.html` in a modern web browser
2. Click "Choose Files" and select a directory containing tile files
3. Click "Load Tiles" to begin loading
4. Use mouse and keyboard controls to navigate

## Supported File Formats

### PNG Files
- Standard PNG image files
- Supports any resolution
- Automatically detected by `.png` extension

### KTX Files
- Khronos Texture format files
- Both compressed and uncompressed textures
- Supports `.ktx` and `.ktx2` extensions
- Fallback to placeholder if parsing fails

## File Naming Convention

Tile files should follow this naming pattern:
```
[prefix]-tile-[x]-[y].[extension]
```

Examples:
- `example-tile-0-0.png`
- `map-tile-5-3.ktx2`
- `texture-tile-10-7.ktx`

## Controls

### Mouse Controls
- **Left Click + Drag**: Pan the view
- **Mouse Wheel**: Zoom in/out
- **Right Click + Drag**: Rotate (3D mode only)

### Keyboard Controls
- **R**: Reset view to fit all tiles
- **T**: Toggle between 2D and 3D modes
- **F**: Fit tiles to screen
- **+/-**: Zoom in/out
- **Arrow Keys**: Pan in small increments

### UI Controls
- **File Selector**: Choose directory with tile files
- **Load Button**: Start loading selected tiles
- **Progress Bar**: Shows loading progress
- **Info Panel**: Displays tile count, grid size, format, zoom level, and position

## Technical Details

### Architecture
- Built with Three.js WebGL renderer
- Object-oriented design with TileViewer class
- Modular KTX loader for texture support
- Progressive loading system for large tile sets

### Performance
- Efficient memory management with automatic cleanup
- Batch loading to prevent browser freezing
- Optimized texture handling for large grids
- Responsive design for various screen sizes

### Browser Compatibility
- Modern browsers with WebGL support
- Chrome, Firefox, Safari, Edge (latest versions)
- Requires JavaScript enabled

## Development

To extend or modify the viewer:

1. `index.html` - Main HTML structure and styling
2. `main.js` - Core TileViewer class and functionality
3. `ktx-loader.js` - KTX texture format parser

### Adding New Formats

To add support for additional texture formats:

1. Add file extension to the accept list in HTML
2. Update `detectFormat()` method
3. Implement new loader method following the pattern of `loadPNGTile()`
4. Update the `loadSingleTile()` method to handle the new format

## License

This viewer is part of the pdftopng project. See the main project README for license information.
