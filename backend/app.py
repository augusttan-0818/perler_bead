"""
Flask API for Perler Bead Pattern Converter

Endpoints:
- POST /convert - Convert an image to a bead pattern
- GET /health - Health check
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import io
import base64
from converter import convert_image_simple, convert_image_dithered, generate_pattern_grid
from mard_colors import MARD_221_COLORS

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "colors": len(MARD_221_COLORS)})


@app.route('/convert', methods=['POST'])
def convert():
    """
    Convert an uploaded image to a bead pattern.

    Request:
        - image: File upload OR base64 encoded image
        - grid_width: int (default 29)
        - grid_height: int (default 29)
        - use_dithering: bool (default true)

    Response:
        {
            "success": true,
            "preview_image": "base64...",  # Scaled up preview
            "pattern_image": "base64...",  # Printable pattern with labels
            "bead_counts": {"A5": 47, "A6": 82, ...},
            "total_beads": 841,
            "colors_used": 12,
            "grid_size": "29x29"
        }
    """
    try:
        # Get image from request
        if 'image' in request.files:
            # File upload
            image_file = request.files['image']
            image = Image.open(image_file.stream)
        elif request.is_json and 'image' in request.json:
            # Base64 encoded image
            image_data = request.json['image']
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
        else:
            return jsonify({"success": False, "error": "No image provided"}), 400

        # Get parameters
        if request.is_json:
            data = request.json
        else:
            data = request.form

        grid_width = int(data.get('grid_width', 29))
        grid_height = int(data.get('grid_height', 29))
        use_dithering = str(data.get('use_dithering', 'true')).lower() == 'true'

        # Validate grid size
        if grid_width < 1 or grid_width > 100 or grid_height < 1 or grid_height > 100:
            return jsonify({"success": False, "error": "Grid size must be 1-100"}), 400

        # Convert image
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

        # Scale up preview for visibility
        scale = 20
        preview_scaled = output_image.resize(
            (grid_width * scale, grid_height * scale),
            Image.Resampling.NEAREST
        )

        # Convert images to base64
        def image_to_base64(img):
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            return base64.b64encode(buffer.read()).decode('utf-8')

        preview_b64 = image_to_base64(preview_scaled)
        pattern_b64 = image_to_base64(pattern_grid)

        # Sort bead counts by quantity (descending)
        sorted_counts = dict(sorted(bead_counts.items(), key=lambda x: -x[1]))

        return jsonify({
            "success": True,
            "preview_image": f"data:image/png;base64,{preview_b64}",
            "pattern_image": f"data:image/png;base64,{pattern_b64}",
            "bead_counts": sorted_counts,
            "total_beads": sum(bead_counts.values()),
            "colors_used": len(bead_counts),
            "grid_size": f"{grid_width}x{grid_height}"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/colors', methods=['GET'])
def get_colors():
    """Get all available MARD 221 colors."""
    return jsonify({
        "success": True,
        "colors": MARD_221_COLORS,
        "count": len(MARD_221_COLORS)
    })


if __name__ == '__main__':
    print("Starting Perler Bead Pattern Converter API...")
    print("Endpoints:")
    print("  GET  /health  - Health check")
    print("  POST /convert - Convert image to bead pattern")
    print("  GET  /colors  - Get all MARD 221 colors")
    print("")
    app.run(debug=True, port=5000)
