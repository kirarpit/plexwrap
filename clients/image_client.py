import os
import asyncio
import base64
import json
from typing import Optional, Dict, Any
from pathlib import Path
import httpx

try:
    from google import genai
    from google.genai import types

    GENAI_AVAILABLE = True
except ImportError:
    try:
        # Fallback to older import style
        import google.generativeai as genai

        types = None
        GENAI_AVAILABLE = True
    except ImportError:
        GENAI_AVAILABLE = False
        genai = None
        types = None


class ImageGenerationClient:
    """Client for generating images using Google's Gemini model"""

    # Gemini model with image generation capabilities
    MODEL_NAME = "gemini-3-pro-image-preview"

    def __init__(
        self,
        api_key: Optional[str] = None,
        enabled: bool = True,
        name_mappings: Optional[Dict[str, str]] = None,
    ):
        self.enabled = enabled and api_key is not None
        self.api_key = api_key
        self.client = None
        self.name_mappings = name_mappings or {}

        if self.enabled and GENAI_AVAILABLE and api_key:
            try:
                # Use the new google-genai SDK client
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"Warning: Failed to configure Google Generative AI: {e}")
                self.enabled = False

    async def generate_all_card_images(
        self,
        cards: list[Dict[str, Any]],
        username: str,
    ) -> list[Optional[str]]:
        """
        Generate images for all cards from a single prompt containing all card data.
        Images are saved immediately as they're generated to avoid losing work.

        Args:
            cards: List of card data dictionaries
            username: Username for personalization

        Returns:
            List of image paths (or None for failed generations)
        """
        if not self.enabled or not self.api_key:
            return [None] * len(cards)

        total_cards = len(cards)

        print(f"🎨 Generating images for all {total_cards} cards (one at a time)...")

        # Generate images one at a time for better quality
        image_paths = await self._generate_images_one_by_one(cards, username)

        successful = sum(1 for p in image_paths if p is not None)
        print(f"✅ Completed: {successful}/{total_cards} images saved to disk")

        return image_paths

    def _get_first_name(self, username: str) -> str:
        """Get display name from username using configured mappings"""
        if username in self.name_mappings:
            return self.name_mappings[username]
        return username if username else "User"

    def _build_system_prompt(
        self,
        cards: list[Dict[str, Any]],
        username: str,
    ) -> str:
        """Build the system prompt with ALL cards information"""
        import json

        # Use mapped first name instead of raw username in prompts
        first_name = self._get_first_name(username)

        all_cards_json = json.dumps(cards, indent=2, ensure_ascii=False)
        total_cards = len(cards)

        system_prompt = f"""\
I'm creating a PlexWrap mobile story that reviews {first_name}'s Plex watching history. This will be a series of {total_cards} story-style screens, with one image per card. This should feel **deeply personal, playful, and self-aware** — not like a product ad or marketing graphic.

## Format & layout
- Each image should be vertical 16:9, optimized for mobile story viewing
- Each image must feel like one full-screen composition
- No nested app frames, device mockups, or screen-within-screen layouts
- Avoid card-in-card or framed containers — content should live directly on the canvas
- Do NOT include story progress indicators (e.g., horizontal bars or dots at the top)

## Visual style
- Modern, vibrant, and expressive, but not glossy or ad-like
- Less "product hero", more "your habits exposed"
- Prefer abstract, illustrative, or stylized visuals over realistic or stock-photo scenes
- Use typography, scale, color, and composition to create emphasis rather than UI widgets or dashboards

## Content & tone
- The key statistics and insights are the main focus and should be immediately legible
- Copy should feel opinionated, playful, and teasing -- as if the story knows the user
- Use small human details when relevant (dates, late-night vibes, binge behavior, "this wasn't casual" moments)
- Avoid neutral or promotional language; prioritize personality and specificity

## Backgrounds
- Include a subtle background reference to the show or movie mentioned in the data
- Backgrounds should suggest the mood or vibe of the title, not literally depict a scene or room
- Keep backgrounds clean and restrained so the data remains easy to read
- Backgrounds should support the story, not compete with the numbers or copy

## Story cohesion
- All images should feel like part of the same cohesive story
- Consistent visual language, colors, and typography across screens

Here is ALL the card data for the complete story ({total_cards} cards total):

{all_cards_json}

We will generate images one at a time. I'll ask you to create each card's image in sequence."""

        return system_prompt

    def _build_card_request_prompt(self, card_index: int, total_cards: int) -> str:
        """Build the prompt to request a specific card image"""
        if card_index == 0:
            return f"Please generate the image for Card 1 of {total_cards}."
        else:
            return f"Great! Now please generate the image for Card {card_index + 1} of {total_cards}."

    async def _generate_images_one_by_one(
        self,
        cards: list[Dict[str, Any]],
        username: str,
    ) -> list[Optional[str]]:
        """
        Generate images one at a time using multi-turn conversation.

        All cards data is provided in the initial system prompt, then we
        continue the conversation asking for each card's image in sequence.
        This helps maintain visual consistency across all cards.

        Note: The model may return multiple images even when asked for one.
        We handle this by saving all returned images and skipping ahead.
        """
        if not self.enabled or not self.client:
            print("Image generation not enabled or client not initialized")
            return [None] * len(cards)

        total_cards = len(cards)
        # Initialize with None for all cards
        saved_paths: list[Optional[str]] = [None] * total_cards

        # Create output directory
        images_dir = Path("generated_images") / username
        images_dir.mkdir(parents=True, exist_ok=True)

        # Build the system prompt with ALL cards information
        system_prompt = self._build_system_prompt(cards, username)

        # Save the system prompt for debugging
        system_prompt_file = images_dir / "system_prompt.txt"
        with open(system_prompt_file, "w") as f:
            f.write(system_prompt)
        print(f"  📝 Saved system prompt to {system_prompt_file}")

        # Initialize conversation history with the system prompt
        # Format: list of content objects for multi-turn conversation
        conversation_history = []

        i = 0
        while i < total_cards:
            # Skip if we already have an image for this card
            if saved_paths[i] is not None:
                i += 1
                continue

            try:
                # Build the request for this specific card
                card_request = self._build_card_request_prompt(i, total_cards)

                print(f"  🖼️  Generating image {i + 1}/{total_cards}...")

                # Build the full conversation for this request
                if i == 0:
                    # First card: include system prompt + first request
                    contents = [
                        {"role": "user", "parts": [{"text": system_prompt}]},
                        {
                            "role": "model",
                            "parts": [
                                {
                                    "text": "I understand. I'll create a cohesive visual story for this PlexWrap. I have all the card data and will maintain consistent visual language across all cards. Let me know which card to generate first."
                                }
                            ],
                        },
                        {"role": "user", "parts": [{"text": card_request}]},
                    ]
                else:
                    # Subsequent cards: use the accumulated conversation history + new request
                    contents = conversation_history + [
                        {"role": "user", "parts": [{"text": card_request}]},
                    ]

                # Save the full request for debugging (raw dump, not processed)
                prompt_file = images_dir / f"prompt_card_{i}.json"
                with open(prompt_file, "w") as f:
                    # Create a serializable version - handle bytes and API objects
                    def make_serializable(obj):
                        if obj is None:
                            return None
                        elif isinstance(obj, (str, int, float, bool)):
                            return obj
                        elif isinstance(obj, bytes):
                            return f"<bytes: {len(obj)} bytes>"
                        elif isinstance(obj, dict):
                            return {k: make_serializable(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [make_serializable(item) for item in obj]
                        elif hasattr(obj, "model_dump"):
                            # Pydantic-style objects
                            return make_serializable(obj.model_dump())
                        elif hasattr(obj, "to_dict"):
                            return make_serializable(obj.to_dict())
                        elif hasattr(obj, "__dict__"):
                            # Generic object with attributes
                            return {
                                "_type": type(obj).__name__,
                                **{
                                    k: make_serializable(v)
                                    for k, v in obj.__dict__.items()
                                    if not k.startswith("_")
                                },
                            }
                        else:
                            # Fallback to string representation
                            return f"<{type(obj).__name__}: {str(obj)[:200]}>"

                    serializable_contents = make_serializable(contents)
                    json.dump(serializable_contents, f, indent=2, ensure_ascii=False)
                print(f"  📝 Saved raw request to {prompt_file}")

                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.MODEL_NAME,
                    contents=contents,
                    config=(
                        types.GenerateContentConfig(
                            response_modalities=["IMAGE", "TEXT"],
                        )
                        if types
                        else None
                    ),
                )

                # Extract all images from response (model may return multiple)
                images = self._extract_images_from_response(response, debug=(i == 0))

                if images:
                    if len(images) > 1:
                        print(
                            f"    ℹ️  Got {len(images)} images from single request, saving all..."
                        )

                    # Save all images we got, starting from current index
                    saved_count = 0
                    for img_idx, img_data in enumerate(images):
                        card_idx = i + img_idx
                        if card_idx >= total_cards:
                            print(
                                f"    ⚠️  Got more images than cards remaining, ignoring extra"
                            )
                            break
                        path = await self._save_image(img_data, username, card_idx)
                        saved_paths[card_idx] = path
                        saved_count += 1
                        print(
                            f"    💾 Saved image {card_idx + 1}/{total_cards}: {path}"
                        )

                    # Extract the raw model response content (preserves thought_signature)
                    # This is crucial - we must use the actual response content, not rebuild it
                    if not (
                        response
                        and response.candidates
                        and response.candidates[0].content
                    ):
                        raise RuntimeError(
                            f"Cannot get raw model content for card {i + 1}. "
                            "This is required to preserve thought_signature for subsequent requests."
                        )

                    raw_model_content = response.candidates[0].content

                    # Update conversation history: use contents (already has the request) + model response
                    conversation_history = list(contents)  # Copy the request we sent
                    conversation_history.append(raw_model_content)

                    # Skip ahead past all the images we just saved
                    i += saved_count
                else:
                    print(f"    ⚠️  No image data in response for card {i + 1}")
                    # No image but we need to continue - require raw model content
                    if not (
                        response
                        and response.candidates
                        and response.candidates[0].content
                    ):
                        raise RuntimeError(
                            f"No image and cannot get raw model content for card {i + 1}. "
                            "Cannot continue without thought_signature."
                        )

                    raw_model_content = response.candidates[0].content

                    # Update conversation history: use contents + model response
                    conversation_history = list(contents)
                    conversation_history.append(raw_model_content)
                    i += 1

            except Exception as e:
                print(f"    ❌ Error generating image {i + 1}: {e}")
                import traceback

                traceback.print_exc()
                i += 1

        return saved_paths

    def _extract_images_from_response(
        self, response, debug: bool = False
    ) -> list[bytes]:
        """Extract all images from an API response"""
        images = []

        if not response:
            if debug:
                print("    🔍 Debug: Response is None/empty")
            return images

        if not response.candidates:
            if debug:
                print(f"    🔍 Debug: No candidates in response")
                # Try to get more info about the response
                if hasattr(response, "prompt_feedback"):
                    print(f"    🔍 Debug: Prompt feedback: {response.prompt_feedback}")
            return images

        for ci, candidate in enumerate(response.candidates):
            if debug:
                print(f"    🔍 Debug: Checking candidate {ci}")
                if hasattr(candidate, "finish_reason"):
                    print(f"    🔍 Debug: Finish reason: {candidate.finish_reason}")

            if not candidate.content:
                if debug:
                    print(f"    🔍 Debug: Candidate {ci} has no content")
                continue

            if not candidate.content.parts:
                if debug:
                    print(f"    🔍 Debug: Candidate {ci} content has no parts")
                continue

            for pi, part in enumerate(candidate.content.parts):
                if debug:
                    part_type = type(part).__name__
                    has_inline = (
                        hasattr(part, "inline_data") and part.inline_data is not None
                    )
                    has_text = hasattr(part, "text") and part.text
                    print(
                        f"    🔍 Debug: Part {pi} type={part_type}, has_inline_data={has_inline}, has_text={has_text}"
                    )

                if hasattr(part, "inline_data") and part.inline_data:
                    try:
                        data = part.inline_data.data
                        # Data is already raw bytes (PNG/JPEG), no base64 decoding needed
                        if isinstance(data, bytes):
                            image_bytes = data
                        else:
                            # Fallback: if it's a string, try base64 decode
                            image_bytes = base64.b64decode(data)
                        images.append(image_bytes)
                        if debug:
                            print(
                                f"    🔍 Debug: Extracted image, size={len(image_bytes)} bytes, is_raw_bytes={isinstance(data, bytes)}"
                            )
                    except Exception as e:
                        print(f"    ⚠️  Failed to extract image: {e}")

        if debug and not images:
            print(f"    🔍 Debug: No images extracted from response")

        return images

    async def _save_image(
        self, image_data: bytes, username: str, card_index: int
    ) -> str:
        """Save generated image to disk and return the path"""
        # Create images directory
        images_dir = Path("generated_images") / username
        images_dir.mkdir(parents=True, exist_ok=True)

        # Save image
        image_path = images_dir / f"card_{card_index}.png"
        with open(image_path, "wb") as f:
            f.write(image_data)

        # Return relative path for storage in JSON
        return str(image_path)
