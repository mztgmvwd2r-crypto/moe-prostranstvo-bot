import json
import os
from datetime import datetime, date
from typing import Dict, List, Optional

# Use relative path for cloud deployment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
DIARY_FILE = os.path.join(DATA_DIR, "diary.json")
DAILY_ENERGY_FILE = os.path.join(DATA_DIR, "daily_energy.json")

def load_json(filepath):
    """Load JSON file or return empty dict"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(filepath, data):
    """Save data to JSON file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class UserDatabase:
    """Manage user data and subscription status"""
    
    @staticmethod
    def get_user(user_id: int) -> Dict:
        """Get user data"""
        users = load_json(USERS_FILE)
        user_id_str = str(user_id)
        
        if user_id_str not in users:
            users[user_id_str] = {
                "user_id": user_id,
                "subscription": "free",  # free, base, premium
                "daily_energy_count": 0,
                "tarot_count": 0,
                "last_daily_energy": None,
                "last_tarot": None,
                "notifications": {
                    "daily_energy": False,
                    "diary_reminder": False
                },
                "created_at": datetime.now().isoformat()
            }
            save_json(USERS_FILE, users)
        
        return users[user_id_str]
    
    @staticmethod
    def update_user(user_id: int, updates: Dict):
        """Update user data"""
        users = load_json(USERS_FILE)
        user_id_str = str(user_id)
        
        if user_id_str in users:
            users[user_id_str].update(updates)
            save_json(USERS_FILE, users)
    
    @staticmethod
    def can_use_daily_energy(user_id: int) -> bool:
        """Check if user can request daily energy"""
        user = UserDatabase.get_user(user_id)
        today = date.today().isoformat()
        
        if user["subscription"] != "free":
            return True
        
        return user["last_daily_energy"] != today
    
    @staticmethod
    def can_use_tarot(user_id: int) -> bool:
        """Check if user can request tarot reading"""
        user = UserDatabase.get_user(user_id)
        today = date.today().isoformat()
        
        if user["subscription"] != "free":
            return True
        
        return user["last_tarot"] != today
    
    @staticmethod
    def record_daily_energy(user_id: int):
        """Record daily energy usage"""
        today = date.today().isoformat()
        UserDatabase.update_user(user_id, {
            "last_daily_energy": today,
            "daily_energy_count": UserDatabase.get_user(user_id)["daily_energy_count"] + 1
        })
    
    @staticmethod
    def record_tarot(user_id: int):
        """Record tarot reading usage"""
        today = date.today().isoformat()
        UserDatabase.update_user(user_id, {
            "last_tarot": today,
            "tarot_count": UserDatabase.get_user(user_id)["tarot_count"] + 1
        })
    
    @staticmethod
    def is_premium(user_id: int) -> bool:
        """Check if user has premium subscription"""
        user = UserDatabase.get_user(user_id)
        return user["subscription"] == "premium"
    
    @staticmethod
    def is_paid(user_id: int) -> bool:
        """Check if user has any paid subscription"""
        user = UserDatabase.get_user(user_id)
        return user["subscription"] in ["base", "premium"]


class DiaryDatabase:
    """Manage diary entries"""
    
    @staticmethod
    def add_entry(user_id: int, content: str, entry_type: str = "note"):
        """Add diary entry"""
        diary = load_json(DIARY_FILE)
        user_id_str = str(user_id)
        
        if user_id_str not in diary:
            diary[user_id_str] = []
        
        entry = {
            "id": len(diary[user_id_str]) + 1,
            "content": content,
            "type": entry_type,  # note, tarot, daily_energy
            "created_at": datetime.now().isoformat()
        }
        
        diary[user_id_str].append(entry)
        save_json(DIARY_FILE, diary)
        return entry
    
    @staticmethod
    def get_entries(user_id: int, limit: Optional[int] = None) -> List[Dict]:
        """Get user's diary entries"""
        diary = load_json(DIARY_FILE)
        user_id_str = str(user_id)
        
        entries = diary.get(user_id_str, [])
        entries.sort(key=lambda x: x["created_at"], reverse=True)
        
        if limit:
            return entries[:limit]
        return entries
    
    @staticmethod
    def get_entry_count(user_id: int) -> int:
        """Get total number of entries"""
        diary = load_json(DIARY_FILE)
        user_id_str = str(user_id)
        return len(diary.get(user_id_str, []))


class DailyEnergyCache:
    """Cache daily energy to avoid regenerating"""
    
    @staticmethod
    def get_today() -> Optional[Dict]:
        """Get today's energy if cached"""
        cache = load_json(DAILY_ENERGY_FILE)
        today = date.today().isoformat()
        return cache.get(today)
    
    @staticmethod
    def set_today(energy_data: Dict):
        """Cache today's energy"""
        cache = load_json(DAILY_ENERGY_FILE)
        today = date.today().isoformat()
        cache[today] = energy_data
        save_json(DAILY_ENERGY_FILE, cache)
