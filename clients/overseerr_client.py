import requests
from typing import List, Dict, Optional
from datetime import datetime


class OverseerrClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {"X-Api-Key": self.api_key, "Content-Type": "application/json"}
        )

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a GET request to Overseerr API"""
        url = f"{self.base_url}/api/v1{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_users(self) -> List[Dict]:
        """Get all users from Overseerr"""
        data = self._get("/user")
        return data.get("results", [])

    def get_user_requests(
        self,
        user_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict]:
        """Get requests for a user"""
        params = {"take": 1000}

        if user_id:
            params["requestedBy"] = user_id

        data = self._get("/request", params)
        requests = data.get("results", [])

        # Filter by date if provided
        if start_date or end_date:
            filtered = []
            for req in requests:
                created = req.get("createdAt", "")
                if start_date and created < start_date:
                    continue
                if end_date and created > end_date:
                    continue
                filtered.append(req)
            return filtered

        return requests

    def get_user_stats(self, user_id: int) -> Dict:
        """Get statistics for a user"""
        # Overseerr doesn't have a direct stats endpoint, so we'll calculate from requests
        requests = self.get_user_requests(user_id)

        return {
            "total_requests": len(requests),
            "approved_requests": len([r for r in requests if r.get("status") == 2]),
            "pending_requests": len([r for r in requests if r.get("status") == 1]),
            "available_requests": len(
                [r for r in requests if r.get("media", {}).get("status") == 5]
            ),
        }
