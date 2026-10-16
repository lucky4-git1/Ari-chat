import os
from PIL import Image, ImageDraw

def create_ari_icon():
    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        # Create image with transparent background
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw rounded dark slate / indigo background
        padding = max(1, int(size * 0.05))
        corner_radius = max(2, int(size * 0.22))
        bg_bbox = [padding, padding, size - padding, size - padding]
        
        # Indigo/slate dark background
        draw.rounded_rectangle(bg_bbox, radius=corner_radius, fill=(15, 23, 42, 255))
        
        # Subtle border
        draw.rounded_rectangle(bg_bbox, radius=corner_radius, outline=(99, 102, 241, 180), width=max(1, int(size * 0.03)))

        # Draw Ari "A" geometric chevron
        # Triangle points: top (32, 8), bottom-left (10, 52), inner-left (22, 52), inner-top (32, 32), inner-right (42, 52), bottom-right (54, 52)
        scale = size / 64.0
        poly_pts = [
            (32 * scale, 12 * scale),
            (14 * scale, 50 * scale),
            (23 * scale, 50 * scale),
            (32 * scale, 32 * scale),
            (41 * scale, 50 * scale),
            (50 * scale, 50 * scale),
        ]
        # Modern vibrant indigo-cyan color
        draw.polygon(poly_pts, fill=(248, 250, 252, 255))
        
        # Central glowing dot
        dot_r = 3.5 * scale
        dot_cx, dot_cy = 32 * scale, 41 * scale
        draw.ellipse([dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r], fill=(99, 102, 241, 255))

        images.append(img)

    # Save multi-resolution .ico
    target_path = "e:/Ari-llm-source/ari-chat-app/app.ico"
    images[-1].save(
        target_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1]
    )
    print(f"[OK] Generated {target_path}")

    # Also save static png and ico
    static_ico = "e:/Ari-llm-source/ari-chat-app/static/img/favicon.ico"
    static_png = "e:/Ari-llm-source/ari-chat-app/static/img/logo.png"
    images[-1].save(static_ico, format="ICO")
    images[-1].save(static_png, format="PNG")
    print(f"[OK] Generated {static_ico} and {static_png}")

if __name__ == "__main__":
    create_ari_icon()
