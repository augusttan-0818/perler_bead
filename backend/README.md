# Perler Bead Pattern Converter - Backend

Convert any image to a Perler bead pattern using the MARD 221 color palette.

## Features

- **Color Quantization**: Maps any color to the nearest MARD 221 bead color
- **Floyd-Steinberg Dithering**: Produces smoother gradients and better detail
- **Pattern Generation**: Creates printable grid with color codes
- **Bead Counting**: Exact count of each color needed

## Quick Start

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run the API server
python app.py
```

Server runs at `http://localhost:5000`

## API Endpoints

### POST /convert

Convert an image to a bead pattern.

**Request (multipart/form-data):**
```
image: <file>
grid_width: 29 (optional)
grid_height: 29 (optional)
use_dithering: true (optional)
```

**Request (JSON with base64):**
```json
{
  "image": "data:image/png;base64,...",
  "grid_width": 29,
  "grid_height": 29,
  "use_dithering": true
}
```

**Response:**
```json
{
  "success": true,
  "preview_image": "data:image/png;base64,...",
  "pattern_image": "data:image/png;base64,...",
  "bead_counts": {"A5": 47, "A6": 82, "H7": 12},
  "total_beads": 841,
  "colors_used": 12,
  "grid_size": "29x29"
}
```

### GET /colors

Get all 221 MARD colors.

### GET /health

Health check.

## CLI Usage

```bash
# Convert an image directly
python converter.py pikachu.png 29 29

# Output:
#   output_preview.png - Scaled up preview
#   output_pattern.png - Printable pattern with labels
```

## Algorithms

### Nearest-Neighbor Color Matching

For each pixel, we find the closest MARD color using Euclidean distance in RGB space:

```
distance = sqrt((r1-r2)² + (g1-g2)² + (b1-b2)²)
```

### Floyd-Steinberg Dithering

Distributes quantization error to neighboring pixels:

```
       X    7/16
 3/16  5/16  1/16
```

This creates smoother gradients by "spreading" colors across neighboring beads.

## Example

Input: 500x500 Pikachu image
Output: 29x29 bead pattern

```
Bead counts:
  A5 (yellow): 412 beads
  A6 (orange): 89 beads
  H7 (black): 45 beads
  F2 (red): 23 beads
  ...

Total: 841 beads
Colors used: 8
```
