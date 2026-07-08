"""
Screenshot Sanitization Script
Blurs sensitive information (API endpoints, IP addresses) in screenshots
"""
import os
from PIL import Image, ImageFilter

INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sanitized")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def blur_region(img, x1, y1, x2, y2, blur_radius=15):
    """Blur a specific region of the image"""
    region = img.crop((x1, y1, x2, y2))
    blurred = region.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    img.paste(blurred, (x1, y1))
    return img

def sanitize_dashboard(img):
    """Dashboard: blur IP info section and status bar"""
    w, h = img.size
    
    # IP info panel - right side, middle section
    # Based on 1920x1080 screenshot
    img = blur_region(img, 770, 430, 1140, 780)  # IP info card area
    
    # Status bar at bottom - provider info
    img = blur_region(img, 60, 1060, 250, 1080)
    
    return img

def sanitize_provider_modal(img):
    """Provider modal: brute-force blur entire subtitle zones"""
    w, h = img.size
    
    # Column 1 (Image): blur a tall band covering all 3 provider subtitles
    img = blur_region(img, 220, 380, 415, 500)
    
    # Column 2 (Video): blur the subtitle area
    img = blur_region(img, 580, 380, 775, 410)
    
    # Column 3 (LLM): blur the subtitle area
    img = blur_region(img, 920, 380, 1105, 410)
    
    # Proxy IP/port row
    img = blur_region(img, 310, 270, 485, 305)
    
    return img

def sanitize_llm_modal(img):
    """LLM modal: blur provider details"""
    # LLM provider subtitle
    img = blur_region(img, 570, 420, 680, 435)
    return img

def sanitize_generate(img):
    """Generate page: blur status bar"""
    img = blur_region(img, 60, 1060, 250, 1080)
    return img

def sanitize_video(img):
    """Video page: blur status bar"""
    img = blur_region(img, 60, 1060, 250, 1080)
    return img

def sanitize_gallery(img):
    """Gallery: blur status bar"""
    img = blur_region(img, 60, 1060, 250, 1080)
    return img

def sanitize_history(img):
    """History: blur status bar"""
    img = blur_region(img, 60, 1060, 250, 1080)
    return img

# sanitization map: filename -> function
SANITIZERS = {
    "01-dashboard.png": sanitize_dashboard,
    "02-generate-t2i.png": sanitize_generate,
    "03-generate-i2i.png": sanitize_generate,
    "04-generate-variation.png": sanitize_generate,
    "05-video-t2v.png": sanitize_video,
    "06-video-i2v.png": sanitize_video,
    "07-video-keyframes.png": sanitize_video,
    "08-video-advanced.png": sanitize_video,
    "09-gallery-images.png": sanitize_gallery,
    "10-gallery-videos.png": sanitize_gallery,
    "11-history.png": sanitize_history,
    "12-modal-provider.png": sanitize_provider_modal,
    "13-modal-theme.png": lambda img: img,  # no sensitive info
    "14-modal-log.png": lambda img: img,    # no sensitive info
    "15-modal-llm.png": sanitize_llm_modal,
    "16-dashboard-full.png": sanitize_dashboard,
    "17-generate-full.png": sanitize_generate,
    "18-video-full.png": sanitize_video,
    "19-gallery-full.png": sanitize_gallery,
    "20-history-full.png": sanitize_history,
}

def main():
    print("Sanitizing screenshots...")
    
    for filename, sanitizer in SANITIZERS.items():
        input_path = os.path.join(INPUT_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, filename)
        
        if not os.path.exists(input_path):
            print(f"  [SKIP] {filename} not found")
            continue
        
        img = Image.open(input_path)
        img = sanitizer(img)
        img.save(output_path, quality=95)
        
        size_kb = os.path.getsize(output_path) / 1024
        print(f"  [OK] {filename} ({size_kb:.0f} KB)")
    
    print(f"\nDone! Sanitized screenshots saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
