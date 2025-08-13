#!/usr/bin/env python3
"""
Script to create a social card version of logo3.png with blue background
"""

from PIL import Image, ImageDraw
import os

def create_social_logo():
    """Create logo3-social.png with blue background for social cards"""
    
    # Define paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    img_dir = os.path.join(script_dir, 'app', 'static', 'img')
    original_logo = os.path.join(img_dir, 'logo3.png')
    social_logo = os.path.join(img_dir, 'logo3-social.png')
    
    if not os.path.exists(original_logo):
        print(f"Original logo not found at: {original_logo}")
        return False
        
    try:
        # Open the original logo
        logo = Image.open(original_logo)
        
        # Convert to RGBA if not already
        logo = logo.convert('RGBA')
        
        # Define the blue gradient colors (matching the site's theme)
        blue_start = (37, 99, 235)  # #2563eb
        blue_end = (59, 130, 246)   # #3b82f6
        
        # Create optimal social card dimensions (1200x630 recommended for Facebook/Twitter)
        social_width = 1200
        social_height = 630
        
        # Calculate logo size (keep aspect ratio, max 60% of card height)
        max_logo_height = int(social_height * 0.6)
        logo_ratio = logo.width / logo.height
        
        if logo.height > max_logo_height:
            new_logo_height = max_logo_height
            new_logo_width = int(new_logo_height * logo_ratio)
        else:
            new_logo_width = logo.width
            new_logo_height = logo.height
            
        # Resize logo if needed
        if new_logo_width != logo.width or new_logo_height != logo.height:
            logo = logo.resize((new_logo_width, new_logo_height), Image.LANCZOS)
        
        # Create the social card background with gradient
        social_card = Image.new('RGB', (social_width, social_height), blue_start)
        
        # Create a simple vertical gradient
        for y in range(social_height):
            # Calculate gradient position (0 to 1)
            gradient_pos = y / social_height
            
            # Interpolate between start and end colors
            r = int(blue_start[0] + (blue_end[0] - blue_start[0]) * gradient_pos)
            g = int(blue_start[1] + (blue_end[1] - blue_start[1]) * gradient_pos)
            b = int(blue_start[2] + (blue_end[2] - blue_start[2]) * gradient_pos)
            
            # Draw horizontal line with interpolated color
            draw = ImageDraw.Draw(social_card)
            draw.line([(0, y), (social_width, y)], fill=(r, g, b))
        
        # Calculate position to center the logo
        logo_x = (social_width - new_logo_width) // 2
        logo_y = (social_height - new_logo_height) // 2
        
        # Paste the logo onto the social card
        # If logo has transparency, use it as mask
        if logo.mode == 'RGBA':
            social_card.paste(logo, (logo_x, logo_y), logo)
        else:
            social_card.paste(logo, (logo_x, logo_y))
        
        # Save the social card version
        social_card.save(social_logo, 'PNG', quality=95, optimize=True)
        
        print(f"Social card logo created successfully at: {social_logo}")
        print(f"Dimensions: {social_width}x{social_height}")
        print(f"Logo size: {new_logo_width}x{new_logo_height}")
        
        return True
        
    except Exception as e:
        print(f"Error creating social logo: {str(e)}")
        return False

if __name__ == "__main__":
    # Check if PIL is available
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("PIL (Pillow) is required. Install it with: pip install Pillow")
        exit(1)
    
    success = create_social_logo()
    if not success:
        exit(1)
