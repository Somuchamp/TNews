import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def test_fetch():
    soup = BeautifulSoup(open('cricbuzz_upcoming.html').read(), 'html.parser')
    target_date = datetime.now() + timedelta(days=7)
    
    matches = []
    for h3 in soup.find_all('h3'):
        text = h3.get_text().strip()
        try:
            dt = datetime.strptime(text, "%a, %b %d %Y")
            if dt >= target_date:
                parent = h3.parent
                for a in parent.find_all('a'):
                    title = a.get('title', '')
                    if 'vs' in title.lower():
                        trend = title.split(',')[0].strip()
                        if trend not in matches:
                            matches.append(trend)
        except ValueError:
            pass
    print("Found matches:")
    for m in matches: print(m)

test_fetch()
