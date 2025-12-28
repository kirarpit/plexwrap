"""
Cross-user analysis to generate comparative insights
"""

from typing import List, Dict, Optional
from collections import Counter, defaultdict
from datetime import datetime


class CrossUserAnalyzer:
    """Analyze all users together to generate cross-user comparisons"""

    def __init__(self):
        self.all_users_data = []

    def add_user_data(self, username: str, user_data: Dict):
        """Add a user's analyzed data"""
        self.all_users_data.append({"username": username, **user_data})

    def generate_cross_user_insights(self) -> Dict:
        """Generate cross-user comparisons and rankings"""
        if not self.all_users_data or len(self.all_users_data) < 2:
            return {}

        insights = {}

        # Watch time comparisons
        watch_times = [
            (u["username"], u.get("total_watch_time", 0)) for u in self.all_users_data
        ]
        watch_times.sort(key=lambda x: x[1], reverse=True)

        if watch_times:
            insights["watch_time_rankings"] = watch_times
            insights["most_watched_user"] = watch_times[0][0]
            insights["least_watched_user"] = watch_times[-1][0]
            insights["avg_watch_time"] = sum(w[1] for w in watch_times) / len(
                watch_times
            )
            insights["max_watch_time"] = watch_times[0][1]
            insights["min_watch_time"] = watch_times[-1][1]

        # Episode counts
        episode_counts = [
            (u["username"], u.get("total_episodes_watched", 0))
            for u in self.all_users_data
        ]
        episode_counts.sort(key=lambda x: x[1], reverse=True)
        if episode_counts:
            insights["episode_rankings"] = episode_counts
            insights["most_episodes_user"] = episode_counts[0][0]

        # Movie counts
        movie_counts = [
            (u["username"], u.get("total_movies_watched", 0))
            for u in self.all_users_data
        ]
        movie_counts.sort(key=lambda x: x[1], reverse=True)
        if movie_counts:
            insights["movie_rankings"] = movie_counts
            insights["most_movies_user"] = movie_counts[0][0]

        # Binge session comparisons
        binge_counts = [
            (u["username"], len(u.get("binge_sessions", [])))
            for u in self.all_users_data
        ]
        binge_counts.sort(key=lambda x: x[1], reverse=True)
        if binge_counts:
            insights["binge_rankings"] = binge_counts
            insights["most_binge_sessions_user"] = (
                binge_counts[0][0] if binge_counts[0][1] > 0 else None
            )

        # Longest binge comparisons
        longest_binges = []
        for u in self.all_users_data:
            longest_binge = u.get("longest_binge")
            if longest_binge:
                # Handle both dict and BingeSession object
                if isinstance(longest_binge, dict):
                    duration = longest_binge.get("duration", 0)
                else:
                    duration = getattr(longest_binge, "duration", 0)
                longest_binges.append((u["username"], duration))

        if longest_binges:
            longest_binges.sort(key=lambda x: x[1], reverse=True)
            insights["longest_binge_rankings"] = longest_binges
            insights["longest_binge_user"] = longest_binges[0][0]

        # Genre diversity
        genre_counts = []
        for u in self.all_users_data:
            genres = u.get("genres", [])
            genre_counts.append((u["username"], len(genres)))
        genre_counts.sort(key=lambda x: x[1], reverse=True)
        if genre_counts:
            insights["genre_diversity_rankings"] = genre_counts
            insights["most_diverse_genres_user"] = genre_counts[0][0]

        # Device usage diversity
        device_counts = []
        for u in self.all_users_data:
            devices = u.get("devices", [])
            device_counts.append((u["username"], len(devices)))
        device_counts.sort(key=lambda x: x[1], reverse=True)
        if device_counts:
            insights["device_diversity_rankings"] = device_counts

        # Total users
        insights["total_users"] = len(self.all_users_data)

        return insights

    def get_user_position(self, username: str, metric: str) -> Optional[Dict]:
        """Get a user's position/ranking for a specific metric"""
        insights = self.generate_cross_user_insights()

        rankings_key = f"{metric}_rankings"
        if rankings_key not in insights:
            return None

        rankings = insights[rankings_key]
        for i, (uname, value) in enumerate(rankings, 1):
            if uname == username:
                total = len(rankings)
                percentile = ((total - i + 1) / total) * 100 if total > 0 else 0
                return {
                    "rank": i,
                    "total": total,
                    "value": value,
                    "percentile": percentile,
                    "is_top": i == 1,
                    "is_bottom": i == total,
                }

        return None

    def get_user_comparative_stats(self, username: str) -> Dict:
        """Get comparative stats for a specific user without revealing other user names"""
        if not self.all_users_data or len(self.all_users_data) < 2:
            return {}

        stats = {}
        insights = self.generate_cross_user_insights()

        # Watch time stats
        watch_times_with_users = [
            (u.get("username"), u.get("total_watch_time", 0))
            for u in self.all_users_data
        ]
        user_watch_time = next(
            (
                u.get("total_watch_time", 0)
                for u in self.all_users_data
                if u.get("username") == username
            ),
            0,
        )
        if watch_times_with_users and user_watch_time > 0:
            watch_times_with_users.sort(key=lambda x: x[1], reverse=True)
            rank = next(
                (
                    i + 1
                    for i, (uname, _) in enumerate(watch_times_with_users)
                    if uname == username
                ),
                0,
            )
            total = len(watch_times_with_users)
            percentile = ((total - rank + 1) / total) * 100 if total > 0 else 0
            stats["watch_time"] = {
                "rank": rank,
                "total_users": total,
                "percentile": round(percentile, 1),
                "is_top": rank == 1,
                "is_bottom": rank == total,
                "above_average": user_watch_time > insights.get("avg_watch_time", 0),
                "average": round(insights.get("avg_watch_time", 0)),
                "max": insights.get("max_watch_time", 0),
                "min": insights.get("min_watch_time", 0),
            }

        # Episode stats
        episode_counts_with_users = [
            (u.get("username"), u.get("total_episodes_watched", 0))
            for u in self.all_users_data
        ]
        user_episodes = next(
            (
                u.get("total_episodes_watched", 0)
                for u in self.all_users_data
                if u.get("username") == username
            ),
            0,
        )
        if episode_counts_with_users and user_episodes > 0:
            episode_counts_with_users.sort(key=lambda x: x[1], reverse=True)
            rank = next(
                (
                    i + 1
                    for i, (uname, _) in enumerate(episode_counts_with_users)
                    if uname == username
                ),
                0,
            )
            total = len(episode_counts_with_users)
            percentile = ((total - rank + 1) / total) * 100 if total > 0 else 0
            avg_episodes = sum(count for _, count in episode_counts_with_users) / len(
                episode_counts_with_users
            )
            stats["episodes"] = {
                "rank": rank,
                "total_users": total,
                "percentile": round(percentile, 1),
                "is_top": rank == 1,
                "above_average": user_episodes > avg_episodes,
                "average": round(avg_episodes),
                "max": max(count for _, count in episode_counts_with_users),
            }

        # Movie stats
        movie_counts_with_users = [
            (u.get("username"), u.get("total_movies_watched", 0))
            for u in self.all_users_data
        ]
        user_movies = next(
            (
                u.get("total_movies_watched", 0)
                for u in self.all_users_data
                if u.get("username") == username
            ),
            0,
        )
        if movie_counts_with_users and user_movies > 0:
            movie_counts_with_users.sort(key=lambda x: x[1], reverse=True)
            rank = next(
                (
                    i + 1
                    for i, (uname, _) in enumerate(movie_counts_with_users)
                    if uname == username
                ),
                0,
            )
            total = len(movie_counts_with_users)
            percentile = ((total - rank + 1) / total) * 100 if total > 0 else 0
            avg_movies = sum(count for _, count in movie_counts_with_users) / len(
                movie_counts_with_users
            )
            stats["movies"] = {
                "rank": rank,
                "total_users": total,
                "percentile": round(percentile, 1),
                "is_top": rank == 1,
                "above_average": user_movies > avg_movies,
                "average": round(avg_movies),
                "max": max(count for _, count in movie_counts_with_users),
            }

        # Binge session stats
        binge_counts_with_users = [
            (u.get("username"), len(u.get("binge_sessions", [])))
            for u in self.all_users_data
        ]
        user_binges = next(
            (
                len(u.get("binge_sessions", []))
                for u in self.all_users_data
                if u.get("username") == username
            ),
            0,
        )
        if binge_counts_with_users and user_binges > 0:
            binge_counts_with_users.sort(key=lambda x: x[1], reverse=True)
            rank = next(
                (
                    i + 1
                    for i, (uname, _) in enumerate(binge_counts_with_users)
                    if uname == username
                ),
                0,
            )
            total = len(binge_counts_with_users)
            percentile = ((total - rank + 1) / total) * 100 if total > 0 else 0
            avg_binges = sum(count for _, count in binge_counts_with_users) / len(
                binge_counts_with_users
            )
            stats["binge_sessions"] = {
                "rank": rank,
                "total_users": total,
                "percentile": round(percentile, 1),
                "is_top": rank == 1,
                "above_average": user_binges > avg_binges,
                "average": round(avg_binges),
                "max": max(count for _, count in binge_counts_with_users),
            }

        # Longest binge stats
        longest_binges_with_users = []
        user_longest_binge = None
        for u in self.all_users_data:
            longest_binge = u.get("longest_binge")
            if longest_binge:
                if isinstance(longest_binge, dict):
                    duration = longest_binge.get("duration", 0)
                else:
                    duration = getattr(longest_binge, "duration", 0)
                longest_binges_with_users.append((u.get("username"), duration))
                if u.get("username") == username:
                    user_longest_binge = duration

        if longest_binges_with_users and user_longest_binge:
            longest_binges_with_users.sort(key=lambda x: x[1], reverse=True)
            rank = next(
                (
                    i + 1
                    for i, (uname, _) in enumerate(longest_binges_with_users)
                    if uname == username
                ),
                0,
            )
            total = len(longest_binges_with_users)
            percentile = ((total - rank + 1) / total) * 100 if total > 0 else 0
            avg_longest = sum(
                duration for _, duration in longest_binges_with_users
            ) / len(longest_binges_with_users)
            stats["longest_binge"] = {
                "rank": rank,
                "total_users": total,
                "percentile": round(percentile, 1),
                "is_top": rank == 1,
                "above_average": user_longest_binge > avg_longest,
                "average": round(avg_longest),
                "max": max(duration for _, duration in longest_binges_with_users),
            }

        # Genre diversity stats
        genre_counts_with_users = [
            (u.get("username"), len(u.get("genres", []))) for u in self.all_users_data
        ]
        user_genres = next(
            (
                len(u.get("genres", []))
                for u in self.all_users_data
                if u.get("username") == username
            ),
            0,
        )
        if genre_counts_with_users and user_genres > 0:
            genre_counts_with_users.sort(key=lambda x: x[1], reverse=True)
            rank = next(
                (
                    i + 1
                    for i, (uname, _) in enumerate(genre_counts_with_users)
                    if uname == username
                ),
                0,
            )
            total = len(genre_counts_with_users)
            percentile = ((total - rank + 1) / total) * 100 if total > 0 else 0
            avg_genres = sum(count for _, count in genre_counts_with_users) / len(
                genre_counts_with_users
            )
            stats["genre_diversity"] = {
                "rank": rank,
                "total_users": total,
                "percentile": round(percentile, 1),
                "is_top": rank == 1,
                "above_average": user_genres > avg_genres,
                "average": round(avg_genres),
                "max": max(count for _, count in genre_counts_with_users),
            }

        # Device diversity stats
        device_counts_with_users = [
            (u.get("username"), len(u.get("devices", []))) for u in self.all_users_data
        ]
        user_devices = next(
            (
                len(u.get("devices", []))
                for u in self.all_users_data
                if u.get("username") == username
            ),
            0,
        )
        if device_counts_with_users and user_devices > 0:
            device_counts_with_users.sort(key=lambda x: x[1], reverse=True)
            rank = next(
                (
                    i + 1
                    for i, (uname, _) in enumerate(device_counts_with_users)
                    if uname == username
                ),
                0,
            )
            total = len(device_counts_with_users)
            percentile = ((total - rank + 1) / total) * 100 if total > 0 else 0
            avg_devices = sum(count for _, count in device_counts_with_users) / len(
                device_counts_with_users
            )
            stats["device_diversity"] = {
                "rank": rank,
                "total_users": total,
                "percentile": round(percentile, 1),
                "is_top": rank == 1,
                "above_average": user_devices > avg_devices,
                "average": round(avg_devices),
                "max": max(count for _, count in device_counts_with_users),
            }

        return stats
