import json
from openai import OpenAI
from app.config import config
from app.models import ResearchPackage, GeneratedArticle
from app.ai.prompts import SYSTEM_PROMPT, REPAIR_PROMPT
from dataclasses import asdict

client = OpenAI(api_key=config.OPENAI_API_KEY, timeout=120.0)

import re

def safe_json_loads(json_str: str) -> dict:
    try:
        return json.loads(json_str, strict=False)
    except json.JSONDecodeError:
        # LLMs often hallucinate literal "\u" without 4 hex digits, breaking JSON
        fixed_str = re.sub(r'\\u(?![0-9a-fA-F]{4})', r'\\\\u', json_str)
        try:
            return json.loads(fixed_str, strict=False)
        except Exception:
            return {}

def generate_article(research: ResearchPackage) -> GeneratedArticle:
    """Generate the initial article."""
    user_content = json.dumps(asdict(research), indent=2)
    
    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Research Data:\n{user_content}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=6000
    )
    
    content_str = response.choices[0].message.content
    data = safe_json_loads(content_str)
    primary_kw = data.get("primary_focus_keyword", research.trend)
    
    # Guarantee focus_keywords has exactly 5 items
    focus_kws = data.get("focus_keywords", [])
    if not isinstance(focus_kws, list):
        focus_kws = []
    
    # Ensure first keyword is the translated primary keyword
    if len(focus_kws) > 0:
        focus_kws[0] = primary_kw
    else:
        focus_kws.append(primary_kw)
        
    # Pad to 5 keywords if AI failed to generate enough
    while len(focus_kws) < 5:
        focus_kws.append(f"{primary_kw} latest update {len(focus_kws)}")
        
    # Truncate to 5 keywords if AI generated too many
    focus_kws = focus_kws[:5]
    
    return GeneratedArticle(
        source_key=research.source_key,
        title=data.get("title", ""),
        slug=data.get("slug", ""),
        content=data.get("content", ""),
        excerpt=data.get("excerpt", ""),
        primary_focus_keyword=primary_kw,
        focus_keywords=focus_kws,
        related_keywords=data.get("related_keywords", []),
        faq_included=data.get("faq_included", False),
        table_included=data.get("table_included", False),
        word_count=0  # Will be calculated by validator
    )

def repair_article(research: ResearchPackage, previous_article: GeneratedArticle, errors: list[str]) -> GeneratedArticle:
    """Repair an article that failed deterministic validation."""
    user_content = json.dumps({
        "original_research": asdict(research),
        "failed_article": asdict(previous_article),
        "validation_errors": errors
    }, indent=2)
    
    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": REPAIR_PROMPT},
            {"role": "user", "content": f"Repair Request:\n{user_content}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.5,
        max_tokens=6000
    )
    
    content_str = response.choices[0].message.content
    data = safe_json_loads(content_str)
    primary_kw = data.get("primary_focus_keyword", research.trend)
    
    # Guarantee focus_keywords has exactly 5 items
    focus_kws = data.get("focus_keywords", [])
    if not isinstance(focus_kws, list):
        focus_kws = []
    
    # Ensure first keyword is the translated primary keyword
    if len(focus_kws) > 0:
        focus_kws[0] = primary_kw
    else:
        focus_kws.append(primary_kw)
        
    # Pad to 5 keywords if AI failed to generate enough
    while len(focus_kws) < 5:
        focus_kws.append(f"{primary_kw} latest update {len(focus_kws)}")
        
    # Truncate to 5 keywords if AI generated too many
    focus_kws = focus_kws[:5]
    
    return GeneratedArticle(
        source_key=research.source_key,
        title=data.get("title", ""),
        slug=data.get("slug", ""),
        content=data.get("content", ""),
        excerpt=data.get("excerpt", ""),
        primary_focus_keyword=primary_kw,
        focus_keywords=focus_kws,
        related_keywords=data.get("related_keywords", []),
        faq_included=data.get("faq_included", False),
        table_included=data.get("table_included", False),
        word_count=0
    )
