import requests
from typing import List
from app.config import config
from app.wordpress.api import get_wp_auth_headers

def resolve_category_id(category_name: str) -> int:
    """Find the category ID by name. Creates it if not found? Usually we just want to find it."""
    url = f"{config.WP_BASE_URL}/wp-json/wp/v2/categories"
    headers = get_wp_auth_headers()
    params = {"search": category_name}
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    cats = response.json()
    
    for c in cats:
        if c['name'].lower() == category_name.lower() or c['slug'].lower() == category_name.lower():
            return c['id']
            
    # If not found, create it
    create_payload = {"name": category_name}
    res = requests.post(url, headers=headers, json=create_payload)
    if res.status_code == 201:
        return res.json()['id']
    else:
        # Fallback to category 1 (Uncategorized) if creation fails
        return 1

def resolve_tag_ids(tags: List[str]) -> List[int]:
    """Finds or creates tags, returning a list of their numeric IDs."""
    url = f"{config.WP_BASE_URL}/wp-json/wp/v2/tags"
    headers = get_wp_auth_headers()
    tag_ids = set()
    
    for tag in tags:
        # 1. Search for existing
        params = {"search": tag}
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            existing = response.json()
            found = False
            for t in existing:
                if t['name'].lower() == tag.lower():
                    tag_ids.add(t['id'])
                    found = True
                    break
            
            if found:
                continue
                
        # 2. If not found, create
        create_payload = {"name": tag}
        res = requests.post(url, headers=headers, json=create_payload)
        if res.status_code == 201:
            tag_ids.add(res.json()['id'])
            
    return list(tag_ids)
