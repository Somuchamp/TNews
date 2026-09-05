import pytest
from app.models import GeneratedArticle, ResearchPackage
from app.validation.deterministic import (
    calculate_word_count,
    validate_word_count,
    validate_html,
    validate_search_behavior_language,
    validate_keyword_structure,
    validate_urls_in_content,
    run_all_deterministic_validations
)

@pytest.fixture
def mock_research():
    return ResearchPackage(
        trend="GV Narayana Rao",
        trend_breakdown=["GV Narayana Rao actor", "GV Narayana Rao movies", "GV Narayana Rao age", "GV Narayana Rao news", "GV Narayana Rao wife"],
        published_at="2026-08-28T05:00:00.000Z",
        category="Entertainment",
        sources=[]
    )

@pytest.fixture
def valid_article(mock_research):
    content = "<p>This is the opening paragraph about GV Narayana Rao.</p>"
    # Add exactly 750 words total
    content += "<p>" + "word " * (750 - 9) + "</p>"
    
    return GeneratedArticle(
        source_key=mock_research.source_key,
        title="GV Narayana Rao Updates",
        slug="gv-narayana-rao-updates",
        content=content,
        excerpt="Summary",
        primary_focus_keyword="GV Narayana Rao",
        focus_keywords=["GV Narayana Rao", "GV Narayana Rao actor", "GV Narayana Rao movies", "GV Narayana Rao age", "GV Narayana Rao news"],
        related_keywords=[]
    )

def test_word_count_749_fails(valid_article):
    # 749 words
    valid_article.content = "<p>" + "word " * 749 + "</p>"
    is_valid, msg = validate_word_count(valid_article)
    assert not is_valid
    assert "at least 750 words" in msg

def test_word_count_750_passes(valid_article):
    # 750 words
    valid_article.content = "<p>" + "word " * 750 + "</p>"
    is_valid, msg = validate_word_count(valid_article)
    assert is_valid

def test_invalid_html_fails(valid_article):
    valid_article.content = "<div><p>GV Narayana Rao</p></div>" + "<p>word </p>" * 750
    is_valid, msg = validate_html(valid_article)
    assert not is_valid
    assert "Invalid HTML tag found: <div>" in msg

def test_search_behavior_fails(valid_article):
    valid_article.content = "<p>GV Narayana Rao</p><p>There is high search interest for this.</p>" + "<p>word </p>" * 750
    is_valid, msg = validate_search_behavior_language(valid_article)
    assert not is_valid
    assert "search interest" in msg

def test_keyword_structure_exact_match(valid_article, mock_research):
    is_valid, msg = validate_keyword_structure(valid_article, mock_research)
    assert is_valid

def test_keyword_structure_duplicate_fails(valid_article, mock_research):
    valid_article.focus_keywords = ["GV Narayana Rao", "GV Narayana Rao", "GV Narayana Rao movies", "GV Narayana Rao age", "GV Narayana Rao news"]
    is_valid, msg = validate_keyword_structure(valid_article, mock_research)
    assert not is_valid
    assert "must be unique" in msg

def test_keyword_structure_altered_breakdown_fails(valid_article, mock_research):
    # Altered phrase
    valid_article.focus_keywords = ["GV Narayana Rao", "GV Narayana Rao the actor", "GV Narayana Rao movies", "GV Narayana Rao age", "GV Narayana Rao news"]
    is_valid, msg = validate_keyword_structure(valid_article, mock_research)
    assert not is_valid
    assert "Must preserve exactly 4" in msg

def test_source_key_contamination_fails(valid_article, mock_research):
    valid_article.source_key = "different|key|here"
    errors = run_all_deterministic_validations(valid_article, mock_research)
    assert len(errors) > 0
    assert any("Source key mismatch" in e for e in errors)
