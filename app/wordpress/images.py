import requests
import os
from typing import Optional
from app.config import config
from app.wordpress.api import get_wp_auth_headers

def download_image(url: str, filename: str) -> Optional[str]:
    """Downloads an image securely and returns local filepath, or None on failure."""
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        
        # Verify content type
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            return None
            
        filepath = f"/tmp/{filename}"
        if os.name == 'nt':
            filepath = f"{os.getenv('TEMP')}\\{filename}"
            
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
                
        return filepath
    except Exception:
        return None

def upload_image_to_wp(filepath: str, filename: str) -> Optional[int]:
    """Uploads the local image to WordPress Media library and returns Media ID."""
    url = f"{config.WP_BASE_URL}/wp-json/wp/v2/media"
    headers = get_wp_auth_headers()
    # WordPress media upload requires Content-Disposition and Content-Type matching the file
    # Or using files payload
    
    try:
        with open(filepath, 'rb') as f:
            files = {
                'file': (filename, f, 'image/jpeg') # Fallback mimetype, WP usually infers from extension
            }
            response = requests.post(url, headers=headers, files=files)
            
        if response.status_code == 201:
            return response.json()['id']
    except Exception:
        pass
        
    return None

def resolve_image(image_url: Optional[str]) -> Optional[int]:
    """Downloads and uploads image, returning the WP Media ID if successful."""
    if not image_url:
        return None
        
    # Block google news logo scraping
    if 'news.google.com' in image_url or 'gstatic.com' in image_url:
        return None
        
    filename = image_url.split('/')[-1].split('?')[0]
    if not filename or '.' not in filename:
        filename = "downloaded_image.jpg"
        
    filepath = download_image(image_url, filename)
    if not filepath:
        return None
        
    media_id = upload_image_to_wp(filepath, filename)
    
    # Cleanup
    try:
        os.remove(filepath)
    except:
        pass
        
    return media_id
