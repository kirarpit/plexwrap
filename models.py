from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime


class User(BaseModel):
    id: str
    username: str
    title: Optional[str] = None
    thumb: Optional[str] = None


class Insight(BaseModel):
    title: str
    description: str
    value: str
    icon: Optional[str] = None
    category: str
    llm_generated: Optional[bool] = False  # Whether description was LLM-generated


class GenreStat(BaseModel):
    genre: str
    watch_time: int  # in minutes
    count: int
    percentage: float


class ActorStat(BaseModel):
    name: str
    watch_time: int
    count: int


class DeviceStat(BaseModel):
    device: str
    watch_time: int
    percentage: float


class BingeSession(BaseModel):
    date: str
    duration: int  # in minutes
    content: List[str]
    episodes: int


class WrapData(BaseModel):
    user: User
    period: Dict[str, str]

    # Core stats
    total_watch_time: int  # in minutes
    total_items_watched: int
    total_episodes_watched: int
    total_movies_watched: int

    # Interesting insights
    insights: List[Insight]

    # Detailed stats
    top_genres: List[GenreStat]
    top_actors: List[ActorStat]
    top_directors: List[ActorStat]
    top_content: List[Dict]
    devices: List[DeviceStat]
    platforms: List[DeviceStat]

    # Binge watching
    longest_binge: Optional[BingeSession] = None
    binge_sessions: List[BingeSession]

    # Legacy fields (kept for backwards compatibility)
    total_requests: int = 0
    approved_requests: int = 0
    most_requested_genre: Optional[str] = None

    # Fun facts (deprecated - cards replace this)
    fun_facts: List[str]

    # LLM-generated card deck
    cards: Optional[List[Dict]] = None

    # Raw data with cross-user comparisons
    raw_data: Optional[Dict] = None
