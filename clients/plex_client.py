import requests
from typing import List, Dict, Optional
from datetime import datetime
from xml.etree import ElementTree as ET


class PlexClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update(
            {"X-Plex-Token": self.token, "Accept": "application/json"}
        )

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a GET request to Plex API"""
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def _get_xml(self, endpoint: str, params: Optional[Dict] = None) -> ET.Element:
        """Make a GET request that returns XML"""
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return ET.fromstring(response.content)

    def get_users(self) -> List[Dict]:
        """Get all users from Plex"""
        try:
            data = self._get("/api/users")
            return data.get("MediaContainer", {}).get("User", [])
        except:
            # Fallback to XML API
            root = self._get_xml("/api/users")
            users = []
            for user in root.findall(".//User"):
                users.append(
                    {
                        "id": user.get("id"),
                        "username": user.get("username"),
                        "title": user.get("title"),
                        "thumb": user.get("thumb"),
                        "email": user.get("email"),
                    }
                )
            return users

    def get_libraries(self) -> List[Dict]:
        """Get all libraries"""
        data = self._get("/library/sections")
        return data.get("MediaContainer", {}).get("Directory", [])

    def get_user_watch_history(
        self, user_id: str, start_date: str, end_date: str
    ) -> List[Dict]:
        """Get watch history for a user (via Tautulli, but keeping interface consistent)"""
        # This would typically be done via Tautulli, but we can get some data from Plex
        # For now, return empty - Tautulli client will handle this
        return []

    def get_metadata(self, rating_key: str) -> Optional[Dict]:
        """Get metadata for a media item by rating_key"""
        try:
            # Try JSON API first
            try:
                data = self._get(f"/library/metadata/{rating_key}")
                media_container = data.get("MediaContainer", {})
                metadata = media_container.get("Metadata", [])
                if metadata:
                    item = metadata[0]
                    # Extract genres, actors, directors
                    genres = []
                    actors = []
                    directors = []
                    
                    # Handle genres
                    genre_elements = item.get("Genre", [])
                    if isinstance(genre_elements, list):
                        genres = [g.get("tag", "") for g in genre_elements if g.get("tag")]
                    elif isinstance(genre_elements, dict):
                        genres = [genre_elements.get("tag", "")]
                    
                    # Handle actors
                    role_elements = item.get("Role", [])
                    if isinstance(role_elements, list):
                        actors = [r.get("tag", "") for r in role_elements if r.get("tag")]
                    elif isinstance(role_elements, dict):
                        actors = [role_elements.get("tag", "")]
                    
                    # Handle directors
                    director_elements = item.get("Director", [])
                    if isinstance(director_elements, list):
                        directors = [d.get("tag", "") for d in director_elements if d.get("tag")]
                    elif isinstance(director_elements, dict):
                        directors = [director_elements.get("tag", "")]
                    
                    return {
                        "genres": genres,
                        "actors": actors,
                        "directors": directors,
                    }
            except Exception:
                # Fallback to XML API
                root = self._get_xml(f"/library/metadata/{rating_key}")
                item = root.find(".//Video") or root.find(".//Directory")
                if item is not None:
                    genres = [g.get("tag", "") for g in item.findall(".//Genre") if g.get("tag")]
                    actors = [r.get("tag", "") for r in item.findall(".//Role") if r.get("tag")]
                    directors = [d.get("tag", "") for d in item.findall(".//Director") if d.get("tag")]
                    
                    return {
                        "genres": genres,
                        "actors": actors,
                        "directors": directors,
                    }
        except Exception:
            # If fetching fails, return None
            return None
        return None
