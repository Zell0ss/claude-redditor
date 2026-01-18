"""Claude-based post classification."""

import json
from typing import List, Dict

from anthropic import Anthropic

from .config import settings
from .projects import project_loader
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

        # Cache for loaded prompts per project
        self._prompt_cache: Dict[str, str] = {}

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

    def _get_prompt_template(self, project: str) -> str:
        """
        Get the classification prompt template for a project.

        Args:
            project: Project name

        Returns:
            Prompt template string
        """
        if project not in self._prompt_cache:
            self._prompt_cache[project] = project_loader.get_prompt(project, 'classify')
        return self._prompt_cache[project]

    def _classify_batch(self, posts: List[RedditPost], project: str = 'default') -> List[Classification]:
        """Classify a batch of posts with a single Claude API call."""

        # Load project configuration
        proj = project_loader.load(project)

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

        # Build the prompt from project-specific template
        prompt_template = self._get_prompt_template(project)
        prompt = prompt_template.replace("{posts_json}", posts_json)
        prompt = prompt.replace("{topic}", proj.topic)

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
                        topic_tags=data.get("topic_tags", []),
                        format_tag=data.get("format_tag"),
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
