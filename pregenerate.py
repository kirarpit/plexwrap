"""
Pre-generate wraps for all users offline.

Usage:
    python pregenerate.py                    # Full pipeline for all users
    python pregenerate.py USERNAME           # Full pipeline for single user
    python pregenerate.py --data-only        # Collect raw data only (no LLM/images)
    python pregenerate.py --cards-only       # Regenerate LLM cards from existing data
    python pregenerate.py --images-only      # Generate images for existing wraps
    python pregenerate.py --force            # Force regenerate even if exists
"""

import argparse
import asyncio
import json
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from config import load_config
from analyzer import WrapAnalyzer
from models import WrapData
from cross_user_analyzer import CrossUserAnalyzer


DATA_DIR = Path("wraps_data")


class WrapStorage:
    """Storage for pre-generated wraps"""

    def __init__(
        self, storage_dir: str = "wraps", tokens_file: str = "data/tokens.json"
    ):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.tokens_file = Path(tokens_file)
        self.tokens_file.parent.mkdir(parents=True, exist_ok=True)
        self._tokens_cache: Optional[Dict[str, str]] = None

    def _load_tokens(self) -> Dict[str, str]:
        if self._tokens_cache is not None:
            return self._tokens_cache
        if not self.tokens_file.exists():
            self._tokens_cache = {}
            return self._tokens_cache
        try:
            with open(self.tokens_file, "r") as f:
                self._tokens_cache = json.load(f)
            return self._tokens_cache
        except Exception as e:
            print(f"Error loading tokens: {e}")
            self._tokens_cache = {}
            return self._tokens_cache

    def _save_tokens(self, tokens: Dict[str, str]) -> bool:
        try:
            with open(self.tokens_file, "w") as f:
                json.dump(tokens, f, indent=2)
            self._tokens_cache = tokens
            return True
        except Exception as e:
            print(f"Error saving tokens: {e}")
            return False

    def get_token_for_user(self, username: str) -> Optional[str]:
        tokens = self._load_tokens()
        for token, uname in tokens.items():
            if uname == username:
                return token
        new_token = str(uuid.uuid4())
        tokens[new_token] = username
        return new_token if self._save_tokens(tokens) else None

    def get_username_for_token(self, token: str) -> Optional[str]:
        return self._load_tokens().get(token)

    def get_wrap_path(self, username: str) -> Path:
        safe_username = "".join(c for c in username if c.isalnum() or c in ("-", "_"))
        return self.storage_dir / f"{safe_username}.json"

    def save_wrap(self, username: str, wrap_data: WrapData) -> bool:
        try:
            with open(self.get_wrap_path(username), "w") as f:
                json.dump(wrap_data.model_dump(), f, indent=2, default=str)
            self.get_token_for_user(username)
            return True
        except Exception as e:
            print(f"Error saving wrap for {username}: {e}")
            return False

    def load_wrap(self, username: str) -> Dict | None:
        try:
            path = self.get_wrap_path(username)
            if not path.exists():
                return None
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading wrap for {username}: {e}")
            return None

    def load_wrap_by_token(self, token: str) -> Dict | None:
        username = self.get_username_for_token(token)
        return self.load_wrap(username) if username else None

    def list_wraps(self) -> List[str]:
        return [f.stem for f in self.storage_dir.glob("*.json")]


# =============================================================================
# Pipeline Stages
# =============================================================================


async def collect_raw_data(
    analyzer: WrapAnalyzer,
    usernames: List[str] | None = None,
    force: bool = False,
) -> List[Tuple[str, Dict]]:
    """Stage 1: Collect raw data from Tautulli API"""
    print("\n📊 STAGE 1: Collecting raw data...")

    # Get excluded users from settings
    excluded_users = set(analyzer.settings.excluded_users)

    if usernames is None:
        # Get all users from Tautulli
        users = analyzer.tautulli.get_users()
        usernames = [
            u.get("username") or u.get("friendly_name", "Unknown")
            for u in users
            if (u.get("username") or u.get("friendly_name", "Unknown"))
            not in excluded_users
        ]

    all_raw_data = []
    DATA_DIR.mkdir(exist_ok=True)

    for i, username in enumerate(usernames, 1):
        if username in excluded_users:
            continue

        cache_path = DATA_DIR / f"{username}_raw_data.json"

        # Try to load cached data if not forcing
        if not force and cache_path.exists():
            print(
                f"  [{i}/{len(usernames)}] Loading cached: {username}...",
                end=" ",
                flush=True,
            )
            try:
                with open(cache_path, "r") as f:
                    raw_data = json.load(f)

                # Validate cached data matches current date range
                cached_start = raw_data.get("period_start")
                cached_end = raw_data.get("period_end")
                config_start = analyzer.settings.start_date
                config_end = analyzer.settings.end_date

                if cached_start != config_start or cached_end != config_end:
                    print(
                        f"⚠️ Date range mismatch (cached: {cached_start}-{cached_end}, config: {config_start}-{config_end}), re-fetching..."
                    )
                else:
                    all_raw_data.append((username, raw_data))
                    print("✅")
                    continue
            except Exception as e:
                print(f"⚠️ Cache error, re-fetching: {e}")

        # Fetch fresh data
        print(f"  [{i}/{len(usernames)}] Fetching: {username}...", end=" ", flush=True)
        try:
            raw_data = await analyzer.analyze_user_raw_data(username)
            all_raw_data.append((username, raw_data))
            # Cache the data
            with open(cache_path, "w") as f:
                json.dump(raw_data, f, indent=2, default=str)
            print("✅")
        except Exception as e:
            print(f"❌ {e}")

    print(f"  → Collected data for {len(all_raw_data)} users")
    return all_raw_data


def compute_cross_user_stats(
    all_raw_data: List[Tuple[str, Dict]],
    enabled: bool = True,
) -> Dict:
    """Compute cross-user comparisons and add comparative stats to raw_data"""
    if not enabled:
        print("\n🔍 Cross-user comparisons: DISABLED")
        # Clear any existing comparative_stats from raw data
        for username, raw_data in all_raw_data:
            raw_data["comparative_stats"] = {}
        return {}

    print("\n🔍 Computing cross-user comparisons...")

    cross_analyzer = CrossUserAnalyzer()
    for username, raw_data in all_raw_data:
        cross_analyzer.add_user_data(username, raw_data)

    cross_user_insights = cross_analyzer.generate_cross_user_insights()

    # Add comparative stats to each user's data
    for username, raw_data in all_raw_data:
        raw_data["comparative_stats"] = cross_analyzer.get_user_comparative_stats(
            username
        )

    print(f"  → Generated {len(cross_user_insights)} comparison metrics")
    return cross_user_insights


def save_raw_data(all_raw_data: List[Tuple[str, Dict]], cross_user_insights: Dict):
    """Save raw data and insights to disk"""
    print("\n💾 Saving raw data...")
    DATA_DIR.mkdir(exist_ok=True)

    # Save cross-user insights
    with open(DATA_DIR / "cross_user_insights.json", "w") as f:
        json.dump(cross_user_insights, f, indent=2, default=str)

    # Save per-user data
    for username, raw_data in all_raw_data:
        with open(DATA_DIR / f"{username}_raw_data.json", "w") as f:
            json.dump(raw_data, f, indent=2, default=str)

    print(f"  → Saved to {DATA_DIR.absolute()}")


def load_existing_raw_data(
    excluded_users: set = None,
) -> Tuple[List[Tuple[str, Dict]], Dict]:
    """Load previously saved raw data from disk"""
    print("\n📂 Loading existing raw data...")

    if excluded_users is None:
        excluded_users = set()

    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"Data directory {DATA_DIR} not found. Run without --cards-only first."
        )

    # Load cross-user insights
    insights_path = DATA_DIR / "cross_user_insights.json"
    cross_user_insights = {}
    if insights_path.exists():
        with open(insights_path, "r") as f:
            cross_user_insights = json.load(f)

    # Load per-user data
    all_raw_data = []
    for path in DATA_DIR.glob("*_raw_data.json"):
        username = path.stem.replace("_raw_data", "")
        if username in excluded_users:
            continue
        try:
            with open(path, "r") as f:
                all_raw_data.append((username, json.load(f)))
        except Exception as e:
            print(f"  ⚠️ Error loading {username}: {e}")

    print(f"  → Loaded data for {len(all_raw_data)} users")
    return all_raw_data, cross_user_insights


async def generate_cards(
    analyzer: WrapAnalyzer,
    storage: WrapStorage,
    all_raw_data: List[Tuple[str, Dict]],
    usernames: List[str] | None = None,
    force: bool = False,
    generate_images: bool = True,
) -> Tuple[int, int, int]:
    """Stage 2: Generate LLM cards and save wraps"""
    print("\n🎨 STAGE 2: Generating LLM cards...")

    successful, failed, skipped = 0, 0, 0

    # Filter to specific users if provided
    if usernames:
        all_raw_data = [(u, d) for u, d in all_raw_data if u in usernames]

    for i, (username, raw_data) in enumerate(all_raw_data, 1):
        print(f"  [{i}/{len(all_raw_data)}] {username}...", end=" ", flush=True)

        if not force and storage.load_wrap(username):
            print("⏭️ exists")
            skipped += 1
            continue

        try:
            wrap_data = await analyzer.generate_wrap_from_raw_data(
                username,
                raw_data,
                generate_images=generate_images,
            )
            if storage.save_wrap(username, wrap_data):
                print(f"✅")
                successful += 1
            else:
                print("❌ save failed")
                failed += 1
        except Exception as e:
            print(f"❌ {e}")
            failed += 1

    print(f"  → Success: {successful}, Skipped: {skipped}, Failed: {failed}")
    return successful, failed, skipped


async def generate_images(
    analyzer: WrapAnalyzer,
    storage: WrapStorage,
    usernames: List[str] | None = None,
) -> Tuple[int, int]:
    """Stage 3: Generate images for existing wraps"""
    print("\n🖼️ STAGE 3: Generating images...")

    if not analyzer.image_gen.enabled:
        print("  ⚠️ Image generation not enabled in config.yaml")
        return 0, 0

    # Get list of wraps to process
    if usernames is None:
        usernames = storage.list_wraps()

    total_images, failed_users = 0, 0

    for i, username in enumerate(usernames, 1):
        print(f"  [{i}/{len(usernames)}] {username}...", end=" ", flush=True)

        wrap_data = storage.load_wrap(username)
        if not wrap_data:
            print("⏭️ no wrap")
            continue

        cards = wrap_data.get("cards", [])
        if not cards:
            print("⏭️ no cards")
            continue

        try:
            image_paths = await analyzer.image_gen.generate_all_card_images(
                cards=cards, username=username
            )

            # Update cards with image paths
            for card, path in zip(cards, image_paths):
                if path:
                    card["generated_image"] = path

            wrap_data["cards"] = cards
            wrap_data_obj = WrapData(**wrap_data)

            if storage.save_wrap(username, wrap_data_obj):
                count = sum(1 for p in image_paths if p)
                total_images += count
                print(f"✅ {count}/{len(cards)} images")
            else:
                print("❌ save failed")
                failed_users += 1
        except Exception as e:
            print(f"❌ {e}")
            failed_users += 1

    print(f"  → Total images: {total_images}, Failed users: {failed_users}")
    return total_images, failed_users


# =============================================================================
# Main Pipeline
# =============================================================================


async def run_pipeline(args):
    """Main pipeline runner"""
    config = load_config()
    analyzer = WrapAnalyzer(config)
    storage = WrapStorage()

    # Determine which users to process
    usernames = [args.username] if args.username else None

    print("=" * 60)
    print("🎬 PLEX WRAPPED - Pre-generation Pipeline")
    print("=" * 60)
    if usernames:
        print(f"👤 User: {usernames[0]}")
    else:
        print("👥 All users")
    print(f"📅 Period: {config.start_date} to {config.end_date}")

    # Determine pipeline mode
    if args.images_only:
        # Only generate images for existing wraps
        await generate_images(analyzer, storage, usernames)

    elif args.cards_only:
        # Load existing data, regenerate cards (without images)
        all_raw_data, cross_user_insights = load_existing_raw_data(
            set(config.excluded_users)
        )
        cross_user_insights = compute_cross_user_stats(
            all_raw_data, enabled=config.cross_user_comparison
        )
        await generate_cards(
            analyzer,
            storage,
            all_raw_data,
            usernames,
            args.force,
            generate_images=False,
        )

    elif args.data_only:
        # Only collect and save raw data
        collected_data = await collect_raw_data(analyzer, usernames, args.force)

        # For cross-user comparison, merge with existing cached data
        if usernames and config.cross_user_comparison:
            try:
                existing_data, _ = load_existing_raw_data(set(config.excluded_users))
                all_data_dict = {u: d for u, d in existing_data}
                for username, data in collected_data:
                    all_data_dict[username] = data
                all_raw_data = list(all_data_dict.items())
            except FileNotFoundError:
                all_raw_data = collected_data
        else:
            all_raw_data = collected_data

        cross_user_insights = compute_cross_user_stats(
            all_raw_data, enabled=config.cross_user_comparison
        )
        save_raw_data(all_raw_data, cross_user_insights)

    else:
        # Full pipeline: data → cards → images (if enabled)
        # Note: generate_cards already generates images when generate_images=True (default)

        # Collect data for specified user(s)
        collected_data = await collect_raw_data(analyzer, usernames, args.force)

        # For cross-user comparison, we need ALL users' data
        # Load existing cached data and merge with freshly collected data
        if usernames and config.cross_user_comparison:
            try:
                existing_data, _ = load_existing_raw_data(set(config.excluded_users))
                # Create a dict for easy lookup/update
                all_data_dict = {u: d for u, d in existing_data}
                # Update with freshly collected data
                for username, data in collected_data:
                    all_data_dict[username] = data
                all_raw_data = list(all_data_dict.items())
            except FileNotFoundError:
                # No existing data, just use what we collected
                all_raw_data = collected_data
        else:
            all_raw_data = collected_data

        cross_user_insights = compute_cross_user_stats(
            all_raw_data, enabled=config.cross_user_comparison
        )
        save_raw_data(all_raw_data, cross_user_insights)
        await generate_cards(
            analyzer,
            storage,
            all_raw_data,
            usernames,
            args.force,
        )

    print()
    print("=" * 60)
    print("✅ Pipeline complete!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Pre-generate Plex Wrapped for all users",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pregenerate.py                    Full pipeline for all users
  python pregenerate.py johnsmith          Full pipeline for single user
  python pregenerate.py --data-only        Collect raw data only
  python pregenerate.py --cards-only       Regenerate cards from existing data
  python pregenerate.py --images-only      Generate images for existing wraps
  python pregenerate.py --force            Force regenerate everything
        """,
    )

    parser.add_argument(
        "username",
        nargs="?",
        help="Username to process (omit for all users)",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force regenerate even if data/wraps already exist",
    )
    parser.add_argument(
        "--data-only",
        action="store_true",
        help="Only collect raw data from APIs, skip card/image generation",
    )
    parser.add_argument(
        "--cards-only",
        action="store_true",
        help="Regenerate LLM cards using existing raw data",
    )
    parser.add_argument(
        "--images-only",
        action="store_true",
        help="Only generate images for existing wraps",
    )

    args = parser.parse_args()

    # Validate mutually exclusive options
    mode_flags = [args.data_only, args.cards_only, args.images_only]
    if sum(mode_flags) > 1:
        parser.error("Only one of --data-only, --cards-only, --images-only can be used")

    asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    main()
