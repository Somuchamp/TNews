import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")       # Generator model (cheap + fast)
    HUMANIZER_MODEL = os.getenv("HUMANIZER_MODEL", "gpt-4o")      # Humanizer model (higher quality)
    VALUESERP_API_KEY = os.getenv("VALUESERP_API_KEY")
    
    WP_BASE_URL = os.getenv("WP_BASE_URL")
    WP_USERNAME = os.getenv("WP_USERNAME")
    WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

    # App settings
    MIN_WORD_COUNT = 900

config = Config()
