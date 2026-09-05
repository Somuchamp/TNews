import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List
from app.models import ResearchPackage
from app.research.collector import fetch_google_news_rss, get_source_score, get_topic_score

def fetch_upcoming_matches(days_ahead=7) -> List[ResearchPackage]:
    url = 'https://www.cricbuzz.com/cricket-schedule/upcoming-series/international'
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    print(f"Fetching upcoming cricket schedule from Cricbuzz...")
    response = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    target_date = datetime.utcnow() + timedelta(days=days_ahead)
    packages = []
    
    for h3 in soup.find_all('h3'):
        text = h3.get_text().strip()
        try:
            dt = datetime.strptime(text, "%a, %b %d %Y")
            if dt >= target_date:
                parent = h3.parent
                for a in parent.find_all('a'):
                    title = a.get('title', '')
                    # Look for match titles, skip the "Live Cricket Score" abbreviation titles
                    if 'vs' in title.lower() and 'Live Cricket Score' not in title:
                        trend_keyword = title.split(',')[0].strip()
                        
                        # Avoid duplicates
                        if any(p.trend == trend_keyword for p in packages):
                            continue
                            
                        print(f"Found upcoming match: {trend_keyword} on {dt.strftime('%Y-%m-%d')}")
                        
                        # Fetch related news for this match
                        sports_query = f"{trend_keyword} site:cricbuzz.com OR site:espncricinfo.com"
                        sources = fetch_google_news_rss(sports_query, limit=5)
                        
                        source_score = get_source_score(sources)
                        topic_score = get_topic_score(trend_keyword, sources)
                        
                        packages.append(ResearchPackage(
                            trend=trend_keyword,
                            trend_breakdown=[f"{trend_keyword} preview", f"{trend_keyword} prediction", f"{trend_keyword} playing 11", f"{trend_keyword} pitch report", f"{trend_keyword} live"],
                            published_at=dt.isoformat() + "Z",
                            category="Sports",
                            sources=sources,
                            search_volume=50000,
                            newsworthiness_score=source_score + topic_score + 20
                        ))
        except ValueError:
            continue

    return packages
