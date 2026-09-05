import sqlite3
import json
from app.models import ArticleState
from dataclasses import asdict

DB_PATH = "tracenews_audit.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            source_key TEXT PRIMARY KEY,
            status TEXT,
            trend TEXT,
            slug TEXT,
            word_count INTEGER,
            wordpress_post_id INTEGER,
            validation_errors TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_state(state: ArticleState):
    """Persists or updates the article state in SQLite."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    trend = state.research.trend
    slug = state.article.slug if state.article else None
    word_count = state.article.word_count if state.article else 0
    wp_id = state.wordpress_post_id
    errors = json.dumps(state.validation_errors)
    
    c.execute('''
        INSERT INTO audit_log (source_key, status, trend, slug, word_count, wordpress_post_id, validation_errors)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_key) DO UPDATE SET
            status=excluded.status,
            slug=excluded.slug,
            word_count=excluded.word_count,
            wordpress_post_id=excluded.wordpress_post_id,
            validation_errors=excluded.validation_errors,
            updated_at=CURRENT_TIMESTAMP
    ''', (state.source_key, state.status, trend, slug, word_count, wp_id, errors))
    
    conn.commit()
    conn.close()
