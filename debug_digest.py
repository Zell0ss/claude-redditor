#!/usr/bin/env python3
"""
Debug script for digest generation.
Run this in VSCode debugger to step through the code.

Usage:
    1. Open this file in VSCode
    2. Set breakpoints where needed
    3. Run with F5 (Python debugger)
"""

import sys
import json
sys.path.insert(0, 'src')

from claude_redditor.config import settings
from claude_redditor.db.connection import DatabaseConnection
from claude_redditor.db.repository import Repository

# Configuration
PROJECT = "claudeia"
LIMIT = 2  # Start with just 2 posts for debugging

print("=" * 60)
print("DEBUG DIGEST GENERATOR")
print("=" * 60)

# Step 1: Connect to database
print("\n[Step 1] Connecting to database...")
db = DatabaseConnection(settings)
repo = Repository(db)
print("✓ Database connected")

# Step 2: Get signal posts
print(f"\n[Step 2] Getting signal posts for project '{PROJECT}'...")
posts_data = repo.get_signal_posts_for_digest(
    project=PROJECT,
    limit=LIMIT,
    min_confidence=0.7
)

print(f"✓ Found {len(posts_data)} posts")

if not posts_data:
    print("No posts found! Exiting.")
    sys.exit(0)

# Show first post
first_post = posts_data[0]
print(f"\nFirst post:")
print(f"  ID: {first_post['post']['id']}")
print(f"  Title: {first_post['post']['title'][:60]}...")
print(f"  Category: {first_post['classification']['category']}")
print(f"  Truncated: {first_post['selftext_truncated']}")

# Step 3: Load prompt template
print("\n[Step 3] Loading prompt template...")
from pathlib import Path
prompt_path = Path('prompts/digest_article.md')
prompt_template = prompt_path.read_text()
print(f"✓ Loaded template ({len(prompt_template)} chars)")

# Step 4: Prepare prompt for first post
print("\n[Step 4] Preparing prompt for first post...")
post = first_post['post']
classification = first_post['classification']
content = post.get('selftext', '') or 'No content available'

# Determine source
post_id = post.get('id', '')
if post_id.startswith('reddit_'):
    source = 'Reddit'
elif post_id.startswith('hn_'):
    source = 'HackerNews'
else:
    source = 'Unknown'

prompt = prompt_template.format(
    title=post.get('title', 'Sin título'),
    source=source,
    subreddit=post.get('subreddit', 'N/A') or 'N/A',
    author=post.get('author', 'unknown') or 'unknown',
    score=post.get('score', 0) or 0,
    num_comments=post.get('num_comments', 0) or 0,
    category=classification.get('category', 'technical'),
    url=post.get('url', ''),
    content=content[:5000]
)

print(f"✓ Prompt prepared ({len(prompt)} chars)")
print("\n--- PROMPT PREVIEW (first 500 chars) ---")
print(prompt[:500])
print("--- END PREVIEW ---")

# Step 5: Call Claude API
print("\n[Step 5] Calling Claude API...")
from anthropic import Anthropic

client = Anthropic(api_key=settings.anthropic_api_key)

response = client.messages.create(
    model=settings.anthropic_model,
    max_tokens=4096,
    messages=[{"role": "user", "content": prompt}]
)

response_text = response.content[0].text

print(f"✓ Got response ({len(response_text)} chars)")
print("\n--- RAW RESPONSE ---")
print(response_text)
print("--- END RAW RESPONSE ---")

# Step 6: Try to extract JSON
print("\n[Step 6] Extracting JSON from response...")
import re

# Method 1: Try code block pattern (greedy match)
code_block_pattern = r'```(?:json)?\s*(\{.*\})\s*```'
match = re.search(code_block_pattern, response_text, re.DOTALL)

if match:
    print("Found JSON in code block")
    json_str = match.group(1)
else:
    print("No code block found, trying brace-matching extraction")

    # Find JSON using brace matching
    json_start = response_text.find('{')
    if json_start == -1:
        print("ERROR: No opening brace found!")
        json_str = None
    else:
        # Count braces to find matching close
        brace_count = 0
        json_end = -1
        in_string = False
        escape_next = False

        for i, char in enumerate(response_text[json_start:], start=json_start):
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
            json_str = response_text[json_start:json_end]
            print(f"Found JSON at positions {json_start} to {json_end}")
        else:
            print("ERROR: No matching closing brace found!")
            json_str = None

if json_str:
    print(f"\n--- EXTRACTED JSON STRING ({len(json_str)} chars) ---")
    print(json_str[:1000])
    if len(json_str) > 1000:
        print("... (truncated)")
    print("--- END JSON STRING ---")

    # Try to parse
    print("\n[Step 7] Parsing JSON...")
    try:
        article = json.loads(json_str)
        print("✓ JSON parsed successfully!")
        print(f"\nKeys found: {list(article.keys())}")
        print(f"\nArticle title: {article.get('article_title', 'N/A')}")
        print(f"Article body length: {len(article.get('article_body', ''))}")
        print(f"Commentary length: {len(article.get('radio_commentary', ''))}")
    except json.JSONDecodeError as e:
        print(f"✗ JSON parse error: {e}")
        print(f"\nError position: {e.pos}")
        print(f"Error line: {e.lineno}, col: {e.colno}")

        # Show context around error
        if e.pos:
            start = max(0, e.pos - 50)
            end = min(len(json_str), e.pos + 50)
            print(f"\nContext around error:")
            print(f"'{json_str[start:end]}'")
            print(f"      {'':>{e.pos - start}}^")

print("\n" + "=" * 60)
print("DEBUG COMPLETE")
print("=" * 60)
