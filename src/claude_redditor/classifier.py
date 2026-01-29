"""Claude-based post classification."""

import json
from typing import List, Dict

from anthropic import Anthropic

from .config import settings
from .projects import project_loader
from .core.models import RedditPost, Classification
from .core.enums import CategoryEnum

# Category correction for common LLM mistakes (maps invalid → valid)
CATEGORY_CORRECTIONS = {
    "discussion": "community",
    "news": "technical",
    "signal": "technical",
    "noise": "unverified_claim",
    "meta": "community",
    "question": "community",
    "showcase": "technical",
    "tutorial": "technical",
    "resource": "technical",
}


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
        Classify a list of posts using Claude API (two-pass classification).

        Args:
            posts: List of RedditPost objects to classify
            batch_size: Number of posts per API request (default from settings)
            project: Project name (default: 'default')

        Returns:
            List of Classification objects with tier data
        """
        if batch_size is None:
            batch_size = settings.default_batch_size

        all_classifications = []

        # STEP 1: Process category classifications in batches
        for i in range(0, len(posts), batch_size):
            batch = posts[i : i + batch_size]
            try:
                classifications = self._classify_batch(batch, project=project)
                all_classifications.extend(classifications)
            except ValueError as e:
                if "refusal" in str(e).lower():
                    # API refused the batch - retry with smaller batches
                    # this happens when the content is "problematic" for the IA (non ethical hacking, smut, etc...)
                    # We try to classify each post individually to skip the problematic one/s
                    print(f"⚠ Batch refused by API, retrying with individual posts...")
                    for post in batch:
                        try:
                            single_result = self._classify_batch([post], project=project)
                            all_classifications.extend(single_result)
                        except ValueError as e2:
                            if "refusal" in str(e2).lower():
                                print(f"⚠ Skipping post {post.id} (content refused by API)")
                            else:
                                raise
                else:
                    raise

        # STEP 2: Tier classification (only for non-UNRELATED posts)
        # Check if project has tagging.md prompt (tier system is optional)
        try:
            self._get_tier_prompt_template(project)
            has_tier_system = True
        except FileNotFoundError:
            has_tier_system = False
            print(f"ℹ No tier tagging system found for project '{project}' (tagging.md missing)")

        if has_tier_system:
            # Filter posts eligible for tier classification
            tier_eligible_posts = []
            for post, cls in zip(posts, all_classifications):
                if cls.category != CategoryEnum.UNRELATED:
                    tier_eligible_posts.append(post)

            if tier_eligible_posts:
                print(f"🏷️  Starting tier classification for {len(tier_eligible_posts)} posts...")

                # Process tiers in batches
                for i in range(0, len(tier_eligible_posts), batch_size):
                    batch = tier_eligible_posts[i : i + batch_size]
                    try:
                        tier_results = self._classify_tiers_batch(batch, project=project)

                        # Merge tier data into classifications
                        tier_map = {t['post_id']: t for t in tier_results}
                        merged_count = 0
                        for cls in all_classifications:
                            if cls.post_id in tier_map:
                                tier_data = tier_map[cls.post_id]
                                cls.tier_tags = tier_data.get('tier_tags')
                                cls.tier_clusters = tier_data.get('clusters', [])
                                cls.tier_scoring = tier_data.get('scoring')
                                merged_count += 1

                        print(f"  📌 Merged tier data for {merged_count}/{len(tier_results)} posts")

                    except Exception as e:
                        print(f"⚠ Warning: Tier classification failed for batch: {e}")
                        import traceback
                        traceback.print_exc()
                        # Continue without tier data for this batch

                print(f"✓ Tier classification complete")

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
            if not response.content:
                raise ValueError(f"Empty response from Claude API. Stop reason: {response.stop_reason}")
            response_text = response.content[0].text

            # Parse JSON response
            classifications_data = self._extract_json(response_text)

            # Convert to Classification objects
            classifications = []
            for data in classifications_data:
                try:
                    # Auto-correct common LLM category mistakes
                    category = data["category"]
                    if category in CATEGORY_CORRECTIONS:
                        corrected = CATEGORY_CORRECTIONS[category]
                        print(f"⚠ Auto-corrected category '{category}' → '{corrected}' for {data['post_id']}")
                        category = corrected

                    classification = Classification(
                        post_id=data["post_id"],
                        category=CategoryEnum(category),
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

    def _get_tier_prompt_template(self, project: str) -> str:
        """
        Get the tier classification prompt template for a project.

        Args:
            project: Project name

        Returns:
            Tier prompt template string

        Raises:
            FileNotFoundError: If tagging.md doesn't exist for project
        """
        try:
            return project_loader.get_prompt(project, 'tagging')
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Tier tagging prompt not found for project '{project}'. "
                f"Create prompts/tagging.md in the project directory based on PROMPT_FOR_TAGGING_SYSTEM.md"
            )

    def _classify_tiers_batch(self, posts: List[RedditPost], project: str = 'default') -> List[Dict]:
        """
        Classify a batch of posts with tier tagging system (second API call).

        Args:
            posts: List of RedditPost objects to classify
            project: Project name

        Returns:
            List of dicts with tier_tags, clusters, scoring
        """
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
            })

        posts_json = json.dumps(posts_data, indent=2)

        # Build the prompt from project-specific tier template
        prompt_template = self._get_tier_prompt_template(project)
        prompt = prompt_template.replace("{posts_json}", posts_json)
        prompt = prompt.replace("{topic}", proj.topic)

        # Call Claude API with higher token limit for tier output
        print(f"🏷️  Tier-tagging {len(posts)} posts with {self.model}...")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,  # Tiers need more output space
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text response
            if not response.content:
                raise ValueError(f"Empty response from Claude API. Stop reason: {response.stop_reason}")
            response_text = response.content[0].text

            # Parse JSON response - tier responses are array of objects
            tier_results = self._extract_json(response_text)

            # Debug: print first result structure
            if tier_results:
                print(f"📋 First tier result keys: {list(tier_results[0].keys())}")

            print(f"✓ Successfully tier-tagged {len(tier_results)} posts")
            return tier_results

        except Exception as e:
            print(f"✗ Error calling Claude API for tier tagging: {e}")
            print(f"Response preview: {response_text[:500] if 'response_text' in locals() else 'N/A'}...")
            raise

    def _extract_json(self, text: str) -> list:
        """Extract JSON array from Claude's response."""
        # Try to find JSON in the response - handle markdown code blocks
        # Look for ```json ... ``` first
        import re
        json_block_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', text)
        if json_block_match:
            json_str = json_block_match.group(1)
        else:
            # Fallback: find first [ to matching ]
            start_idx = text.find("[")
            if start_idx == -1:
                raise ValueError("No JSON array found in response")

            # Find the matching closing bracket (handling nested arrays)
            bracket_count = 0
            end_idx = start_idx
            for i, char in enumerate(text[start_idx:], start_idx):
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_idx = i + 1
                        break

            if end_idx <= start_idx:
                raise ValueError("No matching ] found in response")

            json_str = text[start_idx:end_idx]

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"⚠ JSON parsing error: {e}")
            print(f"Extracted JSON: {json_str[:500]}...")
            raise


def create_classifier() -> PostClassifier:
    """Factory function to create a PostClassifier instance."""
    return PostClassifier()
