#!/usr/bin/env python3
"""
Quick script to fill the blocked videos table with sample data.
Run this to quickly populate the database for testing.
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from databases import database

def quick_fill():
    """Quickly fill the blocked videos table with sample data."""
    
    print("🚀 Quick Fill: Blocked Videos Database")
    print("=" * 40)
    
    # Sample data - realistic YouTube video IDs with durations
    sample_videos = [
        # Clickbait videos
        {"video_id": "dQw4w9WgXcQ", "duration": "PT3M34S"},  # Rick Roll
        {"video_id": "9bZkp7q19f0", "duration": "PT4M12S"},  # PSY - Gangnam Style
        {"video_id": "jNQXAC9IVRw", "duration": "PT19S"},    # Me at the zoo
        
        # Gaming content
        {"video_id": "gaming001abc", "duration": "PT45M30S"},
        {"video_id": "gaming002def", "duration": "PT38M20S"},
        {"video_id": "gaming003ghi", "duration": "PT52M15S"},
        
        # Compilation videos
        {"video_id": "comp001jkl", "duration": "PT25M45S"},
        {"video_id": "comp002mno", "duration": "PT18M30S"},
        {"video_id": "comp003pqr", "duration": "PT32M15S"},
        
        # Outrage/news content
        {"video_id": "news001stu", "duration": "PT7M20S"},
        {"video_id": "news002vwx", "duration": "PT11M45S"},
        {"video_id": "news003yza", "duration": "PT9M30S"},
        
        # Gambling content
        {"video_id": "gamb001bcd", "duration": "PT20M30S"},
        {"video_id": "gamb002efg", "duration": "PT28M15S"},
        
        # Scam content
        {"video_id": "scam001hij", "duration": "PT14M20S"},
        {"video_id": "scam002klm", "duration": "PT19M30S"},
        {"video_id": "scam003nop", "duration": "PT16M45S"},
        
        # Violent content
        {"video_id": "viol001qrs", "duration": "PT5M30S"},
        {"video_id": "viol002tuv", "duration": "PT8M15S"},
        
        # Pranks
        {"video_id": "prank001wxy", "duration": "PT10M20S"},
        {"video_id": "prank002zab", "duration": "PT7M45S"},
        
        # Longer content
        {"video_id": "long001cde", "duration": "PT1H23M45S"},
        {"video_id": "long002fgh", "duration": "PT2H15M30S"},
        {"video_id": "long003ijk", "duration": "PT1H45M20S"},
    ]
    
    # Initialize database
    print("📋 Initializing database...")
    # Database is auto-initialized when database module is imported
    
    # Clear existing data
    print("🧹 Clearing existing data...")
    existing = database.get_blocked_videos()
    for video in existing:
        database.delete_blocked_video(video['video_id'])
    print(f"   Cleared {len(existing)} existing videos")
    
    # Add sample videos
    print("📝 Adding sample videos...")
    for i, video in enumerate(sample_videos, 1):
        database.log_blocked_video(
            video_id=video['video_id'],
            duration=video['duration']
        )
        print(f"   {i:2d}. {video['video_id']} - {video['duration']}")
    
    # Show results
    print("\n📊 Results:")
    stats = database.get_blocked_videos_stats()
    print(f"   Total blocked videos: {stats['total_blocked']}")
    print(f"   Total duration blocked: {stats['total_duration_formatted']}")
    print(f"   Average per video: {stats['total_duration_hours'] / stats['total_blocked']:.3f} hours")
    
    # Show some examples
    print("\n📋 Sample blocked videos:")
    all_videos = database.get_blocked_videos(limit=10)
    for video in all_videos:
        hours = video['duration_hours']
        duration_str = f"{hours:.3f}h" if hours >= 1 else f"{hours*60:.1f}m"
        print(f"   {video['video_id']}: {duration_str}")
    
    print(f"\n✅ Successfully added {len(sample_videos)} blocked videos!")
    print("   You can now test the blocked videos functionality.")

if __name__ == "__main__":
    quick_fill()
