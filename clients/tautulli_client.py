import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time


class TautulliClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()

    def _request(self, cmd: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to Tautulli API"""
        url = f"{self.base_url}/api/v2"
        request_params = {"apikey": self.api_key, "cmd": cmd}
        if params:
            request_params.update(params)

        response = self.session.get(url, params=request_params)
        response.raise_for_status()
        data = response.json()

        if data.get("response", {}).get("result") == "success":
            return data.get("response", {}).get("data", {})
        else:
            raise Exception(
                f"Tautulli API error: {data.get('response', {}).get('message', 'Unknown error')}"
            )

    def get_users(self) -> List[Dict]:
        """Get all users from Tautulli"""
        data = self._request("get_users")
        # Tautulli returns users in different formats
        if isinstance(data, dict):
            return data.get("data", []) if "data" in data else []
        elif isinstance(data, list):
            return data
        return []

    def get_user_history(
        self,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        length: int = 10000,
    ) -> List[Dict]:
        """Get watch history for a user"""
        params = {"length": length, "media_info": 1}  # Include media metadata (genres, actors, directors)

        if user_id:
            # Tautulli expects user_id as integer
            try:
                params["user_id"] = int(user_id)
            except (ValueError, TypeError):
                params["user_id"] = user_id
        elif username:
            params["user"] = username

        # Calculate date range timestamps for filtering
        start_timestamp = None
        end_timestamp = None

        if start_date:
            try:
                # Parse date string and convert to Unix timestamp (start of day)
                dt = datetime.strptime(start_date, "%Y-%m-%d")
                start_timestamp = int(dt.timestamp())
            except (ValueError, TypeError):
                pass

        if end_date:
            try:
                # Parse date string, add end of day, convert to Unix timestamp
                dt = datetime.strptime(end_date, "%Y-%m-%d")
                dt = dt.replace(hour=23, minute=59, second=59)
                end_timestamp = int(dt.timestamp())
            except (ValueError, TypeError):
                pass

        # Fetch all history (Tautulli's date filtering seems unreliable, so we'll filter in Python)
        data = self._request("get_history", params)
        # Tautulli get_history returns nested structure: { "data": [...], "recordsFiltered": N, ... }
        # Handle different response formats
        history = []
        if isinstance(data, dict):
            # Check if there's a nested "data" key (the actual history array)
            if "data" in data and isinstance(data["data"], list):
                history = data["data"]
            # If the dict itself contains history items (unlikely but possible)
            elif "recordsFiltered" in data or "recordsTotal" in data:
                # This is the wrapper, try to find the actual data
                history = data.get("data", [])
        elif isinstance(data, list):
            history = data

        # Filter by date range in Python if dates were provided
        if start_timestamp or end_timestamp:
            filtered_history = []
            for item in history:
                # Use 'date' field (Unix timestamp) for filtering
                item_date = item.get("date", 0)
                if not item_date:
                    # Fallback to 'started' if 'date' is not available
                    item_date = item.get("started", 0)

                # Check if item is within date range
                if start_timestamp and item_date < start_timestamp:
                    continue
                if end_timestamp and item_date > end_timestamp:
                    continue

                filtered_history.append(item)
            return filtered_history

        return history

    def get_user_stats(
        self,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        days: int = 365,
    ) -> Dict:
        """Get statistics for a user"""
        params = {"days": days}

        if user_id:
            params["user_id"] = user_id
        elif username:
            params["user"] = username

        return self._request("get_user_watch_time_stats", params)

    def get_user_most_watched(
        self,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        days: int = 365,
        count: int = 10,
    ) -> List[Dict]:
        """Get most watched content for a user"""
        params = {"days": days, "count": count}

        if user_id:
            params["user_id"] = user_id
        elif username:
            params["user"] = username

        return self._request("get_user_watch_time_stats", params)

    def get_user_player_stats(
        self,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        days: int = 365,
    ) -> List[Dict]:
        """Get player/device statistics for a user"""
        params = {"days": days}

        if user_id:
            params["user_id"] = user_id
        elif username:
            params["user"] = username

        return self._request("get_user_player_stats", params)

    def get_user_platform_stats(
        self,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        days: int = 365,
    ) -> List[Dict]:
        """Get platform statistics for a user"""
        params = {"days": days}

        if user_id:
            params["user_id"] = user_id
        elif username:
            params["user"] = username

        return self._request("get_user_platform_stats", params)

    def get_image_url(self, img_path: str, width: Optional[int] = None, height: Optional[int] = None) -> str:
        """Get the URL for a Plex image proxied through Tautulli
        
        Args:
            img_path: The Plex image path (e.g., /library/metadata/12345/thumb/1234567890)
            width: Optional width to resize the image
            height: Optional height to resize the image
            
        Returns:
            Full URL to fetch the image through Tautulli's pms_image_proxy
        """
        params = {
            "apikey": self.api_key,
            "cmd": "pms_image_proxy",
            "img": img_path,
        }
        if width:
            params["width"] = width
        if height:
            params["height"] = height
            
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.base_url}/api/v2?{query_string}"

    def get_metadata(self, rating_key: str) -> Optional[Dict]:
        """Get metadata for a media item by rating_key
        
        Uses Tautulli's get_metadata command to fetch genres, actors, directors, etc.
        """
        try:
            params = {"rating_key": rating_key}
            data = self._request("get_metadata", params)
            
            if data:
                # Extract genres, actors, directors from Tautulli metadata
                genres = data.get("genres", [])
                actors = data.get("actors", [])
                directors = data.get("directors", [])
                
                return {
                    "genres": genres if isinstance(genres, list) else [],
                    "actors": actors if isinstance(actors, list) else [],
                    "directors": directors if isinstance(directors, list) else [],
                }
        except Exception:
            pass
        return None
