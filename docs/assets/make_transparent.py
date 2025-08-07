#!/usr/bin/env python3
"""
Script to make the background of the LocoHub logo transparent.
This removes white/off-white background colors.
"""

from PIL import Image
import numpy as np

def make_background_transparent(image_path, output_path=None, tolerance=30):
    """
    Make white/off-white background transparent in an image.
    
    Args:
        image_path: Path to input image
        output_path: Path to save output (defaults to overwriting input)
        tolerance: Color tolerance for detecting background (0-255)
    """
    if output_path is None:
        output_path = image_path
    
    # Open the image
    img = Image.open(image_path)
    
    # Convert to RGBA if not already
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Convert to numpy array
    data = np.array(img)
    
    # Get the background color from corners (assume corners are background)
    corners = [
        data[0, 0],  # Top-left
        data[0, -1],  # Top-right
        data[-1, 0],  # Bottom-left
        data[-1, -1]  # Bottom-right
    ]
    
    # Find most common corner color (background color)
    bg_color = np.median(corners, axis=0).astype(int)
    
    # Create a mask for pixels close to background color
    r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]
    
    # Calculate color distance from background
    color_distance = np.sqrt(
        (r - bg_color[0])**2 + 
        (g - bg_color[1])**2 + 
        (b - bg_color[2])**2
    )
    
    # Make pixels transparent if they're close to background color
    mask = color_distance < tolerance
    data[mask, 3] = 0  # Set alpha to 0 (transparent)
    
    # Create new image from modified data
    new_img = Image.fromarray(data, 'RGBA')
    
    # Save the result
    new_img.save(output_path, 'PNG')
    print(f"Saved transparent image to: {output_path}")

if __name__ == "__main__":
    # Process the LocoHub logo
    make_background_transparent('locohub_logo.png')
    print("Background made transparent successfully!")