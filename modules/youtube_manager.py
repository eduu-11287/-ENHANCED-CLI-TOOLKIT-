"""
YouTube Playlist Generator Module
"""

import json
import os
import random
import time
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List

import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tqdm import tqdm

from modules.utils import CLIColors

@dataclass
class PlaylistConfig:
    num_videos: int = 50
    min_duration_seconds: int = 180
    max_duration_seconds: int = 3650
    min_view_count: int = 100
    exclude_keywords: List[str] = None
    include_keywords: List[str] = None
    days_back: int = 2000
    language_preference: str = "en"
    gmail_account: str = "bumble.11287@gmail.com"
    
    def __post_init__(self):
        if self.exclude_keywords is None:
            self.exclude_keywords = ["hindi", "bollywood", "tamil", "telugu", "punjabi", "bhojpuri"]
        if self.include_keywords is None:
            self.include_keywords = ["pop", "urban", "RnB", "mixes", "hiphop", "kenyan rnb", "Russian trap", "afrobeat", "afropop", "reggae", "kikuyu gospel"]

class YouTubeManager:
    def __init__(self, api_key: str, config: PlaylistConfig):
        self.api_key = api_key
        self.config = config
        self.youtube = build("youtube", "v3", developerKey=api_key)
        self.used_videos_file = "data/used_videos.json"
        self.favorites_file = "data/favorites.json"
        self.playlists_file = "data/saved_playlists.json"
        self.ensure_data_dir()
        
    def ensure_data_dir(self):
        """Create data directory if it doesn't exist."""
        os.makedirs("data", exist_ok=True)
    
    def parse_iso8601_duration(self, dur: str) -> int:
        """Convert ISO 8601 duration (PT#H#M#S) to seconds."""
        hours = minutes = seconds = 0
        dur = dur.strip("PT")
        num = ""
        for ch in dur:
            if ch.isdigit():
                num += ch
            else:
                if ch == "H":
                    hours = int(num) if num else 0
                elif ch == "M":
                    minutes = int(num) if num else 0
                elif ch == "S":
                    seconds = int(num) if num else 0
                num = ""
        return hours * 3600 + minutes * 60 + seconds

    def load_used_videos(self) -> Dict:
        """Load used videos with metadata."""
        if os.path.exists(self.used_videos_file):
            try:
                with open(self.used_videos_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}

    def save_used_videos(self, video_data: Dict):
        """Save used videos with metadata."""
        with open(self.used_videos_file, "w") as f:
            json.dump(video_data, f, indent=2)

    def get_trending_search_terms(self) -> List[str]:
        """Get trending music search terms."""
        base_terms = [
            "music", "songs", "playlist", "hits", "top songs", "popular music", 
            "pop music", "hip hop", "electronic music", "dance music",
            "r&b music", "country music", "indie music", "alternative music",
            "music 2024", "music 2023", "music 2022", "classic songs", "oldies",
            "remix", "cover songs", "performance"
        ]
        return base_terms

    def smart_search(self, max_results: int = 300) -> List[str]:
        """Enhanced search with multiple strategies."""
        all_video_ids = []
        search_terms = self.get_trending_search_terms()
        used_videos = self.load_used_videos()
        
        cutoff_date = datetime.now() - timedelta(days=self.config.days_back)
        
        with tqdm(total=max_results, desc="🔍 Searching videos") as pbar:
            for term in random.sample(search_terms, min(15, len(search_terms))):
                if len(all_video_ids) >= max_results:
                    break
                    
                try:
                    for order in ['relevance', 'viewCount', 'date', 'rating']:
                        if len(all_video_ids) >= max_results:
                            break
                            
                        response = self.youtube.search().list(
                            part="id,snippet",
                            q=term,
                            type="video",
                            videoCategoryId="10",
                            order=order,
                            publishedAfter=cutoff_date.isoformat() + "Z",
                            maxResults=50,
                            regionCode="US"
                        ).execute()
                        
                        for item in response.get("items", []):
                            if len(all_video_ids) >= max_results:
                                break
                                
                            video_id = item["id"]["videoId"]
                            if video_id not in used_videos and video_id not in all_video_ids:
                                title = item["snippet"]["title"].lower()
                                
                                if any(exc in title for exc in self.config.exclude_keywords):
                                    continue
                                
                                music_indicators = ["music", "song", "audio", "track", "hit", "mix", 
                                                  "official", "video", "cover", "remix", "live", "acoustic"]
                                if not (any(inc in title for inc in self.config.include_keywords) or 
                                       any(ind in title for ind in music_indicators)):
                                    continue
                                
                                all_video_ids.append(video_id)
                                pbar.update(1)
                                
                        time.sleep(0.1)
                        
                except HttpError as e:
                    print(f"❗ Search error for '{term}': {e}")
                    time.sleep(2)
                    continue
                    
        return all_video_ids

    def create_youtube_playlist_url(self, video_ids: List[str]) -> str:
        """Create a YouTube playlist URL."""
        if len(video_ids) == 0:
            return ""
        
        if len(video_ids) > 1:
            watch_videos_url = "https://www.youtube.com/watch_videos?video_ids=" + ",".join(video_ids)
            return watch_videos_url
        else:
            return f"https://www.youtube.com/watch?v={video_ids[0]}"

def handle_playlist_options(playlist_url: str):
    """Handle options after playlist generation"""
    print(f"\n{CLIColors.BLUE}What would you like to do with this playlist?{CLIColors.END}")
    
    options = {
        "1": "Open in Chrome browser",
        "2": "Send to default email (bumble.11287@gmail.com)",
        "3": "Display URL only",
        "4": "Back to YouTube menu"
    }
    
    for key, value in options.items():
        print(f"  {key}. {value}")
    
    choice = input(f"\n{CLIColors.BOLD}Choose option (1-4): {CLIColors.END}").strip()
    
    if choice == "1":
        try:
            webbrowser.get('chrome').open(playlist_url)
            print(f"{CLIColors.GREEN}✅ Playlist opened in Chrome{CLIColors.END}")
        except webbrowser.Error:
            # Fallback to default browser if Chrome not available
            webbrowser.open(playlist_url)
            print(f"{CLIColors.GREEN}✅ Playlist opened in default browser{CLIColors.END}")
    
    elif choice == "2":
        # This would require setting up email functionality
        print(f"{CLIColors.YELLOW}⚠️ Email functionality coming soon!{CLIColors.END}")
        print(f"{CLIColors.CYAN}Playlist URL: {playlist_url}{CLIColors.END}")
    
    elif choice == "3":
        print(f"\n{CLIColors.CYAN}🔗 Playlist URL: {playlist_url}{CLIColors.END}")
    
    elif choice == "4":
        return
    
    else:
        print(f"{CLIColors.RED}❌ Invalid option{CLIColors.END}")
1
def youtube_menu():
    """YouTube playlist generator menu"""
    print(f"\n{CLIColors.CYAN}🎵 YouTube Playlist Generator{CLIColors.END}")
    print("=" * 50)
    
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print(f"{CLIColors.RED}❗ Error: YOUTUBE_API_KEY not set in .env file{CLIColors.END}")
        print("Please add your YouTube API key to the .env file")
        return

    config = PlaylistConfig()
    manager = YouTubeManager(api_key, config)
    
    options = {
        "1": "Generate Smart Playlist",
        "2": "Create Themed Playlist", 
        "3": "View Saved Playlists",
        "4": "Clear Search History",
        "5": "Back to Main Menu"
    }
    
    for key, value in options.items():
        print(f"  {key}. {value}")
    
    choice = input(f"\n{CLIColors.BOLD}Choose option (1-5): {CLIColors.END}").strip()
    
    if choice == "1":
        print(f"\n{CLIColors.YELLOW}🔍 Generating smart playlist...{CLIColors.END}")
        video_ids = manager.smart_search(max_results=config.num_videos * 4)
        
        if len(video_ids) >= 10:
            selected = video_ids[:config.num_videos]
            playlist_url = manager.create_youtube_playlist_url(selected)
            
            print(f"\n{CLIColors.GREEN}✅ Playlist created with {len(selected)} videos!{CLIColors.END}")
            print(f"{CLIColors.CYAN}🔗 URL: {playlist_url}{CLIColors.END}")
            
            # Update used videos
            used_videos = manager.load_used_videos()
            for vid_id in selected:
                used_videos[vid_id] = {
                    "used_at": datetime.now().isoformat(),
                    "playlist_type": "smart"
                }
            manager.save_used_videos(used_videos)
            
            # Ask user what to do with the playlist
            handle_playlist_options(playlist_url)
        else:
            print(f"{CLIColors.RED}❌ Only found {len(video_ids)} videos, too few for a playlist{CLIColors.END}")
    
    elif choice == "5":
        return
    else:
        print(f"{CLIColors.YELLOW}⚠️ Feature coming soon!{CLIColors.END}")