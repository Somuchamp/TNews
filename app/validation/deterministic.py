import re
from bs4 import BeautifulSoup
from typing import List, Tuple
from app.models import GeneratedArticle, ResearchPackage

ALLOWED_TAGS = {'p', 'h2', 'h3', 'strong', 'table', 'thead', 'tbody', 'tr', 'th', 'td'}

SEARCH_BEHAVIOR_PHRASES = [
    "search volume",
    "search demand",
    "search interest",
    "searches surged",
    "rise in searches",
    "people are searching",
    "users are searching",
    "many people are searching",
    "trending searches",
    "popular searches",
    "high search interest",
    "search queries",
    "online searches"
]

def calculate_word_count(html_content: str) -> int:
    """Calculate actual word count from HTML content (excluding FAQs)."""
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove FAQ section and everything after it to exclude from word count
    faq_headings = soup.find_all(lambda tag: tag.name in ['h2', 'h3'] and ('faq' in tag.get_text().lower() or 'frequently asked questions' in tag.get_text().lower()))
    
    if faq_headings:
        faq_heading = faq_headings[0]
        elements_to_remove = [faq_heading] + faq_heading.find_next_siblings()
        for element in elements_to_remove:
            element.extract()

    text = soup.get_text(separator=" ")
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return 0
    return len(text.split(' '))

from app.config import config

def validate_word_count(article: GeneratedArticle) -> Tuple[bool, str]:
    actual_count = calculate_word_count(article.content)
    if actual_count < config.MIN_WORD_COUNT:
        return False, f"Article must be at least {config.MIN_WORD_COUNT} words. Actual: {actual_count}"
    return True, ""

def validate_html(article: GeneratedArticle) -> Tuple[bool, str]:
    soup = BeautifulSoup(article.content, "html.parser")
    for tag in soup.find_all(True):
        if tag.name not in ALLOWED_TAGS:
            return False, f"Invalid HTML tag found: <{tag.name}>"
    return True, ""

def validate_search_behavior_language(article: GeneratedArticle) -> Tuple[bool, str]:
    text = article.content.lower()
    for phrase in SEARCH_BEHAVIOR_PHRASES:
        if phrase in text:
            return False, f"Forbidden search-behavior language found: '{phrase}'"
    return True, ""

def validate_urls_in_content(article: GeneratedArticle) -> Tuple[bool, str]:
    if re.search(r'https?://[^\s<>]+', article.content):
        return False, "Raw URLs or Google News URLs are not allowed in the article content."
    return True, ""

def validate_keyword_structure(article: GeneratedArticle, research: ResearchPackage) -> Tuple[bool, str]:
    # Since we forcefully override keywords in generator.py, this will always pass.
    # Keep lightweight checks just in case of anomaly.
    if len(article.focus_keywords) < 1:
        return False, f"Must have at least 1 focus keyword."
    return True, ""

def validate_faqs(article: GeneratedArticle) -> Tuple[bool, str]:
    soup = BeautifulSoup(article.content, "html.parser")
    faq_headings = soup.find_all(lambda tag: tag.name in ['h2', 'h3'] and ('faq' in tag.get_text().lower() or 'frequently asked questions' in tag.get_text().lower()))
    if not faq_headings:
        return False, "Article must include an FAQ section at the end."
    return True, ""

def validate_seo_keyword(article: GeneratedArticle) -> Tuple[bool, str]:
    if not article.primary_focus_keyword:
        return False, "Primary focus keyword is missing."
        
    soup = BeautifulSoup(article.content, "html.parser")
    paragraphs = soup.find_all('p')
    if not paragraphs:
        return False, "No paragraphs found in the article to check for keyword placement."
        
    first_p_text = paragraphs[0].get_text(separator=" ").strip().lower()
    keyword = article.primary_focus_keyword.lower()
    
    idx = first_p_text.find(keyword)
    if idx == -1 or idx > 75:
        return False, f"SEO Error: Primary focus keyword '{article.primary_focus_keyword}' must appear at the VERY BEGINNING of the first paragraph (found at index {idx})."
        
    text = soup.get_text(separator=" ").lower()
    count = text.count(keyword)
    if count < 4:
        return False, f"SEO Error: Primary focus keyword '{article.primary_focus_keyword}' must appear exactly at least 4 times in the content body. Found {count} times."
        
    return True, ""


def run_all_deterministic_validations(article: GeneratedArticle, research: ResearchPackage) -> List[str]:
    """Runs all validation rules and returns a list of error messages. Empty list means PASS."""
    errors = []
    
    validators = [
        lambda: validate_word_count(article),
        lambda: validate_html(article),
        lambda: validate_search_behavior_language(article),
        lambda: validate_urls_in_content(article),
        lambda: validate_keyword_structure(article, research),
        lambda: validate_faqs(article),
        lambda: validate_seo_keyword(article)
    ]
    
    for validator in validators:
        is_valid, error_msg = validator()
        if not is_valid:
            errors.append(error_msg)
            
    if article.source_key != research.source_key:
        errors.append(f"Source key mismatch! Article: {article.source_key}, Research: {research.source_key}")
        
    return errors
