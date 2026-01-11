# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Reddit Signal/Noise Analyzer** - A Python CLI application that analyzes Reddit posts from Claude/LLM-related subreddits, automatically classifies them into useful categories (Signal vs Noise), and generates reports with metrics.

**Problem solved**: Claude/LLM subreddits contain mixed content - from useful techniques to unfounded mystical theories. This tool automates the filtering process.

## Development Commands

### Environment Setup
```bash
# Activate virtual environment (Python 3.11+)
source .venv/bin/activate

# Install dependencies (once pyproject.toml is created)
pip install -e .

# Run the CLI (once implemented)
reddit-analyzer --help
```

### Primary CLI Commands (planned)
```bash
# Scan a subreddit
reddit-analyzer scan ClaudeAI --limit 50 --time-filter week

# With exports
reddit-analyzer scan ClaudeAI --export-json --export-html

# Bypass cache
reddit-analyzer scan ClaudeAI --no-cache
```

## Architecture Overview

This is a pipeline-based architecture:

```
CLI (Typer)
    ↓
┌─────────┬──────────┐
│         │          │
Scraper → Classifier → Analyzer → Reporter
(PRAW)   (Claude)    (Stats)    (Rich/JSON)
    ↓         ↓
  Cache    Cache
```

**Data Flow:**
1. **Scraper** (scraper.py): Fetches Reddit posts using PRAW API, normalizes to RedditPost model
2. **Classifier** (classifier.py): Sends batches of 20 posts to Claude Haiku for classification
3. **Analyzer** (analyzer.py): Generates metrics (signal ratio, red flags distribution, top posts)
4. **Reporter** (reporter.py): Renders output using Rich for terminal or exports to JSON/HTML

**Key Design Decisions:**
- **Batch Processing**: 20 posts per Claude API call to minimize cost (~$0.001 per post)
- **Aggressive Caching**: Posts are immutable, cache by (subreddit, params, date) with 24hr TTL
- **Text Truncation**: Selftext limited to 5000/MAX_LINES_ARTICLE chars for classification to reduce tokens
- **Haiku Model**: Cost-effective choice for classification tasks

## Critical Configuration

### Environment Variables (.env)
Required API credentials:

```bash
# Reddit API (create app at https://www.reddit.com/prefs/apps)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=reddit-analyzer/1.0 by /u/your_username

# Anthropic API (get from https://console.anthropic.com)
ANTHROPIC_API_KEY=sk-ant-api03-...
```

**Important**: Reddit app should be type "script" (personal use). Anthropic API access is separate from Claude Pro subscription - new accounts get $5 free credits.

### Settings (config.py with pydantic-settings)
- `anthropic_model`: "claude-haiku-4-5-20251001"
- `default_batch_size`: 20 posts per Claude request
- `cache_ttl_hours`: 24
- Output paths: outputs/{cache,classifications,reports}

## Data Models & Classification System

### Core Enums (core/enums.py)

**CategoryEnum** - Post classification categories:

**SIGNAL** (useful content):
- `technical`: Prompts, workflows, functional code
- `troubleshooting`: Real problems + solutions
- `research_verified`: Papers/experiments with verifiable sources

**NOISE** (problematic content):
- `mystical`: Consciousness claims without scientific evidence
- `unverified_claim`: Technical assertions without sources
- `engagement_bait`: Clickbait content ("You won't believe...")

**META**:
- `community`: Subreddit discussion
- `meme`: Humor/entertainment

**OTHER**:
- `outlier`: Doesn't fit clearly

### Red Flags Detection

The classifier detects these problematic patterns:
- `no_source`: Scientific claims without citation (e.g., "researchers say", "studies show")
- `link_in_bio`: External content promotion
- `mystical_language`: "consciousness emerged", "spiritual", "awakening"
- `precise_numbers_no_source`: Specific metrics without citation (e.g., "95.7 times", "2,725 emojis")
- `cannot_explain`: "researchers can't explain", "mysterious"
- `sensationalist`: "shocking discovery", "you won't believe"

### Signal Ratio Calculation

```python
signal_ratio = (TECHNICAL + TROUBLESHOOTING + RESEARCH_VERIFIED) / total_posts
```

Green threshold: >60% signal indicates healthy subreddit content quality.

## Implementation Constraints

### API Rate Limits & Costs
- **Reddit**: 60 req/min without OAuth, 600/min with OAuth → mandatory caching
- **Claude API**: ~$0.10 per 100 posts (Haiku at $0.80/1M input tokens)
- **Anthropic**: 50 requests/min on free tier

### Technical Gotchas
1. **Selftext length**: Some posts exceed 10k chars → must truncate to 5000 for classification
2. **JSON parsing**: Claude may fail generating valid JSON → implement retry logic with validation
3. **Batch processing**: Always process in batches of 20 to optimize cost vs latency
4. **Reddit auth**: Requires creating Reddit app (see previous.md for setup instructions)

### Error Handling Requirements
- Exponential backoff for rate limit retries
- Pydantic validation for all Claude JSON responses
- Graceful degradation if classification fails (mark as `outlier`)

## Classification Prompt

Location: `prompts/classify_posts.md`

The prompt instructs Claude to return a JSON array with one object per post:

```json
[
  {
    "post_id": "abc123",
    "category": "mystical",
    "confidence": 0.95,
    "red_flags": ["no_source", "precise_numbers_no_source"],
    "reasoning": "Brief explanation of classification decision"
  }
]
```

Template variable: `{posts_json}` - array of RedditPost objects to classify.

## Testing Strategy

### Manual Testing (priority for MVP)
1. Test with `r/test` (small subreddit)
2. Test with 10 posts from `r/ClaudeAI`
3. Manual validation of classifications against expected categories
4. Verify cache works (second run should be instant)

### Unit Tests (post-MVP)
- Use fixtures with real posts (anonymized) in tests/fixtures/sample_posts.json
- Mock Reddit API responses
- Mock Claude API with pre-recorded classifications

### Success Criteria for MVP
1. Scans 50-100 posts from a subreddit
2. Classifies with >80% accuracy (manual validation on sample)
3. Generates readable terminal report using Rich
4. Exports valid JSON
5. Caching works (instant second execution)

## Project Structure

```
reddit-analyzer/
├── pyproject.toml              # Project dependencies and metadata
├── .env                        # API credentials (gitignored)
├── .env.example               # Template for credentials
│
├── src/claude_redditor/
│   ├── cli.py                 # Typer CLI entry point
│   ├── config.py              # pydantic-settings configuration
│   ├── core/
│   │   ├── models.py          # RedditPost, Classification, AnalysisReport
│   │   └── enums.py           # CategoryEnum, red flag constants
│   ├── scraper.py             # Reddit data fetching (PRAW)
│   ├── classifier.py          # Claude batch classification
│   ├── analyzer.py            # Metrics generation
│   ├── reporter.py            # Terminal/JSON/HTML output
│   └── cache.py               # Cache management
│
├── prompts/
│   └── classify_posts.md      # Claude classification system prompt
│
├── outputs/
│   ├── cache/                 # Cached Reddit responses
│   ├── classifications/       # Cached Claude classifications
│   └── reports/               # Generated reports
│
└── tests/
    └── fixtures/
        └── sample_posts.json  # Test data
```

## Implementation Phases

### Phase 1: Foundation (start here)
1. Setup pyproject.toml with dependencies (praw, anthropic, typer, rich, pandas, pydantic, pydantic-settings)
2. Create directory structure
3. Implement config.py with Settings class
4. Implement core/models.py and core/enums.py
5. Basic scraper.py (fetch 10 test posts, no cache yet)
6. Manual test: scrape and print posts

### Phase 2: Classification
1. Write prompts/classify_posts.md
2. Implement classifier.py with batch processing
3. Add red flags detection logic
4. Implement cache.py for classifications
5. Test classification accuracy on sample posts

### Phase 3: Analysis & Output
1. Implement analyzer.py (metrics, stats, signal ratio)
2. Implement reporter.py with Rich formatting (tables, panels, colors)
3. Add JSON export functionality
4. Implement CLI commands in cli.py
5. Add progress indicators (Rich progress bars)

### Phase 4: Polish
1. Robust error handling (rate limits, API failures)
2. Retry logic with exponential backoff
3. README with usage examples
4. Basic tests with fixtures

## Key Dependencies

```toml
dependencies = [
    "praw>=7.7.1",              # Reddit API wrapper
    "anthropic>=0.39.0",        # Claude API
    "typer>=0.12.0",            # CLI framework
    "rich>=13.7.0",             # Terminal formatting
    "pandas>=2.2.0",            # Data analysis
    "pydantic>=2.10.0",         # Data validation
    "pydantic-settings>=2.6.0", # Settings management
]
```

Entry point: `reddit-analyzer = "claude_redditor.cli:app"`
