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
from typing import Dict, List, Optional

import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tqdm import tqdm

from modules.utils import CLIColors
from modules.quota_tracker import QuotaTracker

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
    chrome_path: str = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"  # Windows Chrome path through WSL
    saved_playlists_file: str = "data/saved_playlists.json"
    
    def __post_init__(self):
        if self.exclude_keywords is None:
            self.exclude_keywords = ["hindi", "bollywood", "tamil", "telugu", "punjabi", "bhojpuri"]
        if self.include_keywords is None:
            self.include_keywords = ["pop", "urban", "RnB", "mixes", "hiphop", "kenyan rnb", "Russian trap", "afrobeat", "afropop", "reggae", "kikuyu gospel"]

class YouTubeManager:
    def __init__(self, api_key: str, config: PlaylistConfig):
        self.api_keys = self._load_api_keys(api_key)  # Convert single key to list and load additional keys
        self.current_key_index = 0
        self.config = config
        self.youtube = self._build_youtube_client()
        self.used_videos_file = "data/used_videos.json"
        self.favorites_file = "data/favorites.json"
        self.playlists_file = "data/saved_playlists.json"
        self.cache_file = "data/youtube_cache.json"
        self.api_keys_file = "data/api_keys.json"
        self.cache_duration = 24 * 60 * 60  # 24 hours in seconds
        self.quota_tracker = QuotaTracker()  # Initialize quota tracking
        self.ensure_data_dir()
        self.load_cache()
        
    def _load_api_keys(self, initial_key: str) -> list:
        """Load API keys from file or initialize with single key."""
        try:
            if os.path.exists(self.api_keys_file):
                with open(self.api_keys_file, 'r') as f:
                    keys = json.load(f)
                if initial_key not in keys:
                    keys.append(initial_key)
                return keys
        except Exception:
            pass
        return [initial_key]
        
    def _build_youtube_client(self):
        """Build YouTube client with current API key."""
        return build("youtube", "v3", developerKey=self.api_keys[self.current_key_index])
        
    def rotate_api_key(self):
        """Rotate to next working API key with sufficient quota."""
        if len(self.api_keys) <= 1:
            return False

        original_index = self.current_key_index
        working_key_found = False
        keys_tried = set()

        # Try each key until we find one that works
        while len(keys_tried) < len(self.api_keys):
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            current_key = self.api_keys[self.current_key_index]
            
            if current_key in keys_tried:
                continue
                
            keys_tried.add(current_key)
            self.youtube = self._build_youtube_client()
            
            try:
                print(f"{CLIColors.CYAN}🔍 Testing API key {len(keys_tried)}/{len(self.api_keys)}...{CLIColors.END}")
                
                # Test the key with a minimal request
                response = self.youtube.search().list(
                    part="snippet",
                    maxResults=1,
                    type="video"
                ).execute()
                
                working_key_found = True
                print(f"{CLIColors.GREEN}✅ Found working API key with available quota{CLIColors.END}")
                
                # Save any changes to API keys
                with open(self.api_keys_file, 'w') as f:
                    json.dump(self.api_keys, f, indent=2)
                    
                return True
                
            except HttpError as e:
                error_str = str(e)
                if "quota" in error_str.lower():
                    print(f"{CLIColors.YELLOW}⚠️ API key has exceeded its quota{CLIColors.END}")
                    continue
                elif "invalid" in error_str.lower():
                    print(f"{CLIColors.YELLOW}⚠️ Removing invalid API key{CLIColors.END}")
                    self.api_keys.pop(self.current_key_index)
                    if len(self.api_keys) == 0:
                        print(f"{CLIColors.RED}❌ No valid API keys remaining{CLIColors.END}")
                        return False
                    # Adjust current_key_index since we removed a key
                    self.current_key_index = self.current_key_index % len(self.api_keys)
                    continue
                else:
                    print(f"{CLIColors.RED}❌ API error: {error_str}{CLIColors.END}")
                    continue
            except Exception as e:
                print(f"{CLIColors.RED}❌ Error testing API key: {str(e)}{CLIColors.END}")
                continue

        # If we get here, no working keys were found
        if not working_key_found:
            self.current_key_index = original_index
            self.youtube = self._build_youtube_client()
            print(f"{CLIColors.RED}❌ No API keys with available quota found{CLIColors.END}")
            return False

        return working_key_found
        
    def test_api_key(self, api_key: str) -> bool:
        """Test if an API key is valid and has available quota."""
        try:
            # Check quota status first
            quota_status = self.quota_tracker.get_quota_status(api_key)
            if quota_status["remaining_today"] < 100:  # Ensure sufficient quota remains
                print(f"{CLIColors.YELLOW}⚠️ API key has low quota remaining ({quota_status['remaining_today']} units){CLIColors.END}")
                return False

            # Create a temporary YouTube service with the test key
            youtube = build('youtube', 'v3', developerKey=api_key)
            
            # Try a minimal API request to test the key
            request = youtube.search().list(
                part="id",
                maxResults=1,
                type="video"
            )
            request.execute()
            
            # Record quota usage for this request (search.list costs 100 units)
            self.quota_tracker.record_usage(api_key, cost=100)
            
            print(f"{CLIColors.GREEN}✅ API key is valid (Remaining quota: {quota_status['remaining_today']} units){CLIColors.END}")
            return True
            
        except HttpError as e:
            error_str = str(e)
            if "quota" in error_str.lower():
                print(f"{CLIColors.YELLOW}⚠️ API key has exceeded its daily quota{CLIColors.END}")
                # Record that we've hit the quota limit
                self.quota_tracker.record_usage(api_key, cost=10000)
            else:
                print(f"{CLIColors.RED}❌ Invalid API key: {error_str}{CLIColors.END}")
            return False
            
        except Exception as e:
            print(f"{CLIColors.RED}❌ Error testing API key: {str(e)}{CLIColors.END}")
            return False

    def add_api_key(self, new_key: str):
        """Add a new API key to the rotation."""
        if new_key not in self.api_keys:
            # Test the API key before adding
            print(f"{CLIColors.CYAN}🔍 Testing new API key...{CLIColors.END}")
            if self.test_api_key(new_key):
                self.api_keys.append(new_key)
                with open(self.api_keys_file, 'w') as f:
                    json.dump(self.api_keys, f, indent=2)
                print(f"{CLIColors.GREEN}✅ New API key validated and added successfully!{CLIColors.END}")
                return True
            else:
                print(f"{CLIColors.RED}❌ API key validation failed - key not added{CLIColors.END}")
                return False
        else:
            print(f"{CLIColors.YELLOW}⚠️ API key already exists{CLIColors.END}")
            return False
        
    def ensure_data_dir(self):
        """Create data directory if it doesn't exist and initialize files."""
        os.makedirs("data", exist_ok=True)
        
        # Initialize playlists file if it doesn't exist
        if not os.path.exists(self.playlists_file):
            with open(self.playlists_file, 'w') as f:
                json.dump({}, f)
                
        # Initialize used videos file if it doesn't exist
        if not os.path.exists(self.used_videos_file):
            with open(self.used_videos_file, 'w') as f:
                json.dump({}, f)
                
        # Initialize cache file if it doesn't exist
        if not os.path.exists(self.cache_file):
            with open(self.cache_file, 'w') as f:
                json.dump({
                    "search_cache": {},
                    "video_details_cache": {},
                    "channel_cache": {},
                    "last_quota_reset": datetime.now().isoformat(),
                    "quota_used": 0
                }, f)
    
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

    def get_video_details(self, video_id: str) -> dict:
        """Get video duration and category with caching."""
        # Check cache first
        if video_id in self.cache["video_details_cache"]:
            cached = self.cache["video_details_cache"][video_id]
            cache_time = datetime.fromisoformat(cached["timestamp"])
            if (datetime.now() - cache_time).total_seconds() < self.cache_duration:
                return cached["details"]

        # Check quota before making API call
        if not self.check_quota(1):
            print(f"{CLIColors.YELLOW}⚠️ Daily YouTube API quota exceeded. Try again tomorrow.{CLIColors.END}")
            return None

        try:
            response = self.youtube.videos().list(
                part="contentDetails,snippet,statistics",
                id=video_id
            ).execute()
            
            if response["items"]:
                item = response["items"][0]
                duration = self.parse_iso8601_duration(item["contentDetails"]["duration"])
                title = item["snippet"]["title"]
                stats = item["statistics"]
                details = {
                    "duration": duration,
                    "title": title,
                    "viewCount": int(stats.get("viewCount", 0)),
                    "likeCount": int(stats.get("likeCount", 0)),
                    "commentCount": int(stats.get("commentCount", 0))
                }
                
                # Cache the result
                self.cache["video_details_cache"][video_id] = {
                    "details": details,
                    "timestamp": datetime.now().isoformat()
                }
                self.save_cache()
                return details
        except Exception as e:
            print(f"{CLIColors.YELLOW}⚠️ Error fetching video details: {e}{CLIColors.END}")
        return None

    def load_cache(self):
        """Load the cache from file."""
        try:
            with open(self.cache_file, 'r') as f:
                self.cache = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self.cache = {
                "search_cache": {},
                "video_details_cache": {},
                "channel_cache": {},
                "last_quota_reset": datetime.now().isoformat(),
                "quota_used": 0
            }
            self.save_cache()

    def save_cache(self):
        """Save the cache to file."""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def check_quota(self, units_needed: int = 1) -> bool:
        """Check if we have enough quota units available."""
        now = datetime.now()
        last_reset = datetime.fromisoformat(self.cache["last_quota_reset"])
        
        # Reset quota if it's been 24 hours
        if (now - last_reset).total_seconds() >= 24 * 60 * 60:
            self.cache["last_quota_reset"] = now.isoformat()
            self.cache["quota_used"] = 0
            self.save_cache()
            return True

        # Check if we have enough quota
        if self.cache["quota_used"] + units_needed > 9500:  # Leave some buffer
            return False
            
        self.cache["quota_used"] += units_needed
        self.save_cache()
        return True

    def get_channel_id(self, channel_name: str) -> str:
        """Get channel ID from channel name with caching."""
        # Check cache first
        if channel_name in self.cache["channel_cache"]:
            cached = self.cache["channel_cache"][channel_name]
            cache_time = datetime.fromisoformat(cached["timestamp"])
            if (datetime.now() - cache_time).total_seconds() < self.cache_duration:
                return cached["channel_id"]

        # Check quota before making API call
        if not self.check_quota(100):
            print(f"{CLIColors.YELLOW}⚠️ Daily YouTube API quota exceeded. Try again tomorrow.{CLIColors.END}")
            return None

        try:
            response = self.youtube.search().list(
                part="id",
                q=channel_name,
                type="channel",
                maxResults=1
            ).execute()

            if response["items"]:
                channel_id = response["items"][0]["id"]["channelId"]
                # Cache the result
                self.cache["channel_cache"][channel_name] = {
                    "channel_id": channel_id,
                    "timestamp": datetime.now().isoformat()
                }
                self.save_cache()
                return channel_id
        except Exception as e:
            print(f"{CLIColors.YELLOW}⚠️ Error finding channel: {e}{CLIColors.END}")
        return None

    def smart_search(self, max_results: int = 300, query: str = None) -> List[str]:
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
                                video_details = self.get_video_details(video_id)
                                if not video_details:
                                    continue
                                
                                title = video_details["title"]
                                duration = video_details["duration"]
                                
                                # Skip videos shorter than 3 minutes
                                if duration < self.config.min_duration_seconds:
                                    continue
                                    
                                if any(exc in title for exc in self.config.exclude_keywords):
                                    continue
                                
                                music_indicators = ["music", "song", "audio", "track", "hit", "mix", 
                                                  "official", "video", "cover", "remix", "live", "acoustic",
                                                  "extended", "hour", "playlist", "compilation"]
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
            
    def save_playlist(self, name: str, url: str, video_ids: List[str]):
        """Save a playlist with given name and URL."""
        try:
            self.ensure_data_dir()  # Make sure data directory and files exist
            
            with open(self.playlists_file, 'r') as f:
                try:
                    playlists = json.load(f)
                except json.JSONDecodeError:
                    playlists = {}
            
            playlists[name] = {
                'url': url,
                'video_ids': video_ids,
                'created_at': datetime.now().isoformat(),
                'last_played': None
            }
            
            with open(self.playlists_file, 'w') as f:
                json.dump(playlists, f, indent=2)
            print(f"{CLIColors.GREEN}✅ Playlist saved as '{name}'{CLIColors.END}")
        except Exception as e:
            print(f"{CLIColors.RED}❌ Error saving playlist: {str(e)}{CLIColors.END}")
    
    def get_saved_playlists(self) -> Dict:
        """Get all saved playlists."""
        if os.path.exists(self.playlists_file):
            try:
                with open(self.playlists_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def delete_playlist(self, name: str) -> bool:
        """Delete a saved playlist by name."""
        playlists = self.get_saved_playlists()
        if name in playlists:
            del playlists[name]
            with open(self.playlists_file, 'w') as f:
                json.dump(playlists, f, indent=2)
            return True
        return False
        
    def clear_search_history(self):
        """Clear the used videos history."""
        if os.path.exists(self.used_videos_file):
            os.remove(self.used_videos_file)
        print(f"{CLIColors.GREEN}✅ Search history cleared{CLIColors.END}")
        
    def open_in_chrome(self, url: str):
        """Open URL in Chrome with specified Gmail account."""
        try:
            chrome_cmd = f'"{self.config.chrome_path}" --profile-email="{self.config.gmail_account}" "{url}"'
            os.system(chrome_cmd)
            print(f"{CLIColors.GREEN}✅ Opened in Chrome with account {self.config.gmail_account}{CLIColors.END}")
        except Exception as e:
            print(f"{CLIColors.RED}❌ Error opening Chrome: {e}{CLIColors.END}")

def handle_search_results(manager: YouTubeManager, video_ids: List[str], video_details_list: List[dict], search_query: str):
    """Handle search results and display options"""
    if len(video_ids) >= 5:
        # Display search results
        print(f"\n{CLIColors.GREEN}Found {len(video_ids)} matching videos:{CLIColors.END}")
        for i, vid in enumerate(video_details_list, 1):
            duration_min = vid["duration"] // 60
            duration_sec = vid["duration"] % 60
            views = format(vid.get("viewCount", 0), ",")
            likes = format(vid.get("likeCount", 0), ",")
            print(f"{i}. {CLIColors.CYAN}{vid['title']}{CLIColors.END}")
            print(f"   ⏱️  {duration_min}:{duration_sec:02d} | 📺 {vid['channel']}")
            print(f"   👀 {views} views | 👍 {likes} likes")

        playlist_url = manager.create_youtube_playlist_url(video_ids)
        print(f"\n{CLIColors.GREEN}✅ Playlist created successfully!{CLIColors.END}")

        # Update used videos with detailed metadata
        used_videos = manager.load_used_videos()
        for vid in video_details_list:
            used_videos[vid["id"]] = {
                "used_at": datetime.now().isoformat(),
                "playlist_type": f"search:{search_query}",
                "title": vid["title"],
                "channel": vid["channel"],
                "duration": vid["duration"],
                "viewCount": vid.get("viewCount", 0),
                "likeCount": vid.get("likeCount", 0)
            }
        manager.save_used_videos(used_videos)

        # Ask user what to do with the playlist
        handle_playlist_options(manager, playlist_url, video_ids)
    else:
        print(f"{CLIColors.RED}❌ Not enough relevant videos found for '{search_query}'{CLIColors.END}")

def handle_playlist_options(manager: YouTubeManager, playlist_url: str, video_ids: List[str]):
    """Handle options after playlist generation"""
    while True:
        print(f"\n{CLIColors.BLUE}What would you like to do with this playlist?{CLIColors.END}")
        
        options = {
            "1": "Open in Chrome browser (with Gmail account)",
            "2": "Display URL only",
            "3": "Save playlist",
            "4": "View saved playlists",
            "5": "Delete saved playlist",
            "6": "Clear search history",
            "7": "Back to main menu"
        }
        
        for key, value in options.items():
            print(f"  {key}. {value}")
        
        choice = input(f"\n{CLIColors.BOLD}Choose option (1-7): {CLIColors.END}").strip()
        
        if choice == "1":
            manager.open_in_chrome(playlist_url)
            
        elif choice == "2":
            print(f"\n{CLIColors.CYAN}🔗 Playlist URL: {playlist_url}{CLIColors.END}")
            
        elif choice == "3":
            name = input(f"\n{CLIColors.BOLD}Enter playlist name or number: {CLIColors.END}").strip()
            manager.save_playlist(name, playlist_url, video_ids)
            
        elif choice == "4":
            playlists = manager.get_saved_playlists()
            if not playlists:
                print(f"{CLIColors.YELLOW}No saved playlists found.{CLIColors.END}")
            else:
                print(f"\n{CLIColors.CYAN}Saved Playlists:{CLIColors.END}")
                for name, data in playlists.items():
                    print(f"  • {name} (Created: {data['created_at']})")
                    
        elif choice == "5":
            playlists = manager.get_saved_playlists()
            if not playlists:
                print(f"{CLIColors.YELLOW}No playlists to delete.{CLIColors.END}")
            else:
                print(f"\n{CLIColors.CYAN}Available Playlists:{CLIColors.END}")
                for name in playlists.keys():
                    print(f"  • {name}")
                name = input(f"\n{CLIColors.BOLD}Enter playlist name to delete: {CLIColors.END}").strip()
                if manager.delete_playlist(name):
                    print(f"{CLIColors.GREEN}✅ Playlist '{name}' deleted{CLIColors.END}")
                else:
                    print(f"{CLIColors.RED}❌ Playlist '{name}' not found{CLIColors.END}")
                    
        elif choice == "6":
            confirm = input(f"{CLIColors.YELLOW}Are you sure you want to clear search history? (y/n): {CLIColors.END}").strip().lower()
            if confirm == 'y':
                manager.clear_search_history()
                
        elif choice == "7":
            return
            
        else:
            print(f"{CLIColors.RED}❌ Invalid option{CLIColors.END}")
            
        input(f"\n{CLIColors.BOLD}Press Enter to continue...{CLIColors.END}")
1
def get_terminal_width():
    """Get the terminal width."""
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80  # default width

def center_text(text, width=None):
    """Center align text."""
    if width is None:
        width = get_terminal_width()
    return text.center(width)

def print_centered(text, width=None):
    """Print centered text."""
    print(center_text(text, width))

def print_menu_item(number, text, width=None):
    """Print a centered menu item."""
    menu_text = f"  {number}. {text}"
    print_centered(menu_text, width)

def manage_api_keys(manager):
    """Manage YouTube API keys"""
    while True:
        print(f"\n{CLIColors.CYAN}🔑 YouTube API Key Management{CLIColors.END}")
        print("=" * 60)
        print("1. View API Keys & Quota Status")
        print("2. Add new API key")
        print("3. Remove API key")
        print("4. Test API keys")
        print("5. Back to main menu")
        print("=" * 60)
        
        choice = input(f"\n{CLIColors.BOLD}Choose option (1-5): {CLIColors.END}").strip()
        
        if choice == "1":
            # Display detailed quota status for all keys
            manager.display_quota_status()
            
        elif choice == "2":
            new_key = input(f"\n{CLIColors.BOLD}Enter new API key: {CLIColors.END}").strip()
            if new_key:
                print(f"\n{CLIColors.CYAN}🔍 Validating API key...{CLIColors.END}")
                if manager.add_api_key(new_key):
                    status = manager.get_current_api_key_status()
                    print(f"{CLIColors.GREEN}✅ API key added successfully!")
                    print(f"   ├── Key: {status['key_preview']}")
                    print(f"   ├── Status: {status['status'].title()}")
                    print(f"   └── Quota Remaining: {status['quota_remaining']:,} units{CLIColors.END}")
        
        elif choice == "3":
            if len(manager.api_keys) <= 1:
                print(f"{CLIColors.RED}❌ Cannot remove the last API key{CLIColors.END}")
                continue
                
            print(f"\n{CLIColors.CYAN}Select API key to remove:{CLIColors.END}")
            for i, key in enumerate(manager.api_keys, 1):
                key_preview = f"{key[:4]}...{key[-4:]}"
                status = manager.quota_tracker.get_quota_status(key)
                status_text = f"{CLIColors.GREEN}Active" if status['remaining_today'] > 1000 else \
                            f"{CLIColors.YELLOW}Low Quota" if status['remaining_today'] > 0 else \
                            f"{CLIColors.RED}Exceeded"
                print(f"{i}. {key_preview} - {status_text} ({status['remaining_today']:,} units remaining){CLIColors.END}")
            
            key_num = input(f"\n{CLIColors.BOLD}Enter number to remove (1-{len(manager.api_keys)}): {CLIColors.END}").strip()
            try:
                idx = int(key_num) - 1
                if 0 <= idx < len(manager.api_keys):
                    removed_key = manager.api_keys.pop(idx)
                    with open(manager.api_keys_file, 'w') as f:
                        json.dump(manager.api_keys, f, indent=2)
                    print(f"{CLIColors.GREEN}✅ API key removed successfully{CLIColors.END}")
                    
                    # If we removed the current key, rotate to another one
                    if idx == manager.current_key_index:
                        if manager.rotate_api_key():
                            print(f"{CLIColors.GREEN}✅ Successfully rotated to next available key{CLIColors.END}")
                        else:
                            manager.current_key_index = 0
                            manager.youtube = manager._build_youtube_client()
                            print(f"{CLIColors.YELLOW}⚠️ Using first available key{CLIColors.END}")
                else:
                    print(f"{CLIColors.RED}❌ Invalid selection{CLIColors.END}")
            except ValueError:
                print(f"{CLIColors.RED}❌ Invalid input{CLIColors.END}")
        
        elif choice == "4":
            print(f"\n{CLIColors.CYAN}Testing all API keys...{CLIColors.END}")
            for i, key in enumerate(manager.api_keys, 1):
                key_preview = f"{key[:4]}...{key[-4:]}"
                print(f"\n{CLIColors.CYAN}Testing key {i}/{len(manager.api_keys)}: {key_preview}{CLIColors.END}")
                
                if manager.test_api_key(key):
                    status = manager.quota_tracker.get_quota_status(key)
                    print(f"   ├── Status: {CLIColors.GREEN}Working{CLIColors.END}")
                    print(f"   ├── Quota Available: {status['remaining_today']:,} units")
                    print(f"   └── Usage Today: {status['today_usage']:,} units")
                else:
                    print(f"   └── {CLIColors.RED}❌ Key validation failed{CLIColors.END}")
        
        elif choice == "5":
            break
        
        input(f"\n{CLIColors.BOLD}Press Enter to continue...{CLIColors.END}")

def youtube_menu():
    """YouTube playlist generator menu"""
    width = get_terminal_width()
    padding = "=" * width

    print("\n" + padding)
    print(f"{CLIColors.CYAN}🎵 YouTube Playlist Generator 🎵{CLIColors.END}")
    print(padding + "\n")

    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print(f"{CLIColors.RED}❗ Error: YOUTUBE_API_KEY not set in .env file{CLIColors.END}")
        print("Please add your YouTube API key to the .env file")
        return

    config = PlaylistConfig()
    manager = YouTubeManager(api_key, config)

    options = {
        "1": "📱 Generate Smart Playlist",
        "2": "🔍 YouTube Search",
        "3": "📋 View Saved Playlists",
        "4": "🗑️  Clear Search History",
        "5": "🔑 Manage API Keys",
        "6": "↩️  Back to Main Menu"
    }
    
    print("Available Options:\n")
    for key, value in options.items():
        print(f"  {key}. {value}")

    print()  # Add a blank line
    prompt = f"{CLIColors.BOLD}Choose option (1-6): {CLIColors.END}"
    print(prompt)
    choice = input(">>> ").strip()

    if choice == "1":
        print(f"\n{CLIColors.YELLOW}🔍 Generating smart playlist...{CLIColors.END}")
        video_ids = manager.smart_search(max_results=config.num_videos * 4)

        if len(video_ids) >= 10:
            selected = video_ids[:config.num_videos]
            playlist_url = manager.create_youtube_playlist_url(selected)

            print(f"\n{CLIColors.GREEN}✅ Playlist created with {len(selected)} videos!{CLIColors.END}")

            # Update used videos
            used_videos = manager.load_used_videos()
            for vid_id in selected:
                used_videos[vid_id] = {
                    "used_at": datetime.now().isoformat(),
                    "playlist_type": "smart"
                }
            manager.save_used_videos(used_videos)
            
            # Ask user what to do with the playlist
            handle_playlist_options(manager, playlist_url, selected)
        else:
            print(f"{CLIColors.RED}❌ Only found {len(video_ids)} videos, too few for a playlist{CLIColors.END}")
    
    elif choice == "2":
        print(f"\n{CLIColors.YELLOW}🔍 Advanced YouTube Search{CLIColors.END}")
        print("Search for any type of YouTube content (tutorials, reviews, vlogs, etc.)")
        
        # Get search parameters
        search_query = input(f"{CLIColors.BOLD}Enter what you want to search for: {CLIColors.END}").strip()
        if not search_query:
            print(f"{CLIColors.RED}❌ Search query cannot be empty!{CLIColors.END}")
            return

        # Advanced search options
        print(f"\n{CLIColors.CYAN}Search Options:{CLIColors.END}")
        print("1. Most Relevant")
        print("2. Most Recent")
        print("3. Most Viewed")
        print("4. Highest Rated")
        sort_choice = input(f"{CLIColors.BOLD}Choose sorting option (1-4) [default=1]: {CLIColors.END}").strip() or "1"
        
        sort_options = {
            "1": "relevance",
            "2": "date",
            "3": "viewCount",
            "4": "rating"
        }
        sort_order = sort_options.get(sort_choice, "relevance")

        # Duration filter
        print(f"\n{CLIColors.CYAN}Video Duration:{CLIColors.END}")
        print("1. Any length")
        print("2. Short (< 4 minutes)")
        print("3. Medium (4-20 minutes)")
        print("4. Long (> 20 minutes)")
        duration_choice = input(f"{CLIColors.BOLD}Choose duration filter (1-4) [default=1]: {CLIColors.END}").strip() or "1"

        duration_filters = {
            "1": (0, float('inf')),
            "2": (0, 240),
            "3": (240, 1200),
            "4": (1200, float('inf'))
        }
        min_duration, max_duration = duration_filters.get(duration_choice, (0, float('inf')))

        # Channel filter (optional)
        channel_filter = input(f"\n{CLIColors.BOLD}Filter by channel name (optional): {CLIColors.END}").strip()

        print(f"\n{CLIColors.YELLOW}🔍 Searching for '{search_query}'...{CLIColors.END}")
        try:
            # Generate cache key based on search parameters
            cache_key = f"{search_query}_{sort_order}_{duration_choice}"
            if channel_filter:
                cache_key += f"_{channel_filter}"

            # Check if we have cached results
            if cache_key in manager.cache["search_cache"]:
                cached = manager.cache["search_cache"][cache_key]
                cache_time = datetime.fromisoformat(cached["timestamp"])
                if (datetime.now() - cache_time).total_seconds() < manager.cache_duration:
                    print(f"{CLIColors.GREEN}📋 Using cached results...{CLIColors.END}")
                    video_ids = cached["video_ids"]
                    video_details_list = cached["video_details"]
                    if video_ids and video_details_list:
                        return handle_search_results(manager, video_ids, video_details_list, search_query)

            # Check quota before making API call
            if not manager.check_quota(100):
                print(f"{CLIColors.RED}❌ Daily YouTube API quota exceeded. Try again tomorrow or use cached results.{CLIColors.END}")
                return

            search_params = {
                "part": "id,snippet",
                "q": search_query,
                "type": "video",
                "order": sort_order,
                "maxResults": 50,
                "regionCode": "US"
            }

            if channel_filter:
                channel_id = manager.get_channel_id(channel_filter)
                if channel_id:
                    search_params["channelId"] = channel_id
                else:
                    print(f"{CLIColors.YELLOW}⚠️ Channel not found, searching without channel filter{CLIColors.END}")

            response = manager.youtube.search().list(**search_params).execute()

            video_ids = []
            video_details_list = []  # Store video details for display

            print(f"\n{CLIColors.CYAN}Finding matching videos...{CLIColors.END}")
            with tqdm(total=50, desc="Processing results") as pbar:
                for item in response.get("items", []):
                    video_id = item["id"]["videoId"]
                    
                    # Try to get from cache first
                    details = None
                    if video_id in manager.cache["video_details_cache"]:
                        cached = manager.cache["video_details_cache"][video_id]
                        cache_time = datetime.fromisoformat(cached["timestamp"])
                        if (datetime.now() - cache_time).total_seconds() < manager.cache_duration:
                            details = cached["details"]
                    
                    # If not in cache, fetch from API
                    if not details:
                        if not manager.check_quota(1):
                            print(f"{CLIColors.YELLOW}⚠️ Quota exceeded, using partial results{CLIColors.END}")
                            break
                        details = manager.get_video_details(video_id)
                    
                    if not details:
                        continue

                    duration = details.get("duration", 0)
                    if min_duration <= duration <= max_duration:
                        title = details["title"]
                        video_ids.append(video_id)
                        video_details_list.append({
                            "id": video_id,
                            "title": title,
                            "duration": duration,
                            "channel": item["snippet"]["channelTitle"],
                            "viewCount": details.get("viewCount", 0),
                            "likeCount": details.get("likeCount", 0)
                        })
                        pbar.update(1)

                    if len(video_ids) >= 50:
                        break

            # Cache the search results
            manager.cache["search_cache"][cache_key] = {
                "video_ids": video_ids,
                "video_details": video_details_list,
                "timestamp": datetime.now().isoformat()
            }
            manager.save_cache()

            if len(video_ids) >= 5:
                # Display search results
                print(f"\n{CLIColors.GREEN}Found {len(video_ids)} matching videos:{CLIColors.END}")
                for i, vid in enumerate(video_details_list, 1):
                    duration_min = vid["duration"] // 60
                    duration_sec = vid["duration"] % 60
                    views = format(vid["viewCount"], ",")
                    likes = format(vid["likeCount"], ",")
                    print(f"{i}. {CLIColors.CYAN}{vid['title']}{CLIColors.END}")
                    print(f"   ⏱️  {duration_min}:{duration_sec:02d} | 📺 {vid['channel']}")
                    print(f"   👀 {views} views | 👍 {likes} likes")

                playlist_url = manager.create_youtube_playlist_url(video_ids)
                print(f"\n{CLIColors.GREEN}✅ Playlist created successfully!{CLIColors.END}")

                # Update used videos with detailed metadata
                used_videos = manager.load_used_videos()
                for vid in video_details_list:
                    used_videos[vid["id"]] = {
                        "used_at": datetime.now().isoformat(),
                        "playlist_type": f"advanced_search:{search_query}",
                        "title": vid["title"],
                        "channel": vid["channel"],
                        "duration": vid["duration"],
                        "viewCount": vid["viewCount"],
                        "likeCount": vid["likeCount"]
                    }
                manager.save_used_videos(used_videos)

                # Ask user what to do with the playlist
                handle_playlist_options(manager, playlist_url, video_ids)
            else:
                print(f"{CLIColors.RED}❌ Not enough relevant videos found for '{search_query}'{CLIColors.END}")

        except Exception as e:
            error_str = str(e)
            if "quota" in error_str.lower():
                # Try rotating API key and retrying up to 3 times
                for retry in range(3):
                    if manager.rotate_api_key():
                        print(f"{CLIColors.YELLOW}🔄 Attempt {retry + 1}/3: Rotating to next API key...{CLIColors.END}")
                        try:
                            # Retry the search with new API key
                            response = manager.youtube.search().list(**search_params).execute()
                            video_ids = []
                            video_details_list = []
                            
                            print(f"\n{CLIColors.CYAN}Finding matching videos...{CLIColors.END}")
                            with tqdm(total=50, desc="Processing results") as pbar:
                                for item in response.get("items", []):
                                    video_id = item["id"]["videoId"]
                                    details = manager.get_video_details(video_id)
                                    
                                    if not details:
                                        continue

                                    duration = details.get("duration", 0)
                                    if min_duration <= duration <= max_duration:
                                        title = details["title"]
                                        video_ids.append(video_id)
                                        video_details_list.append({
                                            "id": video_id,
                                            "title": title,
                                            "duration": duration,
                                            "channel": item["snippet"]["channelTitle"]
                                        })
                                        pbar.update(1)

                                    if len(video_ids) >= 50:
                                        break
                                        
                            if video_ids:
                                print(f"{CLIColors.GREEN}✅ Search successful with backup API key{CLIColors.END}")
                                return handle_search_results(manager, video_ids, video_details_list, search_query)
                        except Exception as retry_e:
                            if "quota" not in str(retry_e).lower():
                                print(f"{CLIColors.RED}❌ Error with backup API key: {str(retry_e)}{CLIColors.END}")
                                break
                            continue
                    else:
                        print(f"{CLIColors.RED}❌ No more working API keys available{CLIColors.END}")
                        break
            
            print(f"{CLIColors.RED}❌ Error during search: {error_str}{CLIColors.END}")
            
            # Try to use cached results if available
            if cache_key in manager.cache["search_cache"]:
                cached = manager.cache["search_cache"][cache_key]
                print(f"{CLIColors.YELLOW}🔄 Using cached results from previous search...{CLIColors.END}")
                video_ids = cached["video_ids"]
                video_details_list = cached["video_details"]
                if video_ids and video_details_list:
                    # Display cached results
                    print(f"\n{CLIColors.GREEN}Found {len(video_ids)} videos from cache:{CLIColors.END}")
                    for i, vid in enumerate(video_details_list, 1):
                        duration_min = vid["duration"] // 60
                        duration_sec = vid["duration"] % 60
                        views = format(vid.get("viewCount", 0), ",")
                        likes = format(vid.get("likeCount", 0), ",")
                        print(f"{i}. {CLIColors.CYAN}{vid['title']}{CLIColors.END}")
                        print(f"   ⏱️  {duration_min}:{duration_sec:02d} | 📺 {vid['channel']}")
                        print(f"   👀 {views} views | 👍 {likes} likes")

                    playlist_url = manager.create_youtube_playlist_url(video_ids)
                    handle_playlist_options(manager, playlist_url, video_ids)
    
    elif choice == "3":
        playlists = manager.get_saved_playlists()
        if not playlists:
            print(f"{CLIColors.YELLOW}No saved playlists found.{CLIColors.END}")
        else:
            print(f"\n{CLIColors.CYAN}Saved Playlists:{CLIColors.END}")
            for name, data in playlists.items():
                print(f"  • {name} (Created: {data['created_at']})")
                
    elif choice == "4":
        confirm = input(f"{CLIColors.YELLOW}Are you sure you want to clear search history? (y/n): {CLIColors.END}").strip().lower()
        if confirm == 'y':
            manager.clear_search_history()
            
    elif choice == "5":
        manage_api_keys(manager)
    elif choice == "6":
        return
    else:
        print(f"{CLIColors.YELLOW}⚠️ Feature coming soon!{CLIColors.END}")