import requests
import logging
from app.config import config

def fetch_paa_questions(keyword: str) -> list[dict]:
    """
    Fetches Google "People Also Ask" questions and answer snippets for a given keyword using ValueSERP API.
    Returns the top 3-4 questions as dictionaries.
    """
    if not config.VALUESERP_API_KEY or config.VALUESERP_API_KEY == "your_valueserp_key_here":
        logging.warning("VALUESERP_API_KEY not found or invalid. Skipping PAA fetch.")
        return []
        
    params = {
      'api_key': config.VALUESERP_API_KEY,
      'q': keyword,
      'gl': 'in',
      'hl': 'en',
      'num': 10 # We only need the first page for PAA
    }
    
    try:
        logging.info(f"[SERP] Fetching PAA questions for: {keyword}")
        response = requests.get('https://api.valueserp.com/search', params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        paa_list = []
        if 'related_questions' in data:
            for item in data['related_questions']:
                if 'question' in item:
                    paa_list.append({
                        "question": item['question'],
                        "answer": item.get('snippet', 'No snippet available. Generate answer based on context.')
                    })
                    
        logging.info(f"[SERP] Found {len(paa_list)} PAA questions for {keyword}")
        return paa_list[:4] # Return up to top 4 questions
    except Exception as e:
        logging.error(f"[SERP] Failed to fetch PAA from ValueSERP for {keyword}: {e}")
        return []

def fetch_sports_data(keyword: str) -> str:
    """
    Fetches the latest match scores and stats from sports sites (espncricinfo, cricbuzz)
    to provide the AI with actual numbers for tables.
    """
    if not config.VALUESERP_API_KEY or config.VALUESERP_API_KEY == "your_valueserp_key_here":
        return ""
        
    params = {
      'api_key': config.VALUESERP_API_KEY,
      'q': f"{keyword} score site:espncricinfo.com OR site:cricbuzz.com",
      'gl': 'in',
      'hl': 'en',
      'num': 3
    }
    
    try:
        logging.info(f"[SERP] Fetching sports data for: {keyword}")
        response = requests.get('https://api.valueserp.com/search', params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        snippets = []
        if 'organic_results' in data:
            for item in data['organic_results']:
                title = item.get('title', '')
                snippet = item.get('snippet', '')
                if snippet:
                    snippets.append(f"[{title}]: {snippet}")
                    
        result = " | ".join(snippets)
        if result:
            logging.info(f"[SERP] Found sports data for {keyword}")
        return result
    except Exception as e:
        logging.error(f"[SERP] Failed to fetch sports data for {keyword}: {e}")
        return ""
