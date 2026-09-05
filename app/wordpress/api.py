import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import base64
from app.config import config

def get_session():
    session = requests.Session()
    retry = Retry(
        total=5,
        read=5,
        connect=5,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

session = get_session()

def get_wp_auth_headers():
    token = base64.b64encode(f"{config.WP_USERNAME}:{config.WP_APP_PASSWORD}".encode('utf-8')).decode('utf-8')
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json"
    }

def check_duplicate_post(slug: str) -> bool:
    """Checks if a post with the exact slug already exists."""
    url = f"{config.WP_BASE_URL}/wp-json/wp/v2/posts"
    headers = get_wp_auth_headers()
    params = {"slug": slug, "_fields": "id,slug"}
    
    response = session.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    
    posts = response.json()
    if posts and len(posts) > 0:
        # Extra verification that the slug exactly matches
        return any(p['slug'] == slug for p in posts)
    return False

def get_existing_post_by_slug(slug: str):
    """Returns the existing post dictionary if found, otherwise None."""
    url = f"{config.WP_BASE_URL}/wp-json/wp/v2/posts"
    headers = get_wp_auth_headers()
    params = {"slug": slug}
    
    response = session.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    
    posts = response.json()
    if posts and len(posts) > 0:
        for p in posts:
            if p['slug'] == slug:
                return p
    return None

def create_or_update_post(payload: dict, slug: str) -> int:
    """Idempotent post creation. Updates if it exists, otherwise creates."""
    existing_post = get_existing_post_by_slug(slug)
    
    headers = get_wp_auth_headers()
    
    if existing_post:
        # Update
        post_id = existing_post['id']
        url = f"{config.WP_BASE_URL}/wp-json/wp/v2/posts/{post_id}"
        response = session.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return post_id
    else:
        # Create
        url = f"{config.WP_BASE_URL}/wp-json/wp/v2/posts"
        response = session.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()['id']

def get_recent_posts_by_category(category_id: int, limit: int = 2, exclude_slug: str = None) -> list:
    """Fetches recent published posts for a given category to use in 'Also Read' sections."""
    url = f"{config.WP_BASE_URL}/wp-json/wp/v2/posts"
    headers = get_wp_auth_headers()
    params = {
        "categories": category_id,
        "status": "publish",
        "per_page": limit + 1,
        "_fields": "title,link,slug",
        "orderby": "date",
        "order": "desc"
    }
    try:
        response = session.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        posts = response.json()
        
        results = []
        for p in posts:
            if exclude_slug and p.get("slug") == exclude_slug:
                continue
            title = p.get("title", {}).get("rendered", "")
            # Clean up HTML entities in title if any, though WP usually returns them encoded. We can leave it to the browser.
            link = p.get("link", "")
            if title and link:
                results.append({"title": title, "link": link})
            if len(results) >= limit:
                break
        return results
    except Exception as e:
        import logging
        logging.error(f"Failed to fetch recent posts for category {category_id}: {e}")
        return []
