from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        enabled: bool = True,
        name_mappings: Optional[Dict[str, str]] = None,
        custom_prompt_context: Optional[str] = None,
    ):
        self.enabled = enabled and api_key is not None
        self.client = AsyncOpenAI(api_key=api_key) if self.enabled else None
        self.name_mappings = name_mappings or {}
        self.custom_prompt_context = custom_prompt_context

    async def generate_card_deck(
        self, user_data: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """Generate entire card deck for a user with cohesive story"""
        if not self.enabled or not self.client:
            return None

        try:
            prompt = self._build_card_deck_prompt(user_data)

            # Build context section with optional custom context
            context_lines = ["- This is a shared Plex server with multiple users."]
            if self.custom_prompt_context:
                context_lines.append(f"- {self.custom_prompt_context}")
            context_section = "\n".join(context_lines)

            system_prompt = f"""\
Create a Plex Wrapped card deck. Be fun, insightful, playful, and great overall.

Context:
{context_section}

Card creation instructions:
- don't make more than 10 cards
- don't use full device ID, just use TV, laptop etc
- don't use user's raw user ID. use the provided name
- don't produce raw timestamps
- in comparison card, use only a few key metrics
- start with stats overall, end with summary card
- the first card needs to be the most fun as this will create the first impression
- for cards mentioning specific shows/movies, include the exact title(s) in metrics using keys like:
  * "featured_titles": ["Title 1", "Title 2"] for multiple shows/movies
  * "featured_title": "Title" for a single show/movie
  * "longest_binge_title", "top_title", etc. for specific contexts
  This helps display relevant poster backgrounds for each card.

Fun ideas for cards (in no specific sequence!):
- make it special if they are the top most viewer!
- if someone went crazy and watched the same thing over and over again. tease around that. don't use if barely any repeat
    - 'most_repeated_title': "Title", 'repeat_count': 15, 'other_repeat_hits': {{"Title": count, ...}}
- device usage patterns
    - 'primary_device': "Device Name", 'primary_device_minutes': 9867, 'primary_device_percentage': 93.39, 'other_devices': [{{"device": "Name", "minutes": 402, "percentage": 3.8}}, ...]
- binge sessions and marathon watching
    - 'longest_binge_minutes': 182, 'longest_binge_episodes': 6, 'longest_binge_date': "2025-04-27", 'longest_binge_titles': ["Title 1", "Title 2"], 'longest_session_minutes': 329, 'longest_session_items': 4, 'day_with_most_minutes': 182, 'day_with_most_items': 6
- funny comparisons to understand basic metrics like total watch time
- consistency; if they a peculiar time they watch; look for reasons to pull leg
- (must include!) a card on taste and personality based on watch history
    - 'top_genres': [{{"genre": "Drama", "percentage": 22.12}}, ...]
    - 'top_actors': ["Actor Name", ...]
    ...
- (must include!)watch age! based on their watching history, how old (no range) are they likely to be?
    - kind: fun, metrics: 'watch_age', ...

Return JSON with a "cards" array. Each card must follow this structure:
{{
  "id": "unique string identifier",
  "kind": "summary | stat | record | pattern | comparison | fun",
  "visual_hint": {{
    "icon": "emoji string or null",
    "color": "hex color string or null"
  }},
  "content": {{
    "title": "main title string",
    "subtitle": "subtitle string or null",
    "metrics": {{}} (object with any key-value pairs for stats/metrics),
    "text": {{
      "headline": "headline string",  # no double astricks (*) for bolding
      "description": "main description text",
      "aside": "small aside text or null"
    }}
  }},
  "image_description": "A detailed description of what the image for this card should look like. Describe the visual style, composition, colors, mood, and key elements that should be visualized. Keep it fun and highly personalized."
}}

Remember to make it fun and playful, not creepy.
"""
            response = await self.client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            result = response.choices[0].message.content.strip()
            import json

            # Try to parse as JSON object first
            try:
                parsed = json.loads(result)
                if isinstance(parsed, dict) and "cards" in parsed:
                    return parsed["cards"]
                elif isinstance(parsed, list):
                    return parsed
            except:
                # If not JSON, try to extract JSON from markdown code blocks
                import re

                json_match = re.search(r"```json\s*(.*?)\s*```", result, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(1))
                    if isinstance(parsed, dict) and "cards" in parsed:
                        return parsed["cards"]
                    elif isinstance(parsed, list):
                        return parsed

                # Try to find JSON array directly
                json_match = re.search(r"\[.*\]", result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))

            return []

        except Exception as e:
            print(f"LLM card deck generation failed: {e}")
            return None

    def _get_display_name(self, username: str, user_data: Dict[str, Any]) -> str:
        """Get display name for a username using mappings or fallback to friendly_name"""
        # First check custom name mappings from config
        if username in self.name_mappings:
            return self.name_mappings[username]
        # Fall back to friendly_name from Plex user data
        friendly_name = user_data.get("user_data", {}).get("friendly_name")
        if friendly_name and friendly_name != username:
            return friendly_name
        # Default to username
        return username

    def _build_card_deck_prompt(self, user_data: Dict[str, Any]) -> str:
        """Build prompt for generating entire card deck"""

        username = user_data.get("username", "User")
        display_name = self._get_display_name(username, user_data)

        import json

        user_data_json = json.dumps(user_data, indent=2)

        return f"""Create a Plex Wrap for {display_name}. It should be fun, insightful, playful, and great overall.

{user_data_json}"""
