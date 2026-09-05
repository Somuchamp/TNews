import json
from openai import OpenAI
from app.config import config
from app.models import ResearchPackage
from dataclasses import asdict

client = OpenAI(api_key=config.OPENAI_API_KEY, timeout=30.0)

CLASSIFIER_PROMPT = """You are the editorial news classifier for TraceNews.in. 
Your job is NOT to write an article. Your job is to determine whether a Google Trends topic represents a genuine, timely news story that is worth researching for publication on TraceNews.in. 

Evaluate: 
1. Whether the trend represents a specific news event. 
2. Whether the related articles describe the same underlying event. 
3. Whether the event is recent/current. 
4. Whether there is enough information to research the story. 
5. Whether the topic is suitable for a general news website. 
6. Whether it is primarily spam, lottery results, generic search intent, evergreen information, promotional content, or another low-value topic. 

Do not assume that a high Google Trends score means the topic is newsworthy. Do not invent facts. Return ONLY valid JSON. 

Return exactly:
{ 
  "is_newsworthy": true/false, 
  "confidence": 0.0, 
  "category": "Sports", 
  "story_angle": "", 
  "reason": "", 
  "risk_level": "low", 
  "recommended_action": "research" 
} 

Allowed categories: Politics, Business, Technology, Sports, World, India, Entertainment, Science, Health, Lifestyle, Other 
Allowed risk levels: low, medium, high 
Allowed actions: research, reject, manual_review
"""

def classify_trend(research: ResearchPackage) -> ResearchPackage:
    """Uses LLM to classify if a trend is newsworthy and determines its category and angle."""
    user_content = json.dumps({
        "trend": research.trend,
        "search_volume": research.search_volume,
        "published_at": research.published_at,
        "newsworthiness_score": research.newsworthiness_score,
        "related_news": [asdict(s) for s in research.sources]
    }, indent=2)
    
    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": CLASSIFIER_PROMPT},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        content_str = response.choices[0].message.content
        data = json.loads(content_str)
        
        research.is_newsworthy = data.get("is_newsworthy", False)
        research.category = data.get("category", "Other")
        research.story_angle = data.get("story_angle", "")
        
        # If the action is reject, ensure is_newsworthy is False
        if data.get("recommended_action") == "reject":
            research.is_newsworthy = False
            
    except Exception as e:
        print(f"[CLASSIFIER ERROR] {e}")
        research.is_newsworthy = False
        
    return research
