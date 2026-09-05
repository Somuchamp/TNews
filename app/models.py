from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import re

@dataclass
class ResearchSource:
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None

@dataclass
class ResearchPackage:
    trend: str
    trend_breakdown: List[str]
    published_at: str
    category: str
    sources: List[ResearchSource]
    search_volume: int = 0
    newsworthiness_score: int = 0
    story_angle: str = ""
    is_newsworthy: bool = False
    paa_questions: List[dict] = field(default_factory=list)
    sports_data: str = ""
    
    @property
    def source_key(self) -> str:
        # Create a stable source key: trend|published_at|category
        # Strip and lower to ensure stability
        t = self.trend.strip().lower()
        p = self.published_at.strip().lower()
        c = self.category.strip().lower()
        return f"{t}|{p}|{c}"

@dataclass
class GeneratedArticle:
    source_key: str
    title: str
    slug: str
    content: str # HTML content
    excerpt: str
    primary_focus_keyword: str
    focus_keywords: List[str]
    related_keywords: List[str] = field(default_factory=list)
    word_count: int = 0
    faq_included: bool = False
    table_included: bool = False

@dataclass
class ArticleState:
    source_key: str
    research: ResearchPackage
    status: str = "RESEARCH_READY"
    article: Optional[GeneratedArticle] = None
    
    # WordPress resolutions
    category_id: Optional[int] = None
    tag_ids: List[int] = field(default_factory=list)
    media_id: Optional[int] = None
    wordpress_post_id: Optional[int] = None
    
    validation_errors: List[str] = field(default_factory=list)
