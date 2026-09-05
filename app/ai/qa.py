import json
from openai import OpenAI
from typing import Tuple, List
from app.config import config
from app.models import ResearchPackage, GeneratedArticle
from app.ai.prompts import QA_PROMPT
from dataclasses import asdict

client = OpenAI(api_key=config.OPENAI_API_KEY, timeout=120.0)

def run_factual_qa(research: ResearchPackage, article: GeneratedArticle) -> Tuple[bool, List[str]]:
    """Runs a strict LLM-based factual QA check against the original research."""
    user_content = json.dumps({
        "original_research": asdict(research),
        "generated_article": asdict(article)
    }, indent=2)
    
    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": QA_PROMPT},
            {"role": "user", "content": f"Please verify:\n{user_content}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.0 # Zero temperature for max strictness
    )
    
    content_str = response.choices[0].message.content
    try:
        data = json.loads(content_str)
        is_pass = data.get("pass", False)
        errors = data.get("errors", [])
        return is_pass, errors
    except Exception as e:
        return False, [f"Failed to parse QA output: {str(e)}"]
