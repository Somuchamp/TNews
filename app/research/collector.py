import json
import urllib.parse
import requests
import feedparser
import re
from bs4 import BeautifulSoup
from typing import List, Optional, Dict
from datetime import datetime
from app.models import ResearchPackage, ResearchSource

def get_traffic_score(value: str) -> int:
    try:
        clean_val = re.sub(r'[^0-9KMBkmb+.]', '', str(value))
        number = 0
        if 'K' in clean_val.upper() or 'k' in clean_val.lower():
            number = float(re.sub(r'[^0-9.]', '', clean_val)) * 1000
        elif 'M' in clean_val.upper() or 'm' in clean_val.lower():
            number = float(re.sub(r'[^0-9.]', '', clean_val)) * 1000000
        else:
            number = float(re.sub(r'[^0-9.]', '', clean_val) or 0)
            
        if number >= 500000: return 35
        if number >= 100000: return 30
        if number >= 50000: return 25
        if number >= 20000: return 20
        if number >= 10000: return 17
        if number >= 5000: return 14
        if number >= 2000: return 11
        if number >= 1000: return 8
        if number >= 500: return 5
        return 2
    except:
        return 2

def get_source_score(sources: List[ResearchSource]) -> int:
    unique_sources = set(s.source_name.lower() for s in sources if getattr(s, 'source_name', None))
    score = 0
    if len(unique_sources) >= 3:
        score += 25
    elif len(unique_sources) == 2:
        score += 18
    elif len(unique_sources) == 1:
        score += 8

    reputable = ["the hindu", "reuters", "associated press", "bbc", "times of india", 
                 "aajtak", "aaj tak", "indian express", "hindustan times", 
                 "moneycontrol", "news18", "navbharat times", "jagran"]
    
    rep_count = sum(1 for s in unique_sources if any(r in s for r in reputable))
    if rep_count >= 2:
        score += 15
    elif rep_count == 1:
        score += 8
    return score

def get_topic_score(trend: str, sources: List[ResearchSource]) -> int:
    text = (trend + " " + " ".join(s.title for s in sources)).lower()
    score = 0
    keywords = ["breaking", "latest", "announced", "announcement", "government", 
                "minister", "election", "protest", "earthquake", "accident", 
                "death", "killed", "launch", "launched", "record", "india", 
                "pakistan", "china", "bangladesh", "russia", "usa", "president", "prime minister"]
    for k in keywords:
        if k in text:
            score += 2
    return min(score, 15)

def extract_image_from_rss_entry(entry) -> Optional[str]:
    # Try media:content
    if 'media_content' in entry and len(entry.media_content) > 0:
        return entry.media_content[0].get('url')
    # Try media:thumbnail
    if 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
        return entry.media_thumbnail[0].get('url')
    # Try HTML parsing in description
    if 'description' in entry:
        soup = BeautifulSoup(entry.description, 'html.parser')
        img = soup.find('img')
        if img and img.get('src'):
            return img['src']
    return None

def fetch_google_news_rss(query: str, limit: int = 10) -> List[ResearchSource]:
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    feed = feedparser.parse(rss_url)
    sources = []
    
    for i, entry in enumerate(feed.entries[:limit]):
        img_url = extract_image_from_rss_entry(entry)
        soup = BeautifulSoup(entry.get('description', ''), 'html.parser')
        clean_desc = soup.get_text(separator=' ').strip()
        
        # Scrape full text for the top 3 results to give the AI enough factual material
        if i < 3 and hasattr(entry, 'link'):
            try:
                # Need to use a generic user agent to bypass simple blocks
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                res = requests.get(entry.link, headers=headers, timeout=5)
                if res.status_code == 200:
                    page_soup = BeautifulSoup(res.text, 'html.parser')
                    # Very simple body extraction: grab all <p> tags
                    paragraphs = page_soup.find_all('p')
                    body_text = " ".join(p.get_text() for p in paragraphs)
                    if len(body_text) > 200:
                        clean_desc += "\n\nFULL TEXT:\n" + body_text[:2500] # Limit to 2500 chars to avoid blowing up context
            except Exception:
                pass
        
        rs = ResearchSource(
            title=entry.title,
            description=clean_desc,
            url=entry.link,
            image_url=img_url
        )
        # Add source_name dynamically for scoring
        rs.source_name = entry.get('source', {}).get('title', '') if hasattr(entry, 'source') else ''
        sources.append(rs)
        
    return sources

def parse_trends_data(data: list) -> List[ResearchPackage]:
    # Extract raw trends first
    raw_trends = []
    for item in data:
        if 'data' in item and isinstance(item['data'], str):
            try:
                inner_data = json.loads(item['data'])
            except json.JSONDecodeError:
                continue
        else:
            inner_data = item
            
        trends_list = inner_data.get('items', [])
        for trend_item in trends_list:
            if not trend_item.get('query'):
                continue
                
            # Filter out meaningless generic keywords
            q_lower = trend_item['query'].lower().strip()
            if q_lower in ['search', 'news', 'update', 'today', 'latest', 'google', 'outlook']:
                continue
                
            raw_trends.append(trend_item)

    # Parse actual search volume to integer for accurate sorting
    for rt in raw_trends:
        search_volume = rt.get('search_volume', '0')
        volume_int = 0
        try:
            val = str(search_volume).replace('+', '').replace(',', '')
            if 'K' in val.upper(): volume_int = int(float(val.upper().replace('K', '')) * 1000)
            elif 'M' in val.upper(): volume_int = int(float(val.upper().replace('M', '')) * 1000000)
            else: volume_int = int(val)
        except:
            volume_int = 0
            
        rt['volume_int'] = volume_int
        rt['traffic_score'] = get_traffic_score(search_volume)
    
    # Sort by actual search volume first, then traffic score, and limit to top 20
    raw_trends = sorted(raw_trends, key=lambda x: (x['volume_int'], x['traffic_score']), reverse=True)[:20]

    packages = []
    for trend_item in raw_trends:
        trend_keyword = trend_item.get('query', '')
        breakdown = trend_item.get('trend_breakdown', [])
        published_at = trend_item.get('started_at', datetime.utcnow().isoformat())
        categories = trend_item.get('categories', [])
        category_name = categories[0].get('name', 'General') if categories else 'General'
        traffic_score = trend_item.get('traffic_score', 0)
        volume_int = trend_item.get('volume_int', 0)

        # Fetch actual news articles
        sources = fetch_google_news_rss(trend_keyword)
        
        if category_name.lower() == 'sports' or 'cricket' in trend_keyword.lower():
            sports_query = f"{trend_keyword} site:cricbuzz.com OR site:espncricinfo.com"
            sports_sources = fetch_google_news_rss(sports_query, limit=5)
            existing_urls = {s.url for s in sources}
            for s in sports_sources:
                if s.url not in existing_urls:
                    sources.append(s)
                    existing_urls.add(s.url)
        
        # Calculate full Newsworthiness Score
        source_score = get_source_score(sources)
        topic_score = get_topic_score(trend_keyword, sources)
        total_score = traffic_score + source_score + topic_score

        packages.append(ResearchPackage(
            trend=trend_keyword,
            trend_breakdown=breakdown,
            published_at=published_at,
            category=category_name,
            sources=sources,
            search_volume=volume_int,
            newsworthiness_score=total_score
        ))
        
    # Final sort by search volume first, then total newsworthiness score
    packages.sort(key=lambda x: (x.search_volume, x.newsworthiness_score), reverse=True)
    return packages

def parse_trends_json(filepath: str) -> List[ResearchPackage]:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return parse_trends_data(data)

def fetch_live_trends(geo: str = "IN", hours: int = 4, limit: int = 100) -> List[ResearchPackage]:
    url = "https://google-trends-api-eight-ashy.vercel.app/api/trends"
    params = {"geo": geo, "hours": hours, "limit": limit}
    print(f"Fetching live trends from {url}...")
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    if not isinstance(data, list):
        data = [data]
        
    return parse_trends_data(data)
