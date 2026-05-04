"""
Perler Bead Pattern Converter

Converts any image to a Perler bead pattern using the MARD 221 color palette.

Key algorithms:
1. Image resizing to grid dimensions
2. Nearest-neighbor color matching (Euclidean distance in RGB space)
3. Floyd-Steinberg dithering for smoother color transitions
"""

import numpy as np
from PIL import Image
from typing import Dict, Tuple, List, Optional
from mard_colors import MARD_221_RGB, MARD_221_COLORS

# Pre-compute color arrays for vectorized operations
COLOR_NAMES = list(MARD_221_RGB.keys())
COLOR_RGB_ARRAY = np.array([MARD_221_RGB[name] for name in COLOR_NAMES], dtype=np.float32)


def find_nearest_color(pixel_rgb: np.ndarray) -> Tuple[str, Tuple[int, int, int]]:
    """
    Find the nearest MARD color to a given RGB pixel.

    Uses Euclidean distance in RGB space.
    For better perceptual matching, could use LAB color space.

    Args:
        pixel_rgb: numpy array of [R, G, B] values (0-255)

    Returns:
        Tuple of (color_name, rgb_tuple)
    """
    # Calculate Euclidean distance to all colors
    distances = np.sqrt(np.sum((COLOR_RGB_ARRAY - pixel_rgb) ** 2, axis=1))

    # Find index of minimum distance
    nearest_idx = np.argmin(distances)

    color_name = COLOR_NAMES[nearest_idx]
    color_rgb = tuple(int(c) for c in COLOR_RGB_ARRAY[nearest_idx])

    return color_name, color_rgb


def find_nearest_color_lab(pixel_rgb: np.ndarray) -> Tuple[str, Tuple[int, int, int]]:
    """
    Find nearest color using LAB color space for better perceptual matching.

    LAB is designed to be perceptually uniform - equal distances in LAB
    correspond to equal perceived color differences.
    """
    from skimage import color as skcolor

    # Convert pixel to LAB
    pixel_lab = skcolor.rgb2lab(pixel_rgb.reshape(1, 1, 3) / 255.0).flatten()

    # Convert palette to LAB (could be pre-computed for speed)
    palette_lab = skcolor.rgb2lab(COLOR_RGB_ARRAY.reshape(1, -1, 3) / 255.0).reshape(-1, 3)

    # Calculate distances in LAB space
    distances = np.sqrt(np.sum((palette_lab - pixel_lab) ** 2, axis=1))

    nearest_idx = np.argmin(distances)
    color_name = COLOR_NAMES[nearest_idx]
    color_rgb = tuple(int(c) for c in COLOR_RGB_ARRAY[nearest_idx])

    return color_name, color_rgb


def convert_image_simple(
    image: Image.Image,
    grid_width: int = 29,
    grid_height: int = 29,
    use_lab: bool = False
) -> Tuple[Image.Image, Dict[str, int], np.ndarray]:
    """
    Convert image to bead pattern using simple nearest-neighbor matching.

    Args:
        image: PIL Image to convert
        grid_width: Number of beads horizontally
        grid_height: Number of beads vertically
        use_lab: Use LAB color space for better perceptual matching

    Returns:
        Tuple of:
        - output_image: PIL Image of the bead pattern
        - bead_counts: Dict mapping color names to counts
        - color_grid: 2D numpy array of color names
    """
    # Resize image to grid size
    image = image.convert('RGB')
    image = image.resize((grid_width, grid_height), Image.Resampling.LANCZOS)

    # Convert to numpy array
    pixels = np.array(image, dtype=np.float32)

    # Output arrays
    output_pixels = np.zeros_like(pixels, dtype=np.uint8)
    color_grid = np.empty((grid_height, grid_width), dtype=object)
    bead_counts: Dict[str, int] = {}

    # Find function to use
    find_fn = find_nearest_color_lab if use_lab else find_nearest_color

    # Process each pixel
    for y in range(grid_height):
        for x in range(grid_width):
            pixel = pixels[y, x]
            color_name, color_rgb = find_fn(pixel)

            output_pixels[y, x] = color_rgb
            color_grid[y, x] = color_name
            bead_counts[color_name] = bead_counts.get(color_name, 0) + 1

    output_image = Image.fromarray(output_pixels, mode='RGB')

    return output_image, bead_counts, color_grid


def convert_image_dithered(
    image: Image.Image,
    grid_width: int = 29,
    grid_height: int = 29
) -> Tuple[Image.Image, Dict[str, int], np.ndarray]:
    """
    Convert image using Floyd-Steinberg dithering.

    Dithering distributes quantization error to neighboring pixels,
    creating smoother gradients and better detail preservation.

    Floyd-Steinberg error distribution:
         X   7/16
    3/16 5/16 1/16

    Where X is the current pixel.
    """
    # Resize image to grid size
    image = image.convert('RGB')
    image = image.resize((grid_width, grid_height), Image.Resampling.LANCZOS)

    # Convert to numpy array (use float for error diffusion)
    pixels = np.array(image, dtype=np.float32)

    # Output arrays
    output_pixels = np.zeros_like(pixels, dtype=np.uint8)
    color_grid = np.empty((grid_height, grid_width), dtype=object)
    bead_counts: Dict[str, int] = {}

    # Floyd-Steinberg dithering
    for y in range(grid_height):
        for x in range(grid_width):
            # Get current pixel (may have accumulated error)
            old_pixel = pixels[y, x].copy()

            # Clamp to valid range
            old_pixel = np.clip(old_pixel, 0, 255)

            # Find nearest color
            color_name, color_rgb = find_nearest_color(old_pixel)
            new_pixel = np.array(color_rgb, dtype=np.float32)

            # Store result
            output_pixels[y, x] = color_rgb
            color_grid[y, x] = color_name
            bead_counts[color_name] = bead_counts.get(color_name, 0) + 1

            # Calculate quantization error
            error = old_pixel - new_pixel

            # Distribute error to neighboring pixels (Floyd-Steinberg)
            if x + 1 < grid_width:
                pixels[y, x + 1] += error * 7 / 16
            if y + 1 < grid_height:
                if x > 0:
                    pixels[y + 1, x - 1] += error * 3 / 16
                pixels[y + 1, x] += error * 5 / 16
                if x + 1 < grid_width:
                    pixels[y + 1, x + 1] += error * 1 / 16

    output_image = Image.fromarray(output_pixels, mode='RGB')

    return output_image, bead_counts, color_grid


def generate_pattern_grid(
    color_grid: np.ndarray,
    cell_size: int = 30
) -> Image.Image:
    """
    Generate a printable pattern grid with color codes in each cell.

    Args:
        color_grid: 2D array of color names
        cell_size: Size of each cell in pixels

    Returns:
        PIL Image of the printable pattern
    """
    from PIL import ImageDraw, ImageFont

    height, width = color_grid.shape
    img_width = width * cell_size
    img_height = height * cell_size

    # Create image with white background
    image = Image.new('RGB', (img_width, img_height), 'white')
    draw = ImageDraw.Draw(image)

    # Try to load a font, fall back to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", cell_size // 3)
    except:
        font = ImageFont.load_default()

    for y in range(height):
        for x in range(width):
            color_name = color_grid[y, x]
            color_rgb = MARD_221_RGB[color_name]

            # Cell coordinates
            x0 = x * cell_size
            y0 = y * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size

            # Fill cell with color
            draw.rectangle([x0, y0, x1, y1], fill=color_rgb, outline='gray')

            # Add text label (use contrasting color)
            brightness = sum(color_rgb) / 3
            text_color = 'black' if brightness > 128 else 'white'

            # Center text in cell
            bbox = draw.textbbox((0, 0), color_name, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = x0 + (cell_size - text_width) // 2
            text_y = y0 + (cell_size - text_height) // 2

            draw.text((text_x, text_y), color_name, fill=text_color, font=font)

    return image


def convert_image(
    image_path: str,
    grid_width: int = 29,
    grid_height: int = 29,
    use_dithering: bool = True,
    output_prefix: str = "output"
) -> Dict:
    """
    Main conversion function - converts image and saves outputs.

    Args:
        image_path: Path to input image
        grid_width: Number of beads horizontally
        grid_height: Number of beads vertically
        use_dithering: Whether to use Floyd-Steinberg dithering
        output_prefix: Prefix for output files

    Returns:
        Dict with conversion results
    """
    # Load image
    image = Image.open(image_path)

    # Convert
    if use_dithering:
        output_image, bead_counts, color_grid = convert_image_dithered(
            image, grid_width, grid_height
        )
    else:
        output_image, bead_counts, color_grid = convert_image_simple(
            image, grid_width, grid_height
        )

    # Generate pattern grid
    pattern_grid = generate_pattern_grid(color_grid)

    # Scale up output image for visibility
    scale = 20
    output_scaled = output_image.resize(
        (grid_width * scale, grid_height * scale),
        Image.Resampling.NEAREST
    )

    # Save outputs
    output_scaled.save(f"{output_prefix}_preview.png")
    pattern_grid.save(f"{output_prefix}_pattern.png")

    # Sort bead counts by quantity
    sorted_counts = dict(sorted(bead_counts.items(), key=lambda x: -x[1]))

    return {
        "preview_image": output_scaled,
        "pattern_image": pattern_grid,
        "bead_counts": sorted_counts,
        "total_beads": sum(bead_counts.values()),
        "colors_used": len(bead_counts),
        "grid_size": f"{grid_width}x{grid_height}"
    }


# CLI usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python converter.py <image_path> [grid_width] [grid_height]")
        print("Example: python converter.py pikachu.png 29 29")
        sys.exit(1)

    image_path = sys.argv[1]
    grid_width = int(sys.argv[2]) if len(sys.argv) > 2 else 29
    grid_height = int(sys.argv[3]) if len(sys.argv) > 3 else 29

    print(f"Converting {image_path} to {grid_width}x{grid_height} bead pattern...")

    result = convert_image(image_path, grid_width, grid_height)

    print(f"\nResults:")
    print(f"  Grid size: {result['grid_size']}")
    print(f"  Total beads: {result['total_beads']}")
    print(f"  Colors used: {result['colors_used']}")
    print(f"\nBead counts:")
    for color, count in list(result['bead_counts'].items())[:10]:
        print(f"  {color}: {count}")
    if len(result['bead_counts']) > 10:
        print(f"  ... and {len(result['bead_counts']) - 10} more colors")

    print(f"\nSaved: output_preview.png, output_pattern.png")
