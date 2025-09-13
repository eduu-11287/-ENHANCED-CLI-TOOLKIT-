import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional

class QuotaTracker:
    def __init__(self, quota_file: str = "data/quota_usage.json"):
        self.quota_file = quota_file
        self.quota_data: Dict = self._load_quota_data()
        
    def _load_quota_data(self) -> Dict:
        """Load quota data from file or initialize new data."""
        if os.path.exists(self.quota_file):
            try:
                with open(self.quota_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
        
    def _save_quota_data(self):
        """Save quota data to file."""
        os.makedirs(os.path.dirname(self.quota_file), exist_ok=True)
        with open(self.quota_file, 'w') as f:
            json.dump(self.quota_data, f, indent=2)
            
    def record_usage(self, api_key: str, cost: int = 1):
        """Record API usage for a key."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if api_key not in self.quota_data:
            self.quota_data[api_key] = {}
            
        if today not in self.quota_data[api_key]:
            self.quota_data[api_key][today] = 0
            
        self.quota_data[api_key][today] += cost
        self._save_quota_data()
        
    def get_usage(self, api_key: str, days: int = 1) -> int:
        """Get total usage for an API key over the specified number of days."""
        if api_key not in self.quota_data:
            return 0
            
        total = 0
        date = datetime.now()
        
        for _ in range(days):
            day = date.strftime("%Y-%m-%d")
            total += self.quota_data[api_key].get(day, 0)
            date -= timedelta(days=1)
            
        return total
        
    def clean_old_data(self, days_to_keep: int = 30):
        """Remove quota data older than specified days."""
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        
        for api_key in list(self.quota_data.keys()):
            for date in list(self.quota_data[api_key].keys()):
                try:
                    date_obj = datetime.strptime(date, "%Y-%m-%d")
                    if date_obj < cutoff:
                        del self.quota_data[api_key][date]
                except ValueError:
                    continue
                    
            # Remove empty API key entries
            if not self.quota_data[api_key]:
                del self.quota_data[api_key]
                
        self._save_quota_data()
        
    def get_quota_status(self, api_key: str) -> Dict:
        """Get detailed quota status for an API key."""
        daily_limit = 10000  # YouTube API's standard daily quota limit
        
        return {
            "today_usage": self.get_usage(api_key, 1),
            "week_usage": self.get_usage(api_key, 7),
            "month_usage": self.get_usage(api_key, 30),
            "remaining_today": max(0, daily_limit - self.get_usage(api_key, 1))
        }