def get_rankmath_meta_payload(focus_keywords: list, seo_title: str, excerpt: str) -> dict:
    """
    Constructs the exact meta payload for Rank Math via WP REST API.
    Rank Math PRO supports up to 5 focus keywords separated by commas.
    """
    joined_keywords = ", ".join(focus_keywords)
    
    return {
        "meta": {
            "rank_math_focus_keyword": joined_keywords,
            "rank_math_title": seo_title,
            "rank_math_description": excerpt
        }
    }
