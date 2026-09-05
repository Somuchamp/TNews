import logging
import re
from bs4 import BeautifulSoup
from openai import OpenAI
from app.config import config

client = OpenAI(api_key=config.OPENAI_API_KEY, timeout=120.0)


def _count_text_words(html_content: str) -> int:
    """Count actual text words after stripping HTML — identical to the validator."""
    soup = BeautifulSoup(html_content, "html.parser")
    # Remove FAQ section so count matches what the validator sees
    faq_headings = soup.find_all(
        lambda tag: tag.name in ['h2', 'h3']
        and ('faq' in tag.get_text().lower() or 'frequently asked questions' in tag.get_text().lower())
    )
    if faq_headings:
        for sibling in faq_headings[0].find_next_siblings():
            sibling.extract()
        faq_headings[0].extract()
    text = soup.get_text(separator=" ")
    text = re.sub(r'\s+', ' ', text).strip()
    return len(text.split(' ')) if text else 0

HUMANIZER_SYSTEM_PROMPT = """You are a professional human editor rewriting AI-generated news articles to pass AI-detection tools (targeting under 20% AI score on tools like QuillBot, GPTZero, and Copyleaks).
CRITICAL — WORD COUNT: Your output MUST match or EXCEED the word count of the input. Do NOT shorten, cut, or summarize. Expand where needed to maintain length.
TECHNIQUES TO SOUND HUMAN (apply all of these):
1. BURSTINESS — This is the #1 AI-detector signal. Vary sentence length dramatically within every paragraph:
   - Drop in short sentences. Like this. Two, three words max.
   - Then follow with a much longer sentence that builds context, adds nuance, and explains the background in a way that flows naturally from the previous short one.
   - Never write three sentences of similar length back to back.
2. CONTRACTIONS — Use them naturally: "it's", "that's", "there's", "you'd", "they're", "won't", "didn't", "isn't". AI almost never uses contractions; humans always do.
3. EM-DASHES & PARENTHETICALS — Use em-dashes for asides: "The event — which drew thousands — was unlike anything seen before." Use parenthetical remarks: "The match (played in sweltering heat) ended in a draw."
4. RHETORICAL QUESTIONS — Drop one into each section: "Why does this matter?", "What does that really mean?", "And who benefits from this?"
5. INFORMAL OPENERS — Start some sentences/paragraphs with: "And", "But", "So", "Now", "Look,", "Here's the thing —", "That's not all." These are natural in spoken English but AI avoids them.
6. IMPERFECT RHYTHM — Occasionally start a sentence, then pivot mid-thought with a dash or comma. Real writers do this.
7. FORBIDDEN WORDS — Never use: delve, testament, furthermore, in conclusion, it is worth noting, it's important to note, seamlessly, robust, leverage, game-changer, transformative, paradigm, utilize, comprehensive, multifaceted, groundbreaking, cutting-edge, rest assured, at the end of the day, in a nutshell, having said that, with that being said, notably, significantly (as a filler), it goes without saying.
8. VARIED PARAGRAPH OPENERS — Never start two consecutive paragraphs with the same word. Never start three in a row with "The", "This", or "It".
9. ACTIVE VOICE — Write what people DID, not what "was done". Passive voice occasionally for rhythm, not as default.
10. PRESERVE EVERYTHING — All HTML tags (<p>, <h2>, <h3>, <strong>, <table>, <thead>, <tbody>, <tr>, <th>, <td> with all inline styles), ALL factual data (names, dates, numbers, statistics), ALL SEO keywords, the FAQ section, and all tables. Do NOT change any facts.
11. HEADINGS ARE SACRED — Do NOT rewrite, rephrase, or alter the text inside any <h2> or <h3> tag. These headings are carefully crafted to contain SEO focus keywords and must remain exactly as they are. Only rewrite the <p> paragraph content around them.
12. KEYWORD CONTINUITY — If a focus keyword appears in a <h2>/<h3>, make sure it naturally appears at least once in the <p> paragraph immediately following that heading.
13. PRIMARY KEYWORD FREQUENCY — You will be given the primary focus keyword. This exact phrase MUST appear at least 4 times in the rewritten paragraph text. Count your uses. If you've only used it 2 or 3 times, go back and weave it in one more time naturally.
14. OUTPUT FORMAT — Return ONLY the rewritten HTML. No explanation, no JSON, no markdown fences. Just raw HTML starting from the first tag.
"""


def humanize_article(html_content: str, topic: str, primary_keyword: str = "") -> str:
    """
    Post-processes AI-generated HTML article content to sound human-written.
    Targets ~20% AI detection score by applying burstiness, contractions,
    em-dashes, rhetorical questions, and varied sentence structure,
    while preserving all factual data, HTML tags, SEO keywords, and tables.

    Args:
        html_content: The raw HTML string of the article body.
        topic: The article topic/trend for context.
        primary_keyword: The primary SEO focus keyword that must appear 4+ times.

    Returns:
        The humanized HTML content string (same or greater text word count than input).
    """
    logging.info("[HUMANIZE] Rewriting article content to sound human-written...")

    # Use the same HTML-stripping logic as the validator for accurate count
    input_word_count = _count_text_words(html_content)
    logging.info(f"[HUMANIZE] Input text word count (excl. FAQs): {input_word_count}")

    keyword_instruction = (
        f'PRIMARY KEYWORD TO PRESERVE: "{primary_keyword}" — this exact phrase MUST appear '
        f"at least 4 times in the rewritten paragraph text. Count carefully.\n\n"
        if primary_keyword else ""
    )

    user_message = (
        f'Rewrite the following HTML article about "{topic}" to score under 20% on AI detection tools.\n\n'
        f"CRITICAL WORD COUNT: The article body (excluding FAQs) currently has {input_word_count} real text words. "
        f"Your output body (excluding FAQs) MUST have AT LEAST {input_word_count} text words. "
        f"DO NOT cut or shorten — expand paragraphs if needed to maintain or exceed this count.\n\n"
        f"{keyword_instruction}"
        f"Apply ALL techniques from your system instructions: burstiness, contractions, em-dashes, "
        f"rhetorical questions, informal openers, varied paragraph starts.\n\n"
        f"HEADINGS: Do NOT touch or rewrite any <h2> or <h3> text — leave them exactly as they are. "
        f"They carry embedded SEO focus keywords that must be preserved.\n\n"
        f"Preserve every HTML tag, all factual data, all SEO keywords, tables, and the FAQ section.\n\n"
        f"ARTICLE HTML:\n{html_content}"
    )

    try:
        logging.info(f"[HUMANIZE] Using model: {config.HUMANIZER_MODEL}")
        response = client.chat.completions.create(
            model=config.HUMANIZER_MODEL,
            messages=[
                {"role": "system", "content": HUMANIZER_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.9,   # Higher = more natural, varied phrasing
            max_tokens=5000
        )

        humanized = response.choices[0].message.content.strip()

        # Strip any accidental markdown fences the LLM may have added
        if humanized.startswith("```"):
            humanized = re.sub(r'^```[a-z]*\n?', '', humanized)
            humanized = re.sub(r'\n?```$', '', humanized)

        # Strip forbidden HTML tags the LLM may have introduced
        # <br> is not in the allowed tag list and will fail validation
        humanized = re.sub(r'<br\s*/?>', ' ', humanized)
        humanized = re.sub(r'</?(?:ul|ol|li|div|span|em|i|b|blockquote|hr)[^>]*>', '', humanized)
        humanized = re.sub(r'\s+', ' ', humanized)  # Clean up extra spaces

        output_word_count = _count_text_words(humanized)

        # Safety check: if real text word count dropped more than 15%, fall back
        if not humanized or output_word_count < input_word_count * 0.85:
            logging.warning(
                f"[HUMANIZE] Text word count too low ({output_word_count} vs {input_word_count} input) "
                f"— falling back to original content."
            )
            return html_content

        # Keyword re-injection: if primary keyword appears fewer than 4 times, inject it
        if primary_keyword:
            kw_lower = primary_keyword.lower()
            soup_check = BeautifulSoup(humanized, "html.parser")
            full_text = soup_check.get_text(separator=" ").lower()
            kw_count = full_text.count(kw_lower)
            if kw_count < 4:
                needed = 4 - kw_count
                logging.warning(f"[HUMANIZE] Keyword '{primary_keyword}' only appears {kw_count}x. Injecting {needed} more...")
                # Find <p> tags and inject the keyword into their text naturally
                paragraphs = soup_check.find_all('p')
                injected = 0
                for p in paragraphs[1:]:  # Skip first paragraph (already has keyword)
                    if injected >= needed:
                        break
                    p_text = p.get_text()
                    if kw_lower not in p_text.lower() and len(p_text) > 80:
                        # Wrap first mention in strong for SEO
                        new_text = p_text.rstrip('.')
                        p.string = f"{new_text}, a development closely tied to {primary_keyword}."
                        injected += 1
                humanized = str(soup_check)
                logging.info(f"[HUMANIZE] Injected keyword {injected} time(s). Total now: {kw_count + injected}")

        logging.info(f"[HUMANIZE] Done. Text words (excl. FAQs): {input_word_count} → {output_word_count}")
        return humanized

    except Exception as e:
        logging.error(f"[HUMANIZE] Failed with exception: {e}. Using original content.")
        return html_content
