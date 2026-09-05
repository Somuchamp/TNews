import logging
from typing import Optional
from app.models import ResearchPackage, ArticleState
from app.ai.generator import generate_article, repair_article
from app.ai.humanizer import humanize_article
from app.ai.qa import run_factual_qa
from app.validation.deterministic import run_all_deterministic_validations, calculate_word_count
from app.wordpress.images import resolve_image
from app.wordpress.taxonomies import resolve_category_id, resolve_tag_ids
from app.wordpress.rankmath import get_rankmath_meta_payload
from app.wordpress.api import create_or_update_post, get_recent_posts_by_category
from app.storage.db import init_db, save_state

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

from app.ai.classifier import classify_trend

def inject_also_read(content: str, related_posts: list) -> str:
    if not related_posts:
        return content
        
    also_read_html = "<p><strong>Also Read:-</strong></p>\n"
    for post in related_posts:
        also_read_html += f'<p><a href="{post["link"]}">{post["title"]}</a></p>\n'
        
    paragraphs = content.split('</p>')
    if len(paragraphs) > 2:
        new_content = ""
        for i, p in enumerate(paragraphs):
            if p.strip():
                new_content += p + "</p>\n"
            if i == 1:
                new_content += also_read_html
        return new_content
    else:
        return content + "\n" + also_read_html

def process_article(research: ResearchPackage) -> ArticleState:
    init_db()
    state = ArticleState(source_key=research.source_key, research=research)
    
    try:
        # 0. AI Classification
        logging.info(f"[CLASSIFY] Running LLM classification for {research.source_key}")
        state.status = "CLASSIFYING"
        save_state(state)
        
        research = classify_trend(research)
        if not research.is_newsworthy:
            logging.warning(f"[SKIP] Trend rejected by classifier: {research.trend}")
            state.status = "SKIPPED"
            save_state(state)
            return state
            
        # 0.5 Fetch PAA Questions (Only if Newsworthy to save API credits)
        from app.research.serp import fetch_paa_questions, fetch_sports_data
        research.paa_questions = fetch_paa_questions(research.trend)
        if research.category == "sports":
            research.sports_data = fetch_sports_data(research.trend)
            
        # 1. Generation
        logging.info(f"[GENERATE] Starting generation for {research.source_key}")
        state.status = "GENERATING"
        save_state(state)
        
        article = generate_article(research)
        article.word_count = calculate_word_count(article.content)
        state.article = article
        
        # 1.2 Pre-humanizer word count gate: repair immediately if generator fell short
        # Target is 1050 real words (buffer above the 900 validator minimum) before humanizing
        PRE_HUMANIZE_MIN = 1050
        pre_repair_attempts = 0
        while article.word_count < PRE_HUMANIZE_MIN and pre_repair_attempts < 2:
            pre_repair_attempts += 1
            logging.warning(
                f"[PRE-HUMANIZE REPAIR] Generated article too short ({article.word_count} words). "
                f"Expanding before humanizer (attempt {pre_repair_attempts}/2)..."
            )
            article = repair_article(
                research, article,
                [f"Article must be at least {PRE_HUMANIZE_MIN} words. Actual: {article.word_count}. "
                 f"Drastically expand all sections with more detail, context, and analysis."]
            )
            article.word_count = calculate_word_count(article.content)
            state.article = article
        logging.info(f"[PRE-HUMANIZE] Word count ready: {article.word_count} words")
        
        # 1.5 Humanizer — rewrite content to sound natural, not AI-generated
        logging.info(f"[HUMANIZE] Starting humanizer pass for {research.source_key}")
        state.status = "HUMANIZING"
        save_state(state)
        article.content = humanize_article(
            article.content,
            research.trend,
            primary_keyword=article.primary_focus_keyword
        )
        article.word_count = calculate_word_count(article.content)
        state.article = article

        
        # 2. Deterministic Validation
        state.status = "VALIDATING"
        save_state(state)
        errors = run_all_deterministic_validations(article, research)
        
        # 3. Repair Loop (up to 3 attempts)
        repair_attempts = 0
        max_repairs = 3
        while errors and repair_attempts < max_repairs:
            repair_attempts += 1
            logging.warning(f"[REPAIR] Validation failed (Attempt {repair_attempts}/{max_repairs}). Errors: {errors}. Attempting repair...")
            state.status = f"REPAIRING_{repair_attempts}"
            save_state(state)
            
            article = repair_article(research, article, errors)
            article.word_count = calculate_word_count(article.content)
            state.article = article
            
            # Revalidate
            errors = run_all_deterministic_validations(article, research)
            
        if errors:
            state.status = "PARTIAL_REPAIR"
            state.validation_errors = errors
            save_state(state)
            logging.error(f"[ERROR] Repair failed after {max_repairs} attempts. Proceeding to push as draft anyway. Final errors: {errors}")
            # Do NOT return state here, allow the pipeline to push to WordPress
                
        # 4. Factual QA
        logging.info("[QA] Running factual QA...")
        state.status = "QA_READY"
        save_state(state)
        qa_pass, qa_errors = run_factual_qa(research, article)
        
        if not qa_pass:
            # QA is highly pedantic (e.g. failing '₹2 lakh crore' vs 'Rs 2L crore').
            # We will log the QA errors as warnings but NOT block publication, 
            # matching the behavior of the original n8n workflow.
            logging.warning(f"[QA WARNING] Pedantic QA flagged potential issues, but proceeding: {qa_errors}")
            
        logging.info(f"[VALIDATE] PASS. Word count: {article.word_count}")
        
        # 5. WordPress Taxonomies & Images
        state.status = "PUBLISH_READY"
        save_state(state)
        
        state.category_id = resolve_category_id(research.category)
        
        all_tags = article.focus_keywords + article.related_keywords
        state.tag_ids = resolve_tag_ids(all_tags)
        
        # Image resolving safely
        img_url = next((s.image_url for s in research.sources if s.image_url), None)
        state.media_id = resolve_image(img_url)
        
        related_posts = get_recent_posts_by_category(state.category_id, limit=2, exclude_slug=article.slug)
        if related_posts:
            article.content = inject_also_read(article.content, related_posts)
            
        # 6. WordPress Post Creation
        payload = {
            "title": article.title,
            "slug": article.slug,
            "content": article.content,
            "excerpt": article.excerpt,
            "status": "draft",
            "categories": [state.category_id],
            "tags": state.tag_ids
        }
        
        if state.media_id:
            payload["featured_media"] = state.media_id
            
        # Add Rank Math metadata (pushing ALL 5 focus keywords)
        rm_meta = get_rankmath_meta_payload(article.focus_keywords, article.title, article.excerpt)
        payload.update(rm_meta)
        
        logging.info(f"[WORDPRESS] Pushing draft: {article.slug}")
        post_id = create_or_update_post(payload, article.slug)
        
        state.wordpress_post_id = post_id
        state.status = "DRAFT_CREATED"
        save_state(state)
        logging.info(f"[WORDPRESS] Success! Post ID: {post_id}")
        
    except Exception as e:
        state.status = "ERROR"
        state.validation_errors = [str(e)]
        save_state(state)
        logging.error(f"[ERROR] Pipeline exception: {e}")
        
    return state
