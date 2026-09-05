import argparse
import json
import sys
from dataclasses import dataclass
from app.models import ResearchPackage, ResearchSource
from app.pipeline import process_article

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def run_sample():
    # A mock sample to run the pipeline manually
    research = ResearchPackage(
        trend="Artificial Intelligence",
        trend_breakdown=["AI developments", "Artificial Intelligence news", "AI in healthcare", "AI tools", "Artificial Intelligence stocks"],
        published_at="2026-08-28T00:00:00Z",
        category="Technology",
        sources=[
            ResearchSource(
                title="New AI Model Released",
                description="A new artificial intelligence model has been released showing unprecedented reasoning capabilities in medical diagnostics.",
                url="https://example.com/ai-news",
                image_url=None
            )
        ]
    )
    print("Running pipeline for sample trend...")
    state = process_article(research)
    print(f"Pipeline finished with status: {state.status}")
    if state.validation_errors:
        print(f"Errors: {state.validation_errors}")

def run_live(limit: int = 5):
    from app.research.collector import fetch_live_trends
    packages = fetch_live_trends(geo="IN", hours=4, limit=100)
    
    # Optional: Sort by volume or similar logic before truncating, if desired
    # For now, just take the top 'limit' items that the API returned
    packages = packages[:limit]
    
    print(f"Found {len(packages)} live trends to process.")
    
    for i, research in enumerate(packages):
        print(f"\n--- Processing Live Trend {i+1}/{len(packages)}: {research.trend} ---")
        state = process_article(research)
        print(f"Finished {research.trend} with status: {state.status}")
        if state.validation_errors:
            print(f"Errors: {state.validation_errors}")

def run_from_file(filepath: str):
    from app.research.collector import parse_trends_json
    print(f"Parsing trends from {filepath}...")
    packages = parse_trends_json(filepath)
    print(f"Found {len(packages)} trends to process.")
    
    for i, research in enumerate(packages):
        print(f"\n--- Processing Trend {i+1}/{len(packages)}: {research.trend} ---")
        state = process_article(research)
        print(f"Finished {research.trend} with status: {state.status}")
        if state.validation_errors:
            print(f"Errors: {state.validation_errors}")

def run_upcoming_matches():
    from app.research.cricbuzz import fetch_upcoming_matches
    packages = fetch_upcoming_matches(days_ahead=7)
    
    print(f"Found {len(packages)} upcoming matches to process.")
    
    for i, research in enumerate(packages):
        print(f"\n--- Processing Upcoming Match {i+1}/{len(packages)}: {research.trend} ---")
        state = process_article(research)
        print(f"Finished {research.trend} with status: {state.status}")
        if state.validation_errors:
            print(f"Errors: {state.validation_errors}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TraceNews Automated Publishing Pipeline")
    parser.add_argument("--sample", action="store_true", help="Run with a hardcoded sample payload.")
    parser.add_argument("--trends-file", type=str, help="Path to a Google Trends JSON file to parse and execute.")
    parser.add_argument("--live", action="store_true", help="Fetch live trends from the Vercel API and process the top 5.")
    parser.add_argument("--upcoming-matches", action="store_true", help="Fetch and process upcoming international cricket matches from Cricbuzz.")
    
    args = parser.parse_args()
    
    if args.live:
        run_live(limit=5)
    elif args.trends_file:
        run_from_file(args.trends_file)
    elif args.upcoming_matches:
        run_upcoming_matches()
    elif args.sample:
        run_sample()
    else:
        print("Please provide an input method (e.g. --live, --upcoming-matches, or --trends-file).")
