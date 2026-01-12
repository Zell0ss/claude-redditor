"""Claude-based post classification."""

import json
from pathlib import Path
from typing import List

from anthropic import Anthropic

from .config import settings
from .core.models import RedditPost, Classification
from .core.enums import CategoryEnum


class PostClassifier:
    """Classifies Reddit posts using Claude API."""

    def __init__(self):
        """Initialize classifier with Claude API client."""
        if not settings.anthropic_api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY in .env file."
            )

        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model

        # Load classification prompt
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "classify_posts.md"
        with open(prompt_path, "r") as f:
            self.prompt_template = f.read()

    def classify_posts(self, posts: List[RedditPost], batch_size: int = None, project: str = 'default') -> List[Classification]:
        """
        Classify a list of posts using Claude API.

        Args:
            posts: List of RedditPost objects to classify
            batch_size: Number of posts per API request (default from settings)
            project: Project name (default: 'default')

        Returns:
            List of Classification objects
        """
        if batch_size is None:
            batch_size = settings.default_batch_size

        all_classifications = []

        # Process in batches
        for i in range(0, len(posts), batch_size):
            batch = posts[i : i + batch_size]
            classifications = self._classify_batch(batch, project=project)
            all_classifications.extend(classifications)

        return all_classifications

    def _classify_batch(self, posts: List[RedditPost], project: str = 'default') -> List[Classification]:
        """Classify a batch of posts with a single Claude API call."""

        # Prepare posts as JSON for the prompt
        posts_data = []
        for post in posts:
            posts_data.append({
                "post_id": post.id,
                "title": post.title,
                "selftext": post.truncated_selftext,
                "author": post.author,
                "subreddit": post.subreddit,
                "flair": post.flair,
            })

        posts_json = json.dumps(posts_data, indent=2)

        # Build the prompt
        from .config import settings
        prompt = self.prompt_template.replace("{posts_json}", posts_json)
        prompt = prompt.replace("{topic}", settings.get_project_topic(project))

        # Call Claude API
        print(f"🤖 Classifying {len(posts)} posts with {self.model}...")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text response
            response_text = response.content[0].text

            # Parse JSON response
            classifications_data = self._extract_json(response_text)

            # Convert to Classification objects
            classifications = []
            for data in classifications_data:
                try:
                    classification = Classification(
                        post_id=data["post_id"],
                        category=CategoryEnum(data["category"]),
                        confidence=float(data["confidence"]),
                        red_flags=data.get("red_flags", []),
                        reasoning=data.get("reasoning", ""),
                    )
                    classifications.append(classification)
                except (KeyError, ValueError) as e:
                    print(f"⚠ Warning: Failed to parse classification for post {data.get('post_id', 'unknown')}: {e}")

            print(f"✓ Successfully classified {len(classifications)} posts")
            return classifications

        except Exception as e:
            print(f"✗ Error calling Claude API: {e}")
            raise

    def _extract_json(self, text: str) -> list:
        """Extract JSON array from Claude's response."""
        # Try to find JSON in the response
        start_idx = text.find("[")
        end_idx = text.rfind("]") + 1

        if start_idx == -1 or end_idx == 0:
            raise ValueError("No JSON array found in response")

        json_str = text[start_idx:end_idx]

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"⚠ JSON parsing error: {e}")
            print(f"Response text: {text}")
            raise


def create_classifier() -> PostClassifier:
    """Factory function to create a PostClassifier instance."""
    return PostClassifier()
