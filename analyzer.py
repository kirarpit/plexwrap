from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import asyncio
from clients import PlexClient, TautulliClient, OverseerrClient, ImageGenerationClient
from clients.llm_client import LLMClient
from models import (
    WrapData,
    Insight,
    GenreStat,
    ActorStat,
    DeviceStat,
    BingeSession,
    User,
)
from config import Settings


class WrapAnalyzer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.plex = PlexClient(settings.plex_url, settings.plex_token)
        self.tautulli = TautulliClient(settings.tautulli_url, settings.tautulli_api_key)
        self.overseerr = OverseerrClient(
            settings.overseerr_url, settings.overseerr_api_key
        )
        self.llm = LLMClient(
            api_key=settings.openai_api_key,
            enabled=settings.use_llm,
            name_mappings=settings.name_mappings,
            custom_prompt_context=settings.custom_prompt_context,
        )
        self.image_gen = ImageGenerationClient(
            api_key=settings.google_image_api_key,
            enabled=settings.use_image_generation,
            name_mappings=settings.name_mappings,
        )

    def format_duration(self, minutes: int) -> str:
        """Format minutes into human-readable duration"""
        if minutes < 60:
            return f"{minutes} minutes"
        hours = minutes // 60
        mins = minutes % 60
        if hours < 24:
            return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
        days = hours // 24
        hours = hours % 24
        return f"{days}d {hours}h" if hours > 0 else f"{days} days"

    def calculate_days_between(self, start: str, end: str) -> int:
        """Calculate days between two dates"""
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
        return (end_date - start_date).days

    def analyze_history(
        self, history: List[Dict], start_date: str, end_date: str
    ) -> Dict:
        """Analyze watch history and extract insights"""
        if not history:
            return {}

        total_watch_time = 0
        items_watched = set()
        episodes_watched = 0
        movies_watched = 0

        genres = Counter()
        actors = Counter()
        directors = Counter()
        content_ratings = Counter()
        devices = Counter()
        platforms = Counter()

        # Group by date for binge detection
        watches_by_date = defaultdict(list)

        # Track repeat watches (content watched multiple times)
        content_watch_count = Counter()  # title -> count
        content_watch_times = defaultdict(list)  # title -> list of timestamps

        # Track seasonal patterns (by month)
        watches_by_month = defaultdict(
            lambda: {"time": 0, "count": 0, "genres": Counter()}
        )

        # Track time-of-day patterns (hour of day: 0-23)
        watches_by_hour = defaultdict(lambda: {"time": 0, "count": 0})

        # Track day-of-week patterns (Monday=0, Sunday=6)
        watches_by_weekday = defaultdict(lambda: {"time": 0, "count": 0})

        # Track daily watch times for consistency analysis
        daily_watch_times = []  # List of minutes watched per day

        # Track continuous sessions (for longest stretch detection)
        watch_sessions = []  # List of (start_time, end_time, duration_min)

        for item in history:
            # Tautulli returns duration in SECONDS (not milliseconds!)
            # Try multiple field names for duration
            duration = item.get("duration", 0) or item.get("media_duration", 0) or 0
            # For watched duration, use play_duration (in seconds) or calculate from stopped - started
            watched_duration = (
                item.get("play_duration", 0)
                or (item.get("stopped", 0) - item.get("started", 0))
                if (item.get("stopped", 0) and item.get("started", 0))
                else 0 or item.get("watched_duration", 0) or 0
            )

            # Convert seconds to minutes
            duration_min = duration / 60 if duration > 0 else 0
            watched_min = watched_duration / 60 if watched_duration > 0 else 0

            # Count if watched - be more lenient with criteria
            # Tautulli marks items as watched if they've been watched at least once
            watched_status = item.get("watched_status", 0)
            # Also check if there's a stopped time (means it was played)
            has_stopped = item.get("stopped", 0) > 0

            # Count if: marked as watched, or has significant watch time (>50% or >5 minutes)
            is_watched = (
                watched_status == 1
                or has_stopped
                or (
                    duration_min > 0
                    and watched_min > 0
                    and (watched_min / duration_min) >= 0.5
                )
                or (watched_min >= 5)  # At least 5 minutes watched
            )

            if is_watched and watched_min > 0:
                total_watch_time += watched_min

                media_type = item.get("media_type", "") or item.get("type", "")
                title = item.get("title", "") or item.get("full_title", "")
                grandparent_title = item.get("grandparent_title", "") or item.get(
                    "parent_title", ""
                )
                show_title = grandparent_title or title

                # Filter out music tracks - only count TV shows and movies
                if media_type == "track":
                    continue  # Skip music tracks

                if media_type == "episode" or "episode" in str(media_type).lower():
                    episodes_watched += 1
                    items_watched.add(show_title)
                elif media_type == "movie" or "movie" in str(media_type).lower():
                    movies_watched += 1
                    items_watched.add(title)
                else:
                    # Fallback: treat as show if has grandparent_title
                    if grandparent_title:
                        episodes_watched += 1
                        items_watched.add(show_title)
                    else:
                        movies_watched += 1
                        items_watched.add(title)

                # Extract genres (Tautulli may return as string, list, list of dicts, or nested in media_info)
                item_genres = []
                # Check direct field first
                if "genres" in item:
                    item_genres = item.get("genres", []) or []
                # Check nested media_info structure if direct field is empty
                if (
                    not item_genres
                    and "media_info" in item
                    and isinstance(item.get("media_info"), dict)
                ):
                    media_info = item.get("media_info", {})
                    item_genres = media_info.get("genres", []) or []
                # Handle list of dictionaries (Tautulli format: [{"tag": "Action"}, ...])
                if (
                    item_genres
                    and isinstance(item_genres, list)
                    and len(item_genres) > 0
                ):
                    if isinstance(item_genres[0], dict):
                        item_genres = [
                            g.get("tag", "") for g in item_genres if g.get("tag")
                        ]
                # Check if it's a string
                elif isinstance(item_genres, str):
                    item_genres = [
                        g.strip() for g in item_genres.split(",") if g.strip()
                    ]
                # If still empty, try to fetch from Plex using rating_key
                if not item_genres and item.get("rating_key"):
                    try:
                        plex_metadata = self.plex.get_metadata(
                            str(item.get("rating_key"))
                        )
                        if plex_metadata and plex_metadata.get("genres"):
                            item_genres = plex_metadata.get("genres", [])
                    except Exception:
                        pass  # Silently fail if Plex fetch fails

                for genre in item_genres:
                    if genre:
                        genres[genre] += watched_min

                # Extract actors (Tautulli format)
                item_actors = []
                # Check direct field first
                if "actors" in item:
                    item_actors = item.get("actors", []) or []
                # Check nested media_info structure if direct field is empty
                if (
                    not item_actors
                    and "media_info" in item
                    and isinstance(item.get("media_info"), dict)
                ):
                    media_info = item.get("media_info", {})
                    item_actors = media_info.get("actors", []) or []
                # Handle list of dictionaries (Tautulli format: [{"tag": "Actor Name"}, ...])
                if (
                    item_actors
                    and isinstance(item_actors, list)
                    and len(item_actors) > 0
                ):
                    if isinstance(item_actors[0], dict):
                        item_actors = [
                            a.get("tag", "") for a in item_actors if a.get("tag")
                        ]
                # Check if it's a string
                elif isinstance(item_actors, str):
                    item_actors = [
                        a.strip() for a in item_actors.split(",") if a.strip()
                    ]
                # If still empty, try to fetch from Plex using rating_key
                if not item_actors and item.get("rating_key"):
                    try:
                        plex_metadata = self.plex.get_metadata(
                            str(item.get("rating_key"))
                        )
                        if plex_metadata and plex_metadata.get("actors"):
                            item_actors = plex_metadata.get("actors", [])
                    except Exception:
                        pass  # Silently fail if Plex fetch fails

                for actor in item_actors[:5]:  # Top 5 actors
                    if actor:
                        actors[actor] += watched_min

                # Extract directors
                item_directors = []
                # Check direct field first
                if "directors" in item:
                    item_directors = item.get("directors", []) or []
                # Check nested media_info structure if direct field is empty
                if (
                    not item_directors
                    and "media_info" in item
                    and isinstance(item.get("media_info"), dict)
                ):
                    media_info = item.get("media_info", {})
                    item_directors = media_info.get("directors", []) or []
                # Handle list of dictionaries (Tautulli format: [{"tag": "Director Name"}, ...])
                if (
                    item_directors
                    and isinstance(item_directors, list)
                    and len(item_directors) > 0
                ):
                    if isinstance(item_directors[0], dict):
                        item_directors = [
                            d.get("tag", "") for d in item_directors if d.get("tag")
                        ]
                # Check if it's a string
                elif isinstance(item_directors, str):
                    item_directors = [
                        d.strip() for d in item_directors.split(",") if d.strip()
                    ]
                # If still empty, try to fetch from Plex using rating_key
                if not item_directors and item.get("rating_key"):
                    try:
                        plex_metadata = self.plex.get_metadata(
                            str(item.get("rating_key"))
                        )
                        if plex_metadata and plex_metadata.get("directors"):
                            item_directors = plex_metadata.get("directors", [])
                    except Exception:
                        pass  # Silently fail if Plex fetch fails

                for director in item_directors:
                    if director:
                        directors[director] += watched_min

                # Devices and platforms
                player = item.get("player", "") or item.get("platform", "")
                platform = item.get("platform", "") or item.get("platform_name", "")
                if player:
                    devices[player] += watched_min
                if platform and platform != player:
                    platforms[platform] += watched_min

                # Track content for repeat detection
                # Only track movies for repeat watches - TV episodes are not re-watches
                # (watching different episodes of a show is normal viewing, not re-watching)
                # Check multiple indicators to detect episodes more reliably
                has_season_number = (
                    item.get("season_number") is not None
                    or item.get("parent_index") is not None
                )
                has_episode_number = (
                    item.get("episode_number") is not None
                    or item.get("index") is not None
                )
                is_episode = (
                    media_type == "episode"
                    or "episode" in str(media_type).lower()
                    or grandparent_title
                    or has_season_number
                    or has_episode_number
                )
                # Initialize content_key for watch sessions (use show_title for episodes, title for movies)
                content_key = show_title if is_episode else (title or "Unknown")

                # Only track movies (non-episodes) for repeat detection
                # Use title (not content_key) to ensure we're tracking the actual movie title
                if not is_episode and title:
                    # Only track movies for repeat detection
                    content_watch_count[title] += 1
                    # Track when it was watched
                    date_timestamp = item.get("date", 0) or item.get("started", 0)
                    if date_timestamp:
                        content_watch_times[title].append(date_timestamp)

                # Group by date (Tautulli uses Unix timestamps)
                date_timestamp = item.get("date", 0) or item.get("started", 0)
                started_ts = item.get("started", 0)

                if date_timestamp:
                    # Convert Unix timestamp to date string
                    try:
                        if isinstance(date_timestamp, (int, float)):
                            date_obj = datetime.fromtimestamp(date_timestamp)
                            date_str = date_obj.strftime("%Y-%m-%d")
                            month_key = date_obj.strftime("%Y-%m")  # YYYY-MM format

                            # Track day of week (Monday=0, Sunday=6)
                            weekday = date_obj.weekday()
                            watches_by_weekday[weekday]["time"] += watched_min
                            watches_by_weekday[weekday]["count"] += 1

                            # Track seasonal patterns
                            watches_by_month[month_key]["time"] += watched_min
                            watches_by_month[month_key]["count"] += 1
                            for genre in item_genres:
                                if genre:
                                    watches_by_month[month_key]["genres"][
                                        genre
                                    ] += watched_min
                        else:
                            # If it's already a string, try to parse it
                            date_str = (
                                str(date_timestamp).split(" ")[0]
                                if " " in str(date_timestamp)
                                else str(date_timestamp)
                            )
                        watches_by_date[date_str].append(item)

                        # Track time-of-day patterns (using started timestamp)
                        if started_ts and isinstance(started_ts, (int, float)):
                            try:
                                start_dt = datetime.fromtimestamp(started_ts)
                                hour = start_dt.hour
                                watches_by_hour[hour]["time"] += watched_min
                                watches_by_hour[hour]["count"] += 1
                            except (ValueError, OSError, TypeError):
                                pass

                        # Track watch sessions for continuous stretch detection
                        stopped_ts = item.get("stopped", 0) or started_ts
                        if started_ts and stopped_ts:
                            watch_sessions.append(
                                {
                                    "start": started_ts,
                                    "end": stopped_ts,
                                    "duration": watched_min,
                                    "title": content_key,
                                }
                            )
                    except (ValueError, OSError, TypeError):
                        # If conversion fails, skip date grouping for this item
                        pass

        # Calculate genre percentages
        total_genre_time = sum(genres.values())
        genre_stats = []
        for genre, time in genres.most_common(10):
            genre_stats.append(
                GenreStat(
                    genre=genre,
                    watch_time=int(round(time)),
                    count=sum(1 for item in history if genre in item.get("genres", [])),
                    percentage=(
                        (time / total_genre_time * 100) if total_genre_time > 0 else 0
                    ),
                )
            )

        # Top actors
        actor_stats = [
            ActorStat(
                name=name,
                watch_time=int(round(time)),
                count=sum(1 for item in history if name in item.get("actors", [])),
            )
            for name, time in actors.most_common(10)
        ]

        # Top directors
        director_stats = [
            ActorStat(
                name=name,
                watch_time=int(round(time)),
                count=sum(1 for item in history if name in item.get("directors", [])),
            )
            for name, time in directors.most_common(10)
        ]

        # Device stats
        total_device_time = sum(devices.values())
        device_stats = [
            DeviceStat(
                device=device,
                watch_time=int(round(time)),
                percentage=(
                    (time / total_device_time * 100) if total_device_time > 0 else 0
                ),
            )
            for device, time in devices.most_common(10)
        ]

        # Platform stats
        total_platform_time = sum(platforms.values())
        platform_stats = [
            DeviceStat(
                device=platform,
                watch_time=int(round(time)),
                percentage=(
                    (time / total_platform_time * 100) if total_platform_time > 0 else 0
                ),
            )
            for platform, time in platforms.most_common(10)
        ]

        # Detect binge sessions
        binge_sessions = self._detect_binge_sessions(watches_by_date)

        # Find repeat watchers
        repeat_watches = {
            title: count for title, count in content_watch_count.items() if count > 1
        }

        # Find longest continuous session
        longest_session = self._find_longest_continuous_session(watch_sessions)

        # Find day with most watching
        day_with_most = self._find_day_with_most_watching(watches_by_date)

        # Calculate daily watch times for consistency analysis
        for date, items in watches_by_date.items():
            daily_total = 0
            for item in items:
                watched_duration = (
                    item.get("play_duration", 0)
                    or (item.get("stopped", 0) - item.get("started", 0))
                    if (item.get("stopped", 0) and item.get("started", 0))
                    else 0 or item.get("watched_duration", 0) or 0
                )
                daily_total += watched_duration / 60  # Convert to minutes
            daily_watch_times.append(daily_total)

        # Analyze time-of-day patterns
        time_of_day_analysis = self._analyze_time_of_day(watches_by_hour)

        # Analyze day-of-week patterns
        day_of_week_analysis = self._analyze_day_of_week(watches_by_weekday)

        # Analyze consistency
        consistency_analysis = self._analyze_consistency(
            daily_watch_times, start_date, end_date
        )

        return {
            "total_watch_time": int(round(total_watch_time)),
            "total_items_watched": len(items_watched),
            "total_episodes_watched": episodes_watched,
            "total_movies_watched": movies_watched,
            "genres": genre_stats,
            "actors": actor_stats,
            "directors": director_stats,
            "devices": device_stats,
            "platforms": platform_stats,
            "binge_sessions": binge_sessions,
            "history": history,
            "repeat_watches": repeat_watches,
            "watches_by_month": dict(watches_by_month),
            "longest_session": longest_session,
            "day_with_most": day_with_most,
            "time_of_day": time_of_day_analysis,
            "day_of_week": day_of_week_analysis,
            "consistency": consistency_analysis,
        }

    def _detect_binge_sessions(
        self, watches_by_date: Dict[str, List[Dict]]
    ) -> List[BingeSession]:
        """Detect binge watching sessions (multiple episodes/movies in one day)"""
        binge_sessions = []

        for date, items in watches_by_date.items():
            # Group by show/movie
            by_content = defaultdict(list)
            for item in items:
                title = item.get("grandparent_title") or item.get("title", "")
                by_content[title].append(item)

            # Find days with significant watching
            # Duration is in seconds, convert to minutes
            total_duration = 0
            for item in items:
                watched_duration = (
                    item.get("play_duration", 0)
                    or (item.get("stopped", 0) - item.get("started", 0))
                    if (item.get("stopped", 0) and item.get("started", 0))
                    else 0 or item.get("watched_duration", 0) or 0
                )
                total_duration += watched_duration / 60  # Convert seconds to minutes

            # Consider it a binge if more than 2 hours in a day
            if total_duration > 120:
                episodes = sum(
                    1 for item in items if item.get("media_type") == "episode"
                )
                content_list = list(by_content.keys())

                binge_sessions.append(
                    BingeSession(
                        date=date,
                        duration=int(round(total_duration)),
                        content=content_list,
                        episodes=episodes,
                    )
                )

        # Sort by duration
        binge_sessions.sort(key=lambda x: x.duration, reverse=True)
        return binge_sessions

    def _find_longest_continuous_session(
        self, watch_sessions: List[Dict]
    ) -> Optional[Dict]:
        """Find the longest continuous watching session"""
        if not watch_sessions:
            return None

        # Sort sessions by start time
        sorted_sessions = sorted(watch_sessions, key=lambda x: x.get("start", 0))

        longest = None
        max_duration = 0

        # Group sessions that are close together (within 30 minutes)
        current_group = []
        for session in sorted_sessions:
            if not current_group:
                current_group = [session]
            else:
                last_end = current_group[-1].get("end", 0)
                current_start = session.get("start", 0)
                # If sessions are within 30 minutes, consider them continuous
                if current_start - last_end <= 1800:  # 30 minutes in seconds
                    current_group.append(session)
                else:
                    # Calculate total duration of this group
                    group_duration = sum(s.get("duration", 0) for s in current_group)
                    if group_duration > max_duration:
                        max_duration = group_duration
                        longest = {
                            "duration": int(round(group_duration)),
                            "start": current_group[0].get("start", 0),
                            "end": current_group[-1].get("end", 0),
                            "items": len(current_group),
                        }
                    current_group = [session]

        # Check last group
        if current_group:
            group_duration = sum(s.get("duration", 0) for s in current_group)
            if group_duration > max_duration:
                max_duration = group_duration
                longest = {
                    "duration": int(round(group_duration)),
                    "start": current_group[0].get("start", 0),
                    "end": current_group[-1].get("end", 0),
                    "items": len(current_group),
                }

        return longest

    def _find_day_with_most_watching(
        self, watches_by_date: Dict[str, List[Dict]]
    ) -> Optional[Dict]:
        """Find the day with the most watching time"""
        if not watches_by_date:
            return None

        max_time = 0
        best_day = None

        for date, items in watches_by_date.items():
            total_duration = 0
            for item in items:
                watched_duration = (
                    item.get("play_duration", 0)
                    or (item.get("stopped", 0) - item.get("started", 0))
                    if (item.get("stopped", 0) and item.get("started", 0))
                    else 0 or item.get("watched_duration", 0) or 0
                )
                total_duration += watched_duration / 60  # Convert to minutes

            if total_duration > max_time:
                max_time = total_duration
                best_day = {
                    "date": date,
                    "duration": int(round(total_duration)),
                    "items": len(items),
                }

        return best_day

    def _get_season(self, month: int) -> str:
        """Get season name from month (1-12)"""
        if month in [12, 1, 2]:
            return "Winter"
        elif month in [3, 4, 5]:
            return "Spring"
        elif month in [6, 7, 8]:
            return "Summer"
        else:
            return "Fall"

    def _analyze_seasonal_patterns(self, watches_by_month: Dict) -> Dict:
        """Analyze viewing patterns by season"""
        if not watches_by_month:
            return {}

        seasonal_data = defaultdict(
            lambda: {"time": 0, "count": 0, "genres": Counter()}
        )

        for month_key, data in watches_by_month.items():
            try:
                year, month = map(int, month_key.split("-"))
                season = self._get_season(month)
                seasonal_data[season]["time"] += data["time"]
                seasonal_data[season]["count"] += data["count"]
                for genre, time in data["genres"].items():
                    seasonal_data[season]["genres"][genre] += time
            except (ValueError, KeyError):
                continue

        # Find most active season
        most_active = (
            max(seasonal_data.items(), key=lambda x: x[1]["time"])
            if seasonal_data
            else None
        )

        # Round numbers and convert Counter to dict with rounded values
        rounded_seasonal_data = {}
        for season, data in seasonal_data.items():
            rounded_genres = {
                genre: round(time, 2) for genre, time in data["genres"].items()
            }
            rounded_seasonal_data[season] = {
                "time": round(data["time"], 2),
                "count": data["count"],
                "genres": rounded_genres,
            }

        return {
            "by_season": rounded_seasonal_data,
            "most_active": most_active[0] if most_active else None,
            "most_active_time": (
                int(round(most_active[1]["time"])) if most_active else 0
            ),
        }

    def _analyze_time_of_day(self, watches_by_hour: Dict) -> Dict:
        """Analyze viewing patterns by time of day"""
        if not watches_by_hour:
            return {}

        # Group hours into time periods
        time_periods = {
            "morning": (6, 12),  # 6 AM - 12 PM
            "afternoon": (12, 18),  # 12 PM - 6 PM
            "evening": (18, 22),  # 6 PM - 10 PM
            "night": (22, 6),  # 10 PM - 6 AM (wraps around)
        }

        period_totals = {
            period: {"time": 0, "count": 0} for period in time_periods.keys()
        }

        # Calculate totals by period
        for hour, data in watches_by_hour.items():
            hour_int = int(hour)
            for period, (start, end) in time_periods.items():
                if period == "night":
                    # Handle wrap-around for night (22-6)
                    if hour_int >= start or hour_int < end:
                        period_totals[period]["time"] += data["time"]
                        period_totals[period]["count"] += data["count"]
                else:
                    if start <= hour_int < end:
                        period_totals[period]["time"] += data["time"]
                        period_totals[period]["count"] += data["count"]

        # Find most active time period
        most_active_period = (
            max(period_totals.items(), key=lambda x: x[1]["time"])
            if period_totals
            else None
        )

        # Find peak hour
        peak_hour = (
            max(watches_by_hour.items(), key=lambda x: x[1]["time"])
            if watches_by_hour
            else None
        )

        return {
            "by_period": {
                period: {
                    "time": round(data["time"], 2),
                    "count": data["count"],
                    "percentage": (
                        round(
                            data["time"]
                            / sum(p["time"] for p in period_totals.values())
                            * 100,
                            2,
                        )
                        if sum(p["time"] for p in period_totals.values()) > 0
                        else 0
                    ),
                }
                for period, data in period_totals.items()
            },
            "most_active_period": most_active_period[0] if most_active_period else None,
            "most_active_period_time": (
                int(round(most_active_period[1]["time"])) if most_active_period else 0
            ),
            "peak_hour": peak_hour[0] if peak_hour else None,
            "peak_hour_time": (int(round(peak_hour[1]["time"])) if peak_hour else 0),
            "by_hour": {
                str(hour): {"time": round(data["time"], 2), "count": data["count"]}
                for hour, data in sorted(watches_by_hour.items())
            },
        }

    def _analyze_day_of_week(self, watches_by_weekday: Dict) -> Dict:
        """Analyze viewing patterns by day of week"""
        if not watches_by_weekday:
            return {}

        weekday_names = {
            0: "Monday",
            1: "Tuesday",
            2: "Wednesday",
            3: "Thursday",
            4: "Friday",
            5: "Saturday",
            6: "Sunday",
        }

        # Calculate totals
        weekday_totals = {}
        for weekday, data in watches_by_weekday.items():
            weekday_totals[weekday] = {
                "time": round(data["time"], 2),
                "count": data["count"],
                "name": weekday_names.get(int(weekday), "Unknown"),
            }

        # Find most active day
        most_active_day = (
            max(watches_by_weekday.items(), key=lambda x: x[1]["time"])
            if watches_by_weekday
            else None
        )

        # Calculate percentages
        total_time = sum(data["time"] for data in weekday_totals.values())
        for weekday in weekday_totals:
            weekday_totals[weekday]["percentage"] = (
                round(weekday_totals[weekday]["time"] / total_time * 100, 2)
                if total_time > 0
                else 0
            )

        return {
            "by_weekday": {
                weekday_names.get(int(day), f"Day_{day}"): data
                for day, data in sorted(weekday_totals.items())
            },
            "most_active_day": (
                weekday_names.get(int(most_active_day[0]), "Unknown")
                if most_active_day
                else None
            ),
            "most_active_day_time": (
                int(round(most_active_day[1]["time"])) if most_active_day else 0
            ),
        }

    def _analyze_consistency(
        self, daily_watch_times: List[float], start_date: str, end_date: str
    ) -> Dict:
        """Analyze viewing consistency and regularity"""
        if not daily_watch_times:
            return {}

        import statistics

        # Calculate basic stats
        total_days = self.calculate_days_between(start_date, end_date) + 1
        days_with_watching = len([t for t in daily_watch_times if t > 0])
        days_without_watching = total_days - days_with_watching

        if not daily_watch_times:
            return {
                "consistency_score": 0,
                "regularity": "no_data",
                "average_daily_minutes": 0,
                "days_with_watching": 0,
                "days_without_watching": total_days,
                "watch_frequency_percentage": 0,
            }

        avg_daily = statistics.mean(daily_watch_times)

        # Calculate consistency score (0-100)
        # Based on: frequency of watching + regularity of watch time
        watch_frequency = (
            (days_with_watching / total_days) * 100 if total_days > 0 else 0
        )

        # Regularity: lower standard deviation = more regular
        if len(daily_watch_times) > 1:
            std_dev = statistics.stdev(daily_watch_times)
            # Normalize: lower std dev relative to mean = more consistent
            # If mean is 0, consistency is 0
            if avg_daily > 0:
                coefficient_of_variation = std_dev / avg_daily
                # Lower CV = more consistent (invert and scale to 0-100)
                regularity_score = max(
                    0, min(100, 100 - (coefficient_of_variation * 50))
                )
            else:
                regularity_score = 0
        else:
            regularity_score = 50  # Neutral if only one data point

        # Combined consistency score (weighted average)
        consistency_score = watch_frequency * 0.6 + regularity_score * 0.4

        # Determine regularity label
        if consistency_score >= 80:
            regularity = "very_consistent"
        elif consistency_score >= 60:
            regularity = "consistent"
        elif consistency_score >= 40:
            regularity = "moderate"
        elif consistency_score >= 20:
            regularity = "sporadic"
        else:
            regularity = "irregular"

        # Find longest streak without watching
        longest_gap = 0
        current_gap = 0
        for time in daily_watch_times:
            if time == 0:
                current_gap += 1
                longest_gap = max(longest_gap, current_gap)
            else:
                current_gap = 0

        # Find longest streak of watching
        longest_streak = 0
        current_streak = 0
        for time in daily_watch_times:
            if time > 0:
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
            else:
                current_streak = 0

        return {
            "consistency_score": round(consistency_score, 2),
            "regularity": regularity,
            "average_daily_minutes": round(avg_daily, 2),
            "days_with_watching": days_with_watching,
            "days_without_watching": days_without_watching,
            "watch_frequency_percentage": round(watch_frequency, 2),
            "longest_streak_days": longest_streak,
            "longest_gap_days": longest_gap,
            "standard_deviation": (
                round(statistics.stdev(daily_watch_times), 2)
                if len(daily_watch_times) > 1
                else 0
            ),
        }

    def get_top_content(self, history: List[Dict], limit: int = 10) -> List[Dict]:
        """Get top watched content"""
        content_ratings = Counter()

        for item in history:
            # Skip music tracks
            if item.get("media_type") == "track":
                continue

            title = item.get("grandparent_title") or item.get("title", "")
            if title:
                # Duration is in seconds, convert to minutes
                watched_duration = (
                    item.get("play_duration", 0)
                    or (item.get("stopped", 0) - item.get("started", 0))
                    if (item.get("stopped", 0) and item.get("started", 0))
                    else 0 or item.get("watched_duration", 0) or 0
                )
                duration_min = watched_duration / 60 if watched_duration > 0 else 0
                content_ratings[title] += duration_min

        top_content = []
        for title, time in content_ratings.most_common(limit):
            # Find the item to get more details
            item_details = next(
                (
                    item
                    for item in history
                    if (item.get("grandparent_title") or item.get("title")) == title
                ),
                {},
            )
            top_content.append(
                {
                    "title": title,
                    "watch_time": int(round(time)),
                    "thumb": item_details.get("thumb", ""),
                    "year": item_details.get("year", ""),
                    "media_type": item_details.get("media_type", ""),
                }
            )

        return top_content

    async def analyze_user_raw_data(self, username: str) -> Dict:
        """Analyze user data and return raw data without LLM generation"""
        # Get user info
        tautulli_users = self.tautulli.get_users()
        user_data = next(
            (
                u
                for u in tautulli_users
                if u.get("username") == username or u.get("friendly_name") == username
            ),
            None,
        )

        if not user_data:
            raise ValueError(f"User {username} not found")

        user_id = user_data.get("user_id")
        username = user_data.get("username") or user_data.get("friendly_name")

        # Get watch history
        history = self.tautulli.get_user_history(
            user_id=user_id,
            start_date=self.settings.start_date,
            end_date=self.settings.end_date,
        )

        # Analyze history
        analysis = self.analyze_history(
            history, self.settings.start_date, self.settings.end_date
        )

        # Get Overseerr data
        overseerr_users = self.overseerr.get_users()
        overseerr_user = next(
            (
                u
                for u in overseerr_users
                if u.get("username") == username or u.get("email") == username
            ),
            None,
        )
        overseerr_data = {}

        if overseerr_user:
            overseerr_data = self.overseerr.get_user_stats(overseerr_user["id"])
            requests = self.overseerr.get_user_requests(
                user_id=overseerr_user["id"],
                start_date=self.settings.start_date,
                end_date=self.settings.end_date,
            )

            # Find most requested genre
            request_genres = Counter()
            for req in requests:
                for genre in req.get("media", {}).get("genres", []):
                    request_genres[genre.get("name", "")] += 1
            if request_genres:
                overseerr_data["most_requested_genre"] = request_genres.most_common(1)[
                    0
                ][0]

        # Get top content
        top_content = self.get_top_content(history, limit=10)

        # Get binge sessions
        binge_sessions = analysis.get("binge_sessions", [])
        # Convert BingeSession objects to dicts for raw data
        longest_binge = None
        if binge_sessions:
            longest_binge_obj = binge_sessions[0]
            if isinstance(longest_binge_obj, BingeSession):
                longest_binge = {
                    "date": longest_binge_obj.date,
                    "duration": longest_binge_obj.duration,
                    "content": longest_binge_obj.content,
                    "episodes": longest_binge_obj.episodes,
                }
            else:
                longest_binge = longest_binge_obj

        # Convert binge sessions to dicts
        binge_sessions_dicts = []
        for bs in binge_sessions:
            if isinstance(bs, BingeSession):
                binge_sessions_dicts.append(
                    {
                        "date": bs.date,
                        "duration": bs.duration,
                        "content": bs.content,
                        "episodes": bs.episodes,
                    }
                )
            else:
                binge_sessions_dicts.append(bs)

        # Seasonal analysis
        seasonal_analysis = None
        if analysis.get("watches_by_month"):
            seasonal_analysis = self._analyze_seasonal_patterns(
                analysis.get("watches_by_month", {})
            )

        # Build raw data dict
        raw_data = {
            "username": username,
            "user_id": str(user_id),
            "user_data": user_data,
            "period_start": self.settings.start_date,
            "period_end": self.settings.end_date,
            "total_watch_time": analysis.get("total_watch_time", 0),
            "total_items_watched": analysis.get("total_items_watched", 0),
            "total_episodes_watched": analysis.get("total_episodes_watched", 0),
            "total_movies_watched": analysis.get("total_movies_watched", 0),
            "longest_binge": longest_binge,
            "binge_sessions": binge_sessions_dicts,
            "longest_session": analysis.get("longest_session"),
            "day_with_most": analysis.get("day_with_most"),
            "repeat_watches": dict(
                sorted(
                    analysis.get("repeat_watches", {}).items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            ),
            "genres": [
                {
                    "genre": g.genre,
                    "watch_time": g.watch_time,
                    "percentage": round(g.percentage, 2),
                }
                for g in analysis.get("genres", [])
            ],
            "top_content": top_content,
            "devices": [
                {
                    "device": d.device,
                    "watch_time": d.watch_time,
                    "percentage": round(d.percentage, 2),
                }
                for d in analysis.get("devices", [])
            ],
            "actors": [
                {"name": a.name, "watch_time": a.watch_time, "count": a.count}
                for a in analysis.get("actors", [])
            ],
            "directors": [
                {"name": d.name, "watch_time": d.watch_time, "count": d.count}
                for d in analysis.get("directors", [])
            ],
            "seasonal_analysis": seasonal_analysis,
            "time_of_day": analysis.get("time_of_day", {}),
            "day_of_week": analysis.get("day_of_week", {}),
            "consistency": analysis.get("consistency", {}),
            "overseerr_data": overseerr_data,
        }

        return raw_data

    async def generate_wrap_from_raw_data(
        self,
        username: str,
        raw_data: Dict,
        cross_user_insights: Dict = None,
        cross_analyzer=None,
        generate_images: bool = True,
    ) -> WrapData:
        """Generate wrap from raw data using LLM to create card deck"""
        user_data = raw_data["user_data"]
        user_id = raw_data["user_id"]

        # Generate LLM card deck (pass empty dict for cross_user_insights since we now use comparative_stats)
        # comparative_stats should already be in raw_data from pregenerate.py
        cards = await self.llm.generate_card_deck(raw_data, {})

        # Generate images for each card sequentially if image generation is enabled
        if cards and self.image_gen.enabled and generate_images:
            image_paths = await self.image_gen.generate_all_card_images(
                cards=cards,
                username=username,
            )
            # Add generated image paths to cards
            for i, (card, image_path) in enumerate(zip(cards, image_paths)):
                if image_path:
                    card["generated_image"] = image_path

        # Convert raw data to WrapData format
        genres = [
            GenreStat(
                genre=g["genre"],
                watch_time=g["watch_time"],
                count=0,  # We don't have count in raw data
                percentage=g["percentage"],
            )
            for g in raw_data.get("genres", [])[:5]
        ]

        actors = [
            ActorStat(
                name=a["name"],
                watch_time=a["watch_time"],
                count=a["count"],
            )
            for a in raw_data.get("actors", [])[:5]
        ]

        directors = [
            ActorStat(
                name=d["name"],
                watch_time=d["watch_time"],
                count=d["count"],
            )
            for d in raw_data.get("directors", [])[:5]
        ]

        devices = [
            DeviceStat(
                device=d["device"],
                watch_time=d["watch_time"],
                percentage=d["percentage"],
            )
            for d in raw_data.get("devices", [])[:5]
        ]

        platforms = []  # We can add this if needed

        return WrapData(
            user=User(
                id=user_id,
                username=username,
                title=user_data.get("friendly_name"),
                thumb=user_data.get("thumb"),
            ),
            period={
                "start": raw_data["period_start"],
                "end": raw_data["period_end"],
            },
            total_watch_time=raw_data["total_watch_time"],
            total_items_watched=raw_data["total_items_watched"],
            total_episodes_watched=raw_data["total_episodes_watched"],
            total_movies_watched=raw_data["total_movies_watched"],
            insights=[],  # Empty - cards replace this
            top_genres=genres,
            top_actors=actors,
            top_directors=directors,
            top_content=raw_data.get("top_content", []),
            devices=devices,
            platforms=platforms,
            longest_binge=raw_data.get("longest_binge"),
            binge_sessions=raw_data.get("binge_sessions", [])[:10],
            total_requests=raw_data.get("overseerr_data", {}).get("total_requests", 0),
            approved_requests=raw_data.get("overseerr_data", {}).get(
                "approved_requests", 0
            ),
            most_requested_genre=raw_data.get("overseerr_data", {}).get(
                "most_requested_genre"
            ),
            fun_facts=[],  # Empty - cards replace this
            llm_card_descriptions=None,  # Not used anymore
            cards=cards,  # LLM-generated card deck
            raw_data=raw_data,  # Store raw data for reference
        )

    async def generate_wrap(self, username: str) -> WrapData:
        """Generate a complete wrap for a user"""
        # Get user info
        tautulli_users = self.tautulli.get_users()
        user_data = next(
            (
                u
                for u in tautulli_users
                if u.get("username") == username or u.get("friendly_name") == username
            ),
            None,
        )

        if not user_data:
            raise ValueError(f"User {username} not found")

        user_id = user_data.get("user_id")
        username = user_data.get("username") or user_data.get("friendly_name")

        # Get watch history
        history = self.tautulli.get_user_history(
            user_id=user_id,
            start_date=self.settings.start_date,
            end_date=self.settings.end_date,
        )

        # Analyze history
        analysis = self.analyze_history(
            history, self.settings.start_date, self.settings.end_date
        )

        # Get Overseerr data
        overseerr_users = self.overseerr.get_users()
        overseerr_user = next(
            (
                u
                for u in overseerr_users
                if u.get("username") == username or u.get("email") == username
            ),
            None,
        )
        overseerr_data = {}

        if overseerr_user:
            overseerr_data = self.overseerr.get_user_stats(overseerr_user["id"])
            requests = self.overseerr.get_user_requests(
                user_id=overseerr_user["id"],
                start_date=self.settings.start_date,
                end_date=self.settings.end_date,
            )

            # Find most requested genre
            request_genres = Counter()
            for req in requests:
                for genre in req.get("media", {}).get("genres", []):
                    request_genres[genre.get("name", "")] += 1
            if request_genres:
                overseerr_data["most_requested_genre"] = request_genres.most_common(1)[
                    0
                ][0]

        # Get top content
        top_content = self.get_top_content(history, limit=10)

        # Get longest binge
        binge_sessions = analysis.get("binge_sessions", [])
        longest_binge = binge_sessions[0] if binge_sessions else None

        return WrapData(
            user=User(
                id=str(user_id),
                username=username,
                title=user_data.get("friendly_name"),
                thumb=user_data.get("thumb"),
            ),
            period={"start": self.settings.start_date, "end": self.settings.end_date},
            total_watch_time=analysis.get("total_watch_time", 0),
            total_items_watched=analysis.get("total_items_watched", 0),
            total_episodes_watched=analysis.get("total_episodes_watched", 0),
            total_movies_watched=analysis.get("total_movies_watched", 0),
            insights=[],  # Empty - cards replace this
            top_genres=analysis.get("genres", [])[:5],
            top_actors=analysis.get("actors", [])[:5],
            top_directors=analysis.get("directors", [])[:5],
            top_content=top_content,
            devices=analysis.get("devices", [])[:5],
            platforms=analysis.get("platforms", [])[:5],
            longest_binge=longest_binge,
            binge_sessions=binge_sessions[:10],
            total_requests=overseerr_data.get("total_requests", 0),
            approved_requests=overseerr_data.get("approved_requests", 0),
            most_requested_genre=overseerr_data.get("most_requested_genre"),
            fun_facts=[],  # Empty - cards replace this
            llm_card_descriptions=None,  # Not used anymore
        )
