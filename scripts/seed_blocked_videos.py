#!/usr/bin/env python3
"""
Script to seed the blocked videos database with sample data.
This simulates real-world blocked content across different categories.
"""

import sys
import os
import random
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from databases import database

# Sample video data representing different blocked categories
SAMPLE_BLOCKED_VIDEOS = [
    # Clickbait / Curiosity Traps
    {"video_id": "clickbait_001", "duration": "PT8M45S", "category": "Clickbait / Curiosity Traps"},
    {"video_id": "clickbait_002", "duration": "PT12M30S", "category": "Clickbait / Curiosity Traps"},
    {"video_id": "clickbait_003", "duration": "PT6M15S", "category": "Clickbait / Curiosity Traps"},
    {"video_id": "clickbait_004", "duration": "PT15M20S", "category": "Clickbait / Curiosity Traps"},
    {"video_id": "clickbait_005", "duration": "PT9M10S", "category": "Clickbait / Curiosity Traps"},
    
    # Internet Clip Compilations
    {"video_id": "compilation_001", "duration": "PT25M45S", "category": "Internet Clip Compilations"},
    {"video_id": "compilation_002", "duration": "PT18M30S", "category": "Internet Clip Compilations"},
    {"video_id": "compilation_003", "duration": "PT32M15S", "category": "Internet Clip Compilations"},
    {"video_id": "compilation_004", "duration": "PT22M40S", "category": "Internet Clip Compilations"},
    
    # Sensational / Outrage News
    {"video_id": "outrage_001", "duration": "PT7M20S", "category": "Sensational / Outrage News"},
    {"video_id": "outrage_002", "duration": "PT11M45S", "category": "Sensational / Outrage News"},
    {"video_id": "outrage_003", "duration": "PT9M30S", "category": "Sensational / Outrage News"},
    {"video_id": "outrage_004", "duration": "PT13M15S", "category": "Sensational / Outrage News"},
    
    # Gaming – High-Arousal/Competitive
    {"video_id": "gaming_001", "duration": "PT45M30S", "category": "Gaming – High-Arousal/Competitive"},
    {"video_id": "gaming_002", "duration": "PT38M20S", "category": "Gaming – High-Arousal/Competitive"},
    {"video_id": "gaming_003", "duration": "PT52M15S", "category": "Gaming – High-Arousal/Competitive"},
    {"video_id": "gaming_004", "duration": "PT41M45S", "category": "Gaming – High-Arousal/Competitive"},
    
    # Gambling & Betting
    {"video_id": "gambling_001", "duration": "PT20M30S", "category": "Gambling & Betting"},
    {"video_id": "gambling_002", "duration": "PT28M15S", "category": "Gambling & Betting"},
    {"video_id": "gambling_003", "duration": "PT35M45S", "category": "Gambling & Betting"},
    
    # Scams & Get-Rich-Quick
    {"video_id": "scam_001", "duration": "PT14M20S", "category": "Scams & Get-Rich-Quick"},
    {"video_id": "scam_002", "duration": "PT19M30S", "category": "Scams & Get-Rich-Quick"},
    {"video_id": "scam_003", "duration": "PT16M45S", "category": "Scams & Get-Rich-Quick"},
    {"video_id": "scam_004", "duration": "PT22M10S", "category": "Scams & Get-Rich-Quick"},
    
    # Violent / Graphic
    {"video_id": "violent_001", "duration": "PT5M30S", "category": "Violent / Graphic"},
    {"video_id": "violent_002", "duration": "PT8M15S", "category": "Violent / Graphic"},
    {"video_id": "violent_003", "duration": "PT6M45S", "category": "Violent / Graphic"},
    
    # Pranks & Dangerous Challenges
    {"video_id": "prank_001", "duration": "PT10M20S", "category": "Pranks & Dangerous Challenges"},
    {"video_id": "prank_002", "duration": "PT7M45S", "category": "Pranks & Dangerous Challenges"},
    {"video_id": "prank_003", "duration": "PT12M30S", "category": "Pranks & Dangerous Challenges"},
    
    # Sexual / Suggestive
    {"video_id": "suggestive_001", "duration": "PT6M15S", "category": "Sexual / Suggestive"},
    {"video_id": "suggestive_002", "duration": "PT8M30S", "category": "Sexual / Suggestive"},
    
    # Conspiracy & Fringe Claims
    {"video_id": "conspiracy_001", "duration": "PT23M45S", "category": "Conspiracy & Fringe Claims"},
    {"video_id": "conspiracy_002", "duration": "PT31M20S", "category": "Conspiracy & Fringe Claims"},
    {"video_id": "conspiracy_003", "duration": "PT18M15S", "category": "Conspiracy & Fringe Claims"},
    
    # True Crime & Investigations
    {"video_id": "crime_001", "duration": "PT42M30S", "category": "True Crime & Investigations"},
    {"video_id": "crime_002", "duration": "PT38M45S", "category": "True Crime & Investigations"},
    {"video_id": "crime_003", "duration": "PT35M20S", "category": "True Crime & Investigations"},
    
    # Politics & Public Affairs
    {"video_id": "politics_001", "duration": "PT15M30S", "category": "Politics & Public Affairs"},
    {"video_id": "politics_002", "duration": "PT22M15S", "category": "Politics & Public Affairs"},
    {"video_id": "politics_003", "duration": "PT19M45S", "category": "Politics & Public Affairs"},
]

def generate_realistic_video_ids():
    """Generate realistic YouTube video IDs."""
    # YouTube video IDs are 11 characters long
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    return ''.join(random.choice(chars) for _ in range(11))

def seed_blocked_videos():
    """Seed the blocked videos database with sample data."""
    
    print("🌱 Seeding Blocked Videos Database")
    print("=" * 50)
    
    # Initialize database
    print("📋 Initializing database...")
    # Database is auto-initialized when database module is imported
    
    # Clear existing data (optional - comment out if you want to keep existing data)
    print("🧹 Clearing existing blocked videos...")
    existing_videos = database.get_blocked_videos()
    for video in existing_videos:
        database.delete_blocked_video(video['video_id'])
    print(f"   ✅ Cleared {len(existing_videos)} existing videos")
    
    print()
    
    # Add sample blocked videos
    print("📝 Adding sample blocked videos...")
    added_count = 0
    
    for video_data in SAMPLE_BLOCKED_VIDEOS:
        # Generate a realistic video ID if not provided
        video_id = video_data.get('video_id') or generate_realistic_video_ids()
        
        # Log the blocked video
        database.log_blocked_video(
            video_id=video_id,
            duration=video_data.get('duration'),
            duration_seconds=video_data.get('duration_seconds'),
            duration_hours=video_data.get('duration_hours')
        )
        
        added_count += 1
        print(f"   ✅ Added: {video_id} ({video_data.get('category', 'Unknown')}) - {video_data.get('duration', 'Unknown duration')}")
    
    print()
    
    # Display statistics
    print("📊 Database Statistics:")
    stats = database.get_blocked_videos_stats()
    print(f"   Total blocked videos: {stats['total_blocked']}")
    print(f"   Total duration blocked: {stats['total_duration_formatted']}")
    print(f"   Average duration per video: {stats['total_duration_hours'] / stats['total_blocked']:.3f} hours")
    
    print()
    
    # Show category breakdown
    print("📈 Category Breakdown:")
    category_counts = {}
    for video_data in SAMPLE_BLOCKED_VIDEOS:
        category = video_data.get('category', 'Unknown')
        category_counts[category] = category_counts.get(category, 0) + 1
    
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   {category}: {count} videos")
    
    print()
    
    # Test API endpoints
    print("🌐 Testing API endpoints...")
    try:
        import requests
        
        # Test getting all videos
        response = requests.get('http://127.0.0.1:5050/api/blocked-videos/')
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ GET /api/blocked-videos/: {data['count']} videos")
        else:
            print(f"   ❌ GET /api/blocked-videos/: HTTP {response.status_code}")
        
        # Test getting stats
        response = requests.get('http://127.0.0.1:5050/api/blocked-videos/stats')
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ GET /api/blocked-videos/stats: {data['stats']['total_duration_formatted']}")
        else:
            print(f"   ❌ GET /api/blocked-videos/stats: HTTP {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("   ⚠️  Server not running - API tests skipped")
    except ImportError:
        print("   ⚠️  requests library not available - API tests skipped")
    
    print()
    print("✅ Seeding completed successfully!")
    print(f"   Added {added_count} blocked videos to the database")
    print("   You can now test the blocked videos functionality")

def add_random_blocked_videos(count=10):
    """Add random blocked videos for testing."""
    
    print(f"🎲 Adding {count} random blocked videos...")
    
    # Sample durations in YouTube format
    durations = [
        "PT30S", "PT1M", "PT2M30S", "PT5M", "PT8M45S", 
        "PT12M", "PT15M30S", "PT20M", "PT25M45S", "PT30M",
        "PT45M", "PT1H", "PT1H15M", "PT1H30M", "PT2H"
    ]
    
    # Sample categories
    categories = [
        "Clickbait / Curiosity Traps",
        "Internet Clip Compilations", 
        "Sensational / Outrage News",
        "Gaming – High-Arousal/Competitive",
        "Gambling & Betting",
        "Scams & Get-Rich-Quick",
        "Violent / Graphic",
        "Pranks & Dangerous Challenges"
    ]
    
    for i in range(count):
        video_id = generate_realistic_video_ids()
        duration = random.choice(durations)
        category = random.choice(categories)
        
        database.log_blocked_video(
            video_id=video_id,
            duration=duration
        )
        
        print(f"   ✅ Added random video: {video_id} ({category}) - {duration}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed blocked videos database")
    parser.add_argument("--random", type=int, help="Add N random blocked videos")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")
    
    args = parser.parse_args()
    
    if args.random:
        add_random_blocked_videos(args.random)
    else:
        seed_blocked_videos()
