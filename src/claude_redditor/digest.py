"""Daily digest generation for ClaudeRedditor."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from anthropic import Anthropic
from rich.progress import Progress, SpinnerColumn, TextColumn
import logging

from .config import settings
from .projects import project_loader
from .db.repository import Repository
from .content_fetcher import fetch_full_content

logger = logging.getLogger(__name__)


class DigestGenerator:
    """Generate daily digest of top signal posts."""

    def __init__(self, repo: Repository, project: str = 'claudeia'):
        """
        Initialize digest generator.

        Args:
            repo: Repository instance for database access
            project: Project name for loading prompts
        """
        self.repo = repo
        self.project = project
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self._prompt_cache: Dict[str, str] = {}

    def _get_prompt_template(self, project: str) -> str:
        """Load the digest prompt template for a project."""
        if project not in self._prompt_cache:
            self._prompt_cache[project] = project_loader.get_prompt(project, 'digest')
        return self._prompt_cache[project]

    def generate(
        self,
        project: str,
        limit: int = 15,
        output_dir: Optional[Path] = None,
        show_progress: bool = True
    ) -> Path:
        """
        Generate daily digest markdown file.

        Args:
            project: Project name (e.g., 'claudeia')
            limit: Maximum number of posts to include
            output_dir: Output directory (defaults to outputs/digests)
            show_progress: Show progress bar

        Returns:
            Path to generated markdown file

        Raises:
            ValueError: If no signal posts are available
        """
        # 1. Get signal posts not yet sent
        posts_data = self.repo.get_signal_posts_for_digest(
            project=project,
            limit=limit
        )

        if not posts_data:
            raise ValueError(f"No signal posts available for digest in project '{project}'")

        logger.info(f"Found {len(posts_data)} signal posts for digest")

        # 2. Process each post
        articles = []
        processed_ids = []

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("Generating articles...", total=len(posts_data))

                for item in posts_data:
                    post = item['post']
                    classification = item['classification']

                    progress.update(task, description=f"Processing: {post.get('title', '')[:40]}...")

                    article = self._process_post(item)

                    if article:
                        articles.append({
                            'post': post,
                            'article': article
                        })
                        processed_ids.append(post['id'])

                    progress.advance(task)
        else:
            for item in posts_data:
                article = self._process_post(item)
                if article:
                    articles.append({
                        'post': item['post'],
                        'article': article
                    })
                    processed_ids.append(item['post']['id'])

        if not articles:
            raise ValueError("Failed to generate any articles. Check API connectivity.")

        # 3. Generate markdown digest
        output_path = self._write_markdown(
            articles=articles,
            project=project,
            output_dir=output_dir
        )

        # 4. Mark posts as sent
        self.repo.mark_posts_as_sent_in_digest(processed_ids, project)

        logger.info(f"Digest generated: {output_path} ({len(articles)} articles)")
        return output_path

    def generate_both(
        self,
        project: str,
        limit: int = 15,
        output_dir: Optional[Path] = None,
        show_progress: bool = True
    ) -> tuple[Path, Path]:
        """
        Generate both markdown and JSON digests from the same posts.

        This ensures both formats have the same posts in the same order,
        and marks posts as sent only after both are generated.

        Args:
            project: Project name (e.g., 'claudeia')
            limit: Maximum number of posts to include
            output_dir: Output directory for markdown (defaults to outputs/digests)
            show_progress: Show progress bar

        Returns:
            Tuple of (markdown_path, json_path)
        """
        # 1. Get signal posts not yet sent (shared between both formats)
        posts_data = self.repo.get_signal_posts_for_digest(
            project=project,
            limit=limit
        )

        if not posts_data:
            raise ValueError(f"No signal posts available for digest in project '{project}'")

        logger.info(f"Found {len(posts_data)} signal posts for digest (both formats)")

        # 2. Process posts for markdown (generate articles via Claude)
        articles = []
        processed_ids = []

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("Generating articles...", total=len(posts_data))

                for item in posts_data:
                    post = item['post']
                    progress.update(task, description=f"Processing: {post.get('title', '')[:40]}...")

                    article = self._process_post(item)

                    if article:
                        articles.append({
                            'post': post,
                            'article': article,
                            'item': item  # Keep original item for JSON
                        })
                        processed_ids.append(post['id'])

                    progress.advance(task)
        else:
            for item in posts_data:
                article = self._process_post(item)
                if article:
                    articles.append({
                        'post': item['post'],
                        'article': article,
                        'item': item
                    })
                    processed_ids.append(item['post']['id'])

        if not articles:
            raise ValueError("Failed to generate any articles. Check API connectivity.")

        # 3. Generate markdown
        md_path = self._write_markdown(
            articles=articles,
            project=project,
            output_dir=output_dir
        )

        # 4. Extract sequence number from markdown filename to use for JSON
        # Markdown: digest_{project}_{date}_{NN}.md -> extract NN
        try:
            seq_num = int(md_path.stem.split('_')[-1])
        except (ValueError, IndexError):
            seq_num = 1

        # 5. Generate JSON from the same posts (same order, same sequence number)
        date_str = datetime.now().strftime('%Y-%m-%d')
        stories = []
        for idx, art in enumerate(articles, 1):
            story = self._build_story(art['item'], date_str, idx)
            stories.append(story)

        # Write JSON with SAME sequence number as markdown
        json_output_dir = settings.output_dir / 'web'
        json_output_dir.mkdir(parents=True, exist_ok=True)

        digest_id = f"{date_str}_{seq_num:02d}"

        for idx, story in enumerate(stories, 1):
            story["id"] = f"{date_str}_{seq_num:02d}_{idx:03d}"

        digest_data = {
            "digest_id": digest_id,
            "generated_at": datetime.now().isoformat() + "Z",
            "project": project,
            "story_count": len(stories),
            "stories": stories
        }

        json_path = json_output_dir / f"{project}_{date_str}_{seq_num:02d}.json"
        json_path.write_text(json.dumps(digest_data, indent=2, ensure_ascii=False), encoding='utf-8')

        # Update latest.json symlink
        latest_path = json_output_dir / "latest.json"
        if latest_path.exists() or latest_path.is_symlink():
            latest_path.unlink()
        latest_path.symlink_to(json_path.name)

        # 5. Mark posts as sent (only after both are generated)
        self.repo.mark_posts_as_sent_in_digest(processed_ids, project)

        logger.info(f"Both digests generated: {md_path}, {json_path} ({len(articles)} articles)")
        return md_path, json_path

    def _process_post(self, item: Dict) -> Optional[Dict]:
        """
        Process a single post: fetch content if needed and generate article.

        Args:
            item: Dict with 'post', 'classification', 'selftext_truncated'

        Returns:
            Article dict or None if failed
        """
        post = item['post']
        classification = item['classification']

        # Fetch full content if truncated
        content = post.get('selftext', '') or ''
        if item['selftext_truncated'] and post.get('url'):
            logger.info(f"Fetching full content for truncated post: {post['id']}")
            full_content = fetch_full_content(post['url'])
            if full_content:
                content = full_content

        # Generate article via Claude
        return self._generate_article(
            post=post,
            classification=classification,
            content=content
        )

    def _generate_article(
        self,
        post: Dict,
        classification: Dict,
        content: str
    ) -> Optional[Dict]:
        """
        Generate article and commentary for a single post via Claude API.

        Args:
            post: Post dict
            classification: Classification dict
            content: Full content text

        Returns:
            Dict with article_title, article_body, radio_commentary or None
        """
        # Determine source type
        post_id = post.get('id', '')
        if post_id.startswith('reddit_'):
            source = 'Reddit'
        elif post_id.startswith('hn_'):
            source = 'HackerNews'
        else:
            source = 'Unknown'

        # Prepare prompt using project-specific template
        prompt_template = self._get_prompt_template(self.project)
        prompt = prompt_template.format(
            title=post.get('title', 'Sin título'),
            source=source,
            subreddit=post.get('subreddit', 'N/A') or 'N/A',
            author=post.get('author', 'unknown') or 'unknown',
            score=post.get('score', 0) or 0,
            num_comments=post.get('num_comments', 0) or 0,
            category=classification.get('category', 'technical'),
            url=post.get('url', ''),
            content=content[:10000] if content else 'No content available'
        )

        try:
            response = self.client.messages.create(
                model=settings.anthropic_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Extract JSON from response - handle markdown code blocks
            article = self._extract_json(response_text)

            if article:
                # Validate required fields
                if all(k in article for k in ['article_title', 'article_body', 'radio_commentary']):
                    logger.debug(f"Generated article for {post.get('id')}")
                    return article
                else:
                    logger.warning(f"Incomplete article response for {post.get('id')}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error for {post.get('id')}: {e}")
        except Exception as e:
            logger.error(f"Failed to generate article for {post.get('id')}: {e}")

        return None

    def _extract_json(self, text: str) -> Optional[Dict]:
        """
        Extract JSON from Claude response, handling various formats.

        Handles:
        - Raw JSON
        - JSON wrapped in ```json ... ``` code blocks
        - JSON wrapped in ``` ... ``` code blocks
        """
        import re

        # Try to find JSON in code block first (greedy match for nested braces)
        # Look for opening ``` with optional json, then capture until closing ```
        code_block_pattern = r'```(?:json)?\s*(\{.*\})\s*```'
        match = re.search(code_block_pattern, text, re.DOTALL)
        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Try cleaning the extracted string
                pass

        # Fallback: find raw JSON object using brace matching
        json_start = text.find('{')
        if json_start == -1:
            return None

        # Find the matching closing brace by counting
        brace_count = 0
        json_end = -1
        in_string = False
        escape_next = False

        for i, char in enumerate(text[json_start:], start=json_start):
            if escape_next:
                escape_next = False
                continue
            if char == '\\' and in_string:
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break

        if json_end > json_start:
            json_str = text[json_start:json_end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error: {e}")
                # Log the problematic area for debugging
                if hasattr(e, 'pos') and e.pos:
                    start = max(0, e.pos - 30)
                    end = min(len(json_str), e.pos + 30)
                    logger.warning(f"Error context: ...{json_str[start:end]}...")

        return None

    def _write_markdown(
        self,
        articles: List[Dict],
        project: str,
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        Write digest to markdown file.

        Args:
            articles: List of {'post': ..., 'article': ...}
            project: Project name
            output_dir: Output directory

        Returns:
            Path to generated file
        """
        if output_dir is None:
            output_dir = settings.output_dir / 'digests'
        output_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime('%Y-%m-%d')

        # Find next available sequence number for today
        existing = list(output_dir.glob(f"digest_{project}_{date_str}_*.md"))
        if existing:
            # Extract numbers and find max
            numbers = []
            for f in existing:
                try:
                    num = int(f.stem.split('_')[-1])
                    numbers.append(num)
                except ValueError:
                    pass
            next_num = max(numbers) + 1 if numbers else 1
        else:
            next_num = 1

        filename = f"digest_{project}_{date_str}_{next_num:02d}.md"
        output_path = output_dir / filename

        # Build markdown content
        lines = [
            f"# La Gaceta IA - {date_str}",
            "",
            f"*Resumen diario de las {len(articles)} noticias mas relevantes sobre Inteligencia Artificial*",
            "",
            "---",
            ""
        ]

        for i, item in enumerate(articles, 1):
            post = item['post']
            article = item['article']

            # Build story ID: {date}_{seq}_{idx}
            story_id = f"{date_str}_{next_num:02d}_{i:03d}"

            # Article section with full story ID in title
            lines.extend([
                f"## {story_id}. {article.get('article_title', post.get('title', 'Sin titulo'))}",
                "",
                article.get('article_body', ''),
                "",
                f"**Fuente:** [{post.get('title', 'Ver post original')}]({post.get('url', '#')})",
                "",
                "### Comentario del presentador",
                "",
                article.get('radio_commentary', ''),
                "",
                "---",
                ""
            ])

        # Footer
        lines.extend([
            "",
            f"*Generado automaticamente por ClaudeRedditor - Proyecto: {project}*",
            f"*Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"
        ])

        output_path.write_text('\n'.join(lines), encoding='utf-8')
        return output_path

    def generate_json(
        self,
        project: str,
        limit: int = 15,
        show_progress: bool = True
    ) -> Path:
        """
        Generate JSON digest for web consumption.

        Args:
            project: Project name (e.g., 'claudeia')
            limit: Maximum number of posts to include
            show_progress: Show progress bar

        Returns:
            Path to generated JSON file
        """
        # 1. Get signal posts not yet sent
        posts_data = self.repo.get_signal_posts_for_digest(
            project=project,
            limit=limit
        )

        if not posts_data:
            raise ValueError(f"No signal posts available for JSON digest in project '{project}'")

        logger.info(f"Found {len(posts_data)} signal posts for JSON digest")

        date_str = datetime.now().strftime('%Y-%m-%d')

        # 2. Build stories array
        stories = []

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("Building JSON...", total=len(posts_data))

                for idx, item in enumerate(posts_data, 1):
                    story = self._build_story(item, date_str, idx)
                    stories.append(story)
                    progress.advance(task)
        else:
            for idx, item in enumerate(posts_data, 1):
                story = self._build_story(item, date_str, idx)
                stories.append(story)

        # 3. Write to outputs/web/ with sequential numbering
        output_dir = settings.output_dir / 'web'
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find next available sequence number for today (same logic as markdown)
        existing = list(output_dir.glob(f"{project}_{date_str}_*.json"))
        if existing:
            numbers = []
            for f in existing:
                try:
                    # Extract NN from {project}_{date}_{NN}.json
                    num = int(f.stem.split('_')[-1])
                    numbers.append(num)
                except ValueError:
                    pass
            next_num = max(numbers) + 1 if numbers else 1
        else:
            next_num = 1

        # Build digest ID with sequence number
        digest_id = f"{date_str}_{next_num:02d}"

        # Update story IDs to match digest sequence
        for idx, story in enumerate(stories, 1):
            story["id"] = f"{date_str}_{next_num:02d}_{idx:03d}"

        # 4. Build digest JSON
        digest_data = {
            "digest_id": digest_id,
            "generated_at": datetime.now().isoformat() + "Z",
            "project": project,
            "story_count": len(stories),
            "stories": stories
        }

        output_path = output_dir / f"{project}_{date_str}_{next_num:02d}.json"
        output_path.write_text(json.dumps(digest_data, indent=2, ensure_ascii=False), encoding='utf-8')

        # 5. Update latest.json symlink
        latest_path = output_dir / "latest.json"
        if latest_path.exists() or latest_path.is_symlink():
            latest_path.unlink()
        latest_path.symlink_to(output_path.name)

        logger.info(f"JSON digest generated: {output_path}")
        return output_path

    def _build_story(self, item: Dict, date_str: str, idx: int) -> Dict:
        """
        Build a single story dict for JSON output.

        Args:
            item: Dict with 'post', 'classification', 'selftext_truncated'
            date_str: Date string (YYYY-MM-DD)
            idx: Story index (1-based)

        Returns:
            Story dict for JSON
        """
        post = item['post']
        classification = item['classification']

        # Determine source
        post_id = post.get('id', '')
        if post_id.startswith('reddit_'):
            source = f"r/{post.get('subreddit', 'unknown')}"
        elif post_id.startswith('hn_'):
            source = "HackerNews"
        else:
            source = "Unknown"

        # Story ID will be set later with digest sequence number
        return {
            "id": "",  # Placeholder, updated in generate_json with digest sequence
            "post_id": post_id,  # Original post ID for traceability (reddit_abc123 or hn_12345678)
            "title": post.get('title', ''),
            "source": source,
            "author": post.get('author', 'unknown'),
            "url": post.get('url', ''),
            "score": post.get('score', 0),
            "num_comments": post.get('num_comments', 0),
            "category": classification.get('category', 'technical'),
            "confidence": classification.get('confidence', 0),
            "topic_tags": classification.get('topic_tags', []),
            "format_tag": classification.get('format_tag'),
            "red_flags": classification.get('red_flags', []),
            "reasoning": classification.get('reasoning', '')
        }
