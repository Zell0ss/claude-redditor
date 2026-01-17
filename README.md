# Multi-Source Signal/Noise Analyzer

**Production-ready CLI tool** to analyze posts from Reddit and HackerNews, automatically classify them as Signal vs Noise using Claude AI, and generate insightful reports.

## Table of Contents

- [Problem Solved](#problem-solved)
- [Status: ✅ Complete & Functional](#status--complete--functional)
- [Features](#features)
- [Quick Start](#quick-start)
  - [1. Installation](#1-installation)
  - [2. Configuration](#2-configuration)
  - [3. Usage](#3-usage)
- [Project Status](#project-status)
- [CLI Commands](#cli-commands)
  - [`scan` - Analyze a Subreddit](#scan---analyze-a-subreddit)
  - [`scan-hn` - Analyze HackerNews](#scan-hn---analyze-hackernews)
  - [`compare` - Compare Subreddits](#compare---compare-subreddits)
  - [`digest` - Generate Daily Digest](#digest---generate-daily-digest)
  - [`config` - Show Configuration](#config---show-configuration)
  - [`init-db` - Initialize Database](#init-db---initialize-database)
  - [`history` - View Scan History](#history---view-scan-history)
  - [`cache-stats` - Cache Statistics](#cache-stats---cache-statistics)
  - [`version` - Version Info](#version---version-info)
- [Architecture](#architecture)
  - [Dual-Mode Scraper](#dual-mode-scraper)
- [MariaDB Cache Layer](#mariadb-cache-layer)
  - [Database Schema](#database-schema)
  - [Cache Behavior](#cache-behavior)
  - [Setup Instructions](#setup-instructions)
- [Classification System](#classification-system)
  - [Classification Criteria](#classification-criteria)
  - [Categories](#categories)
  - [Red Flags](#red-flags)
  - [Signal Ratio](#signal-ratio)
- [Tech Stack](#tech-stack)
- [Development](#development)
  - [Project Structure](#project-structure)
  - [Testing](#testing)
  - [Makefile Commands](#makefile-commands)
- [Cost Estimates](#cost-estimates)
- [Usage Examples](#usage-examples)
- [Extending the Project](#extending-the-project)
- [License](#license)

## Problem Solved

Claude/LLM communities (Reddit subreddits and HackerNews) contain mixed content - from useful technical guides to unfounded mystical theories. This tool automates the filtering process using Claude AI to classify posts and identify red flags.

**Sources Supported:**
- **Reddit**: Subreddit-based analysis (r/ClaudeAI, r/LocalLLaMA, etc.)
- **HackerNews**: Keyword-based filtering for relevant discussions

## Status: ✅ Complete & Functional

All core features implemented and tested. Ready for immediate use.

```
┌────────────────────────────────────────────────────────────┐
│  📊 Multi-Source Signal/Noise Analyzer                     │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│                                                            │
│  🎯 Reddit + HN → 🤖 Classify with Claude AI              │
│  📈 Generate metrics → 📊 Beautiful reports               │
│                                                            │
│  ✅ 2 Sources  ✅ 10 Categories  ✅ 6 Red Flags           │
│  ✅ Multi-Project  ✅ Batch Processing  ✅ Zero Auth      │
│  ✅ MariaDB Cache  ✅ 70-80% Cost Reduction               │
└────────────────────────────────────────────────────────────┘
```

## Features

- **Multi-Project Architecture**: Run independent daily extractions for different content domains (AI/podcast, wine/blog, etc.) with isolated data
- **Multi-Source Support**: Analyze posts from both Reddit and HackerNews with unified classification
- **Dual-Mode Reddit Scraping**: RSS mode (no auth required) or PRAW mode (with Reddit credentials) with automatic fallback
- **HackerNews Integration**: Firebase API with keyword filtering (500 req/min, no auth needed)
- **AI-Powered Classification**: Uses Claude Haiku 4.5 to classify posts into 10 categories (Signal/Noise/Meta/Other/Unrelated)
- **Daily Digest Generation**: Automatically generates newsletter-ready articles in Spanish from signal posts
- **Topic-Aware Filtering**: UNRELATED category filters off-topic posts based on configured TOPIC
- **Batch Processing**: Efficient batch classification (20 posts per API call) minimizes costs (~$0.10 per 100 posts)
- **MariaDB Cache Layer**: Persistent cache that avoids re-classifying posts, reducing API costs by 70-80%
- **Historical Tracking**: Scan history with metrics evolution over time (tracks both sources and projects)
- **Red Flag Detection**: Identifies 6 problematic patterns (unsourced claims, sensationalism, mystical language, etc.)
- **Rich Terminal Output**: Beautiful CLI reports with tables, charts, and color-coded categories
- **Multi-Subreddit Analysis**: Compare signal ratios across multiple subreddits simultaneously
- **Export Options**: JSON export for further analysis
- **Comprehensive Testing**: 7 test scripts covering all major components
- **Easy Management**: Makefile with convenient commands for common tasks

## Quick Start

### 1. Installation

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

### 2. Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

**Required**: Add your Anthropic API key to `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-your_key_here
```

**Multi-Project Support**: Configure multiple independent projects with prefixed variables:

```bash
# Project: ClaudeIA (AI/LLM content for podcast)
CLAUDEIA_TOPIC="AI and Large Language Models, particularly Claude"
CLAUDEIA_SUBREDDITS=ClaudeAI,Claude,ClaudeCode,ClaudeExplorers
CLAUDEIA_HN_KEYWORDS=claude,anthropic,ai,llm

# Project: WineWorld (Wine industry for blog)
WINEWORLD_TOPIC="Wine industry, viticulture, wine tasting"
WINEWORLD_SUBREDDITS=wine,winemaking,sommelier
WINEWORLD_HN_KEYWORDS=wine,viticulture,vineyard,sommelier
```

**Legacy (backward compatible)**: Single project configuration:
```bash
SUBREDDITS=ClaudeAI,Claude,ClaudeCode
HN_DEFAULT_KEYWORDS=claude,anthropic,ai
```

**Optional**: Add Reddit credentials for faster scraping (60 req/min vs 10 req/min):
```bash
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
```

Get Reddit credentials at: https://www.reddit.com/prefs/apps (create "script" type app)

**Optional but Recommended**: Enable MariaDB cache for cost savings:
```bash
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=reddit_analyzer
```

Then initialize the database:
```bash
./reddit-analyzer init-db
```

### 3. Usage

```bash
# Reddit: Analyze a single subreddit (uses default project)
./reddit-analyzer scan ClaudeAI --limit 50

# Multi-Project: Analyze ClaudeIA project (AI content)
./reddit-analyzer scan all --project claudeia --limit 50

# Multi-Project: Analyze WineWorld project (wine content)
./reddit-analyzer scan all --project wineworld --limit 50

# Reddit: Compare multiple subreddits within a project
./reddit-analyzer compare --project claudeia --limit 20

# HackerNews: Scan with specific keywords
./reddit-analyzer scan-hn -k claude -k anthropic --limit 20

# HackerNews: Use project-specific keywords
./reddit-analyzer scan-hn --project wineworld --limit 50

# Show configuration
./reddit-analyzer config

# Initialize database (if using cache)
./reddit-analyzer init-db

# View scan history
./reddit-analyzer history

# View cache statistics
./reddit-analyzer cache-stats

# Show version
./reddit-analyzer version
```

## Multi-Project Support

The analyzer supports running multiple independent projects with isolated data and configurations. Perfect for:
- **Content diversification**: AI podcast + Wine blog from the same tool
- **Team isolation**: Different teams analyzing different topics
- **A/B testing**: Compare classification strategies across projects

### Key Features

- **Project Isolation**: Complete data separation in database (`project` column)
- **Independent Configs**: Each project has its own TOPIC, SUBREDDITS, HN_KEYWORDS
- **Shared Infrastructure**: Single API key, database, and codebase
- **Backward Compatible**: Existing scans continue working (assigned to "default" project)

### Configuration Example

```bash
# In .env file
CLAUDEIA_TOPIC="AI and Large Language Models"
CLAUDEIA_SUBREDDITS=ClaudeAI,Claude,ClaudeCode
CLAUDEIA_HN_KEYWORDS=claude,anthropic,ai,llm

WINEWORLD_TOPIC="Wine industry and viticulture"
WINEWORLD_SUBREDDITS=wine,winemaking,sommelier
WINEWORLD_HN_KEYWORDS=wine,viticulture,vineyard
```

### Usage Examples

```bash
# Scan ClaudeIA project (AI content)
./reddit-analyzer scan all --project claudeia --limit 50
./reddit-analyzer scan-hn --project claudeia --limit 100

# Scan WineWorld project (wine content)
./reddit-analyzer scan all --project wineworld --limit 50
./reddit-analyzer scan-hn --project wineworld --limit 100

# View project-specific history
./reddit-analyzer history --project claudeia --limit 20
./reddit-analyzer history --project wineworld --limit 20

# Check cache stats per project
./reddit-analyzer cache-stats --project claudeia
./reddit-analyzer cache-stats --project wineworld
```

### Database Migration

If upgrading from a previous version, run the migration:

```bash
mysql -u your_user -p reddit_analyzer < src/claude_redditor/db/migrations/004_add_project_column.sql
```

All existing data will be assigned to the "default" project automatically.

## Project Status

**✅ PROJECT COMPLETE - Production Ready**

**Phase 1: Foundation** ✅
- [x] Project structure with proper package organization
- [x] Core data models (RedditPost, Classification, AnalysisReport)
- [x] Configuration management (pydantic-settings)
- [x] Dual-mode scraper (RSS/PRAW) with automatic fallback
- [x] Comprehensive testing suite

**Phase 2: Classification** ✅
- [x] Classification prompt with detailed rules (prompts/classify_posts.md)
- [x] Classifier with batch processing (20 posts per request)
- [x] Red flags detection (6 patterns)
- [x] Pydantic validation and error handling
- [x] Integration with Claude Haiku 4.5

**Phase 3: Analysis & Output** ✅
- [x] Analysis engine (metrics, signal ratio, health grades)
- [x] Reporter (Rich terminal output with tables and charts)
- [x] JSON export functionality
- [x] Full CLI interface with Typer (scan, compare, config commands)
- [x] Multi-subreddit comparison feature

**Phase 4: Polish** ✅
- [x] Error handling and graceful degradation
- [x] Multiple test scripts (7 test files)
- [x] Makefile for easy project management
- [x] Complete documentation (README + CLAUDE.md + handover)

**Phase 5: Cache Layer** ✅
- [x] MariaDB/MySQL integration with SQLAlchemy
- [x] Three-table schema (posts, classifications, scan_history)
- [x] Connection pooling and performance optimization
- [x] UPSERT logic for classifications
- [x] CLI commands (init-db, history, cache-stats)
- [x] Automatic cache detection and graceful fallback
- [x] Cache hit rate display and cost savings tracking

## CLI Commands

### `scan` - Analyze a Subreddit

```bash
# Basic usage
./reddit-analyzer scan ClaudeAI

# With options
./reddit-analyzer scan ClaudeAI \
  --limit 100 \
  --sort top \
  --time-filter month \
  --export-json

# Analyze all configured subreddits
./reddit-analyzer scan all --limit 30
```

**Options:**
- `--limit, -l`: Number of posts (default: 50)
- `--sort, -s`: Sort method (hot, new, top, rising)
- `--time-filter, -t`: Time filter for 'top' (hour, day, week, month, year, all)
- `--export-json`: Export report to JSON
- `--no-details`: Show summary only
- `--no-cache`: Bypass database cache (classify all posts)

### `scan-hn` - Analyze HackerNews

Scan and analyze posts from HackerNews with keyword filtering:

```bash
# Using specific keywords
./reddit-analyzer scan-hn -k claude -k anthropic --limit 20

# Using default keywords from config
./reddit-analyzer scan-hn --limit 50

# Different sort methods
./reddit-analyzer scan-hn -k llm --sort new --limit 30

# With JSON export
./reddit-analyzer scan-hn -k ai --export-json
```

**Options:**
- `--keyword, -k`: Keywords to filter HN posts (can specify multiple, case-insensitive)
- `--limit, -l`: Number of matching posts to fetch (default: 50, max: 500)
- `--sort, -s`: Sort method (top, new, best) - default: top
- `--export-json`: Export report to JSON
- `--no-cache`: Bypass database cache (classify all posts)

**Note**: If no keywords are provided, uses `HN_DEFAULT_KEYWORDS` from config. HackerNews uses Firebase API (500 req/min, no authentication required).

### `compare` - Compare Subreddits

Compare signal ratios across all configured subreddits:

```bash
./reddit-analyzer compare --limit 20
```

Shows a comparison table with signal ratios and health grades.

### `config` - Show Configuration

View current settings:

```bash
./reddit-analyzer config
```

### `init-db` - Initialize Database

Create database schema for cache (requires MySQL/MariaDB):

```bash
./reddit-analyzer init-db
```

Creates three tables: `posts`, `classifications`, and `scan_history`. Supports both Reddit and HackerNews sources. Safe to run multiple times (idempotent).

**Migration Note**: If upgrading from version 1.x, run the multi-source migration:
```bash
mysql -u your_user -p reddit_analyzer < src/claude_redditor/db/migrations/002_multi_source.sql
```

### `history` - View Scan History

Show historical scan records from database:

```bash
# All history
./reddit-analyzer history

# Filter by subreddit
./reddit-analyzer history ClaudeAI --limit 20
```

### `cache-stats` - Cache Statistics

Display cache usage and savings:

```bash
./reddit-analyzer cache-stats
```

Shows total cached posts, classifications, and estimated API cost savings.

### `digest` - Generate Daily Digest

Generate a daily digest article from signal posts (in Spanish, designed for newsletters/podcasts):

```bash
# Generate digest for default project (claudeia)
./reddit-analyzer digest

# Generate digest for specific project
./reddit-analyzer digest --project claudeia

# Preview without generating file
./reddit-analyzer digest --dry-run

# Limit number of posts and set minimum confidence
./reddit-analyzer digest --limit 10 --min-confidence 0.8

# Custom output directory
./reddit-analyzer digest --output-dir /path/to/digests
```

**Options:**
- `--project, -p`: Project name (default: claudeia)
- `--limit, -l`: Maximum number of posts to include (default: 15)
- `--output-dir, -o`: Output directory for digest files
- `--dry-run`: Preview digest without generating file
- `--min-confidence`: Minimum confidence threshold (default: 0.7)

**Output Format ("La Gaceta IA"):**

The digest generates a Spanish-language markdown newsletter with this structure:

```
# La Gaceta IA - 2026-01-17

*Resumen diario de las 15 noticias mas relevantes sobre Inteligencia Artificial*

---

## 1. [Article Title in Spanish]

[News article body - professional journalism style, minimum 1000 chars]

**Fuente:** [Original Post Title](https://reddit.com/...)

### Comentario del presentador

[Radio host commentary - conversational, opinionated, 2-3 paragraphs]

---

## 2. [Next Article...]
...
```

**Content Processing:**

1. **Post selection** - Only SIGNAL posts (technical, troubleshooting, research_verified) not yet sent
2. **Truncation detection** - If stored selftext is exactly 5000 chars, it was likely truncated
3. **Full content fetch** - For truncated posts, fetches original content via Reddit JSON API or web scraping
4. **Article generation** - Claude generates Spanish news article + presenter commentary from each post
5. **Tracking** - Posts marked with `sent_in_digest_at` timestamp to avoid duplicates in future digests

**File naming:** `digest_{project}_{date}_{sequence}.md` (e.g., `digest_claudeia_2026-01-17_01.md`)

**N8N Integration:**

The digest command is designed for automation with N8N. The typical workflow:

1. **Schedule trigger** - Run daily at a configured time (e.g., 9:00 AM)
2. **Scan sources** - Fetch new posts from Reddit and HackerNews
3. **Generate digest** - Run `source .venv/bin/activate && ./reddit-analyzer digest --project claudeia --limit 15`
4. **Read output** - Extract the generated markdown file path from stdout
5. **Send email** - Deliver the digest to subscribers (optionally converting markdown to HTML)

For the complete step-by-step setup guide, see [docs/N8N_INTEGRATION.md](docs/N8N_INTEGRATION.md).

### `version` - Version Info

```bash
./reddit-analyzer version
```

## Architecture

```
CLI (Typer)
    ↓
Scraper → Cache Check → Classifier → Analyzer → Reporter
(RSS/PRAW)  (MariaDB)   (Claude)    (Stats)    (Rich/JSON)
                        Haiku 4.5
                            ↓
                        Save to DB
```

**Pipeline Flow:**
1. **Scraper** fetches posts from Reddit (RSS or PRAW mode)
2. **Cache Check** queries MariaDB for existing classifications
3. **Classifier** sends only new posts to Claude Haiku for categorization
4. **Database** saves new classifications and scan history
5. **Analyzer** generates metrics, signal ratios, and statistics
6. **Reporter** renders beautiful terminal output or exports to JSON

**Cache Benefits:**
- **70-80% cost reduction** - Cached posts avoid API calls
- **Instant results** - Cached classifications returned immediately
- **Historical tracking** - Scan history with metrics evolution

### Dual-Mode Scraper

**RSS Mode** (default, no auth required):
- 10 requests/min
- Zero setup
- Limited data (no score/comments)
- Perfect for development

**PRAW Mode** (with Reddit credentials):
- 60 requests/min
- Full post data
- Automatic upgrade when credentials detected

## MariaDB Cache Layer

The cache layer uses MariaDB/MySQL to persistently store classifications, avoiding redundant API calls to Claude.

### Database Schema

The system uses three tables to manage caching and tracking:

#### `posts` - Post Metadata (Multi-Source)
Stores post information from Reddit and HackerNews to avoid re-fetching.

| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR(50) | Prefixed post ID: reddit_abc123, hn_8863 (primary key) |
| `source` | ENUM | Content source: 'reddit' or 'hackernews' |
| `subreddit` | VARCHAR(100) | Subreddit name (Reddit only, NULL for HN) |
| `title` | TEXT | Post title |
| `author` | VARCHAR(100) | Post author |
| `score` | INT | Post score/upvotes |
| `num_comments` | INT | Comment count |
| `created_utc` | BIGINT | Unix timestamp |
| `url` | TEXT | Post URL |
| `selftext` | TEXT | Post content (truncated to 5000 chars) |
| `fetched_at` | TIMESTAMP | When post was cached |

**Indexes:** `source`, `subreddit`, `created_utc`, `fetched_at`, composite `(source, created_utc)`

#### `classifications` - Claude Classifications
Stores classification results from Claude API (one per post, multi-source).

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT | Auto-increment primary key |
| `post_id` | VARCHAR(50) | Foreign key to posts.id (unique) |
| `source` | ENUM | Content source matching the post: 'reddit' or 'hackernews' |
| `category` | ENUM | One of 9 categories (technical, mystical, etc.) |
| `confidence` | DECIMAL(3,2) | Confidence score (0.00-1.00) |
| `red_flags` | JSON | Array of detected red flags |
| `reasoning` | TEXT | Classification explanation |
| `model_version` | VARCHAR(50) | Claude model used |
| `classified_at` | TIMESTAMP | When classification was made |

**Indexes:** `post_id` (unique), `source`, `category`, `classified_at`

**Constraints:** Foreign key cascade delete on `post_id`

#### `scan_history` - Scan Tracking
Records each scan with metrics for historical analysis (multi-source).

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT | Auto-increment primary key |
| `subreddit` | VARCHAR(100) | Subreddit name (Reddit) or "HackerNews" (HN) |
| `source` | ENUM | Content source: 'reddit' or 'hackernews' |
| `scan_date` | TIMESTAMP | When scan occurred |
| `posts_fetched` | INT | Total posts retrieved |
| `posts_classified` | INT | New posts classified |
| `posts_cached` | INT | Posts retrieved from cache |
| `signal_ratio` | DECIMAL(5,2) | Signal percentage (0-100) |

**Indexes:** `subreddit`, `source`, `scan_date`

### Cache Behavior

**UPSERT Logic:**
- Posts are inserted if new, skipped if already exist
- Classifications use `ON DUPLICATE KEY UPDATE` to replace old ones
- Scan history always appends new records

**Storage Optimization:**

The system applies intelligent selftext truncation based on classification category to reduce database storage:

| Category Type | Max selftext | Rationale |
|---------------|-------------|-----------|
| SIGNAL (technical, troubleshooting, research_verified) | 5000 chars | Full content preserved for digest generation |
| META (community, meme) | 5000 chars | Full content preserved |
| NOISE (mystical, unverified_claim, engagement_bait) | 500 chars | Low-value content, minimal storage |
| UNRELATED | 500 chars | Off-topic content, minimal storage |

This reduces database storage significantly over time while preserving full content only for posts that matter.

**Performance:**
- Connection pool: 5 permanent + 10 overflow connections
- Pre-ping verification prevents stale connections
- 1-hour connection recycling prevents timeouts

**Cache Stats Display:**
```
💾 Cache Stats
Total posts:       50
Cached:           40 (80.0%)
New classified:   10
API cost saved:   ~$0.040
```

### Setup Instructions

1. **Install MariaDB/MySQL** (if not already installed)
2. **Configure credentials** in `.env`:
   ```bash
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=your_user
   MYSQL_PASSWORD=your_password
   MYSQL_DATABASE=reddit_analyzer
   ```
3. **Initialize schema**:
   ```bash
   ./reddit-analyzer init-db
   ```
4. **Verify setup**:
   ```bash
   ./reddit-analyzer config  # Check cache status
   ```

The cache works automatically once configured. Use `--no-cache` flag to bypass when needed.

## Classification System

The classifier uses Claude AI to analyze each post and assign a category based on content quality and reliability. The system is designed to separate genuinely useful technical content from problematic or low-quality posts.

### Classification Criteria

**How posts are classified:**

1. **Topic relevance** - First, the classifier checks if the post relates to the configured TOPIC (e.g., "AI and Large Language Models"). Off-topic posts are marked as `unrelated` regardless of quality.

2. **Source verification** - Posts making technical or scientific claims are evaluated for citations and verifiable sources. Claims without sources are classified as noise.

3. **Content actionability** - Technical posts must contain actionable content: working code, specific prompts, clear step-by-step guides, or reproducible experiments.

4. **Red flag detection** - The classifier scans for problematic language patterns that indicate unreliable content (see Red Flags below).

5. **Confidence scoring** - Each classification includes a confidence score (0.0-1.0). Scores above 0.9 indicate clear-cut cases; scores between 0.5-0.8 indicate ambiguous content.

For the complete classification prompt and rules, see [prompts/classify_posts.md](prompts/classify_posts.md).

### Categories

**SIGNAL** (useful content):
- `technical`: Prompts, workflows, functional code, tutorials, how-to guides with actionable steps
- `troubleshooting`: Real problems with solutions, debugging help, error resolution with clear answers
- `research_verified`: Papers, experiments, or claims backed by verifiable sources and citations

**NOISE** (problematic content):
- `mystical`: Claims about AI consciousness, sentience, or spirituality without scientific evidence
- `unverified_claim`: Technical assertions, statistics, or performance claims without sources or proof
- `engagement_bait`: Clickbait titles designed to generate reactions rather than inform

**META**:
- `community`: Subreddit meta-discussion, community announcements, polls, rule discussions
- `meme`: Humor, entertainment, jokes, creative content not meant to inform

**OTHER**:
- `outlier`: Posts that don't fit clearly into other categories

**UNRELATED**:
- `unrelated`: Content outside the configured topic scope (not necessarily bad, just off-topic)

### Red Flags

The classifier detects these problematic patterns that indicate unreliable content:

| Red Flag | What it detects | Example phrases |
|----------|-----------------|-----------------|
| `no_source` | Scientific claims without citation | "researchers say", "studies show", "experiments found" |
| `link_in_bio` | External content promotion | "link in bio", "check my profile", "visit my page" |
| `mystical_language` | Unscientific AI claims | "consciousness emerged", "sentient", "awakening", "divine" |
| `precise_numbers_no_source` | Specific metrics without proof | "95.7 times faster", "2,725 tokens", "14.3% improvement" |
| `cannot_explain` | Appeal to mystery | "researchers can't explain", "mysterious", "defies explanation" |
| `sensationalist` | Clickbait language | "you won't believe", "shocking", "mind-blowing", "incredible discovery" |

For the pattern definitions, see [src/claude_redditor/core/enums.py](src/claude_redditor/core/enums.py).

### Signal Ratio

The **signal ratio** measures overall content quality:

```
Signal Ratio = (technical + troubleshooting + research_verified) / total_relevant_posts
```

- Posts marked as `unrelated` are excluded from the calculation
- A ratio above 60% is considered healthy (grade B or better)
- The grading scale: A+ (80%+), A (70%+), B (60%+), C (50%+), D (40%+), F (<40%)

## Tech Stack

- **Python 3.11+**
- **PRAW** - Reddit API wrapper (optional)
- **feedparser** - RSS feed parsing (default mode)
- **Anthropic SDK** - Claude Haiku for classification
- **Typer** - CLI framework
- **Rich** - Beautiful terminal output
- **Pydantic** - Data validation and settings
- **SQLAlchemy** - Database ORM
- **PyMySQL** - MariaDB/MySQL driver
- **MariaDB/MySQL** - Cache database (optional)

## Development

### Project Structure

```
reddit-analyzer/
├── src/claude_redditor/
│   ├── core/
│   │   ├── models.py          # RedditPost, Classification, AnalysisReport
│   │   └── enums.py           # CategoryEnum, red flag patterns
│   ├── scrapers/              # Multi-source scraper package
│   │   ├── __init__.py        # Factory functions & ScraperManager
│   │   ├── base.py            # BaseScraper abstract class, Post model
│   │   ├── reddit.py          # RedditScraper (dual-mode: PRAW/RSS)
│   │   └── hackernews.py      # HackerNewsScraper (Firebase API)
│   ├── db/                    # MariaDB cache layer
│   │   ├── connection.py      # SQLAlchemy connection pool
│   │   ├── models.py          # Database models (tables)
│   │   ├── repository.py      # Data access layer
│   │   └── migrations/
│   │       ├── 001_initial_schema.sql
│   │       ├── 002_multi_source.sql
│   │       ├── 003_add_flair.sql
│   │       └── 004_add_project_column.sql
│   ├── config.py              # Settings management (pydantic-settings)
│   ├── scraper.py             # DEPRECATED - backward compatibility wrapper
│   ├── classifier.py          # Claude-based classification with batching
│   ├── analyzer.py            # Metrics generation with cache support
│   ├── reporter.py            # Rich terminal output and JSON export
│   ├── digest.py              # Daily digest generation (Spanish)
│   ├── content_fetcher.py     # Fetch full content from truncated posts
│   ├── cli_helpers.py         # Helper functions for CLI
│   └── cli.py                 # Typer CLI entry point (8 commands)
├── prompts/
│   ├── classify_posts.md      # Classification system prompt
│   └── digest_article.md      # Digest article generation prompt
├── outputs/
│   ├── cache/                 # Cached Reddit responses
│   ├── classifications/       # Cached Claude classifications
│   ├── reports/               # Generated JSON reports
│   └── digests/               # Generated markdown digests
├── tests/                     # Test scripts for components
│   ├── test_scraper.py
│   ├── test_classifier.py
│   ├── test_analyzer.py
│   ├── test_e2e.py
│   └── ...
├── Makefile                   # Convenient project commands
├── pyproject.toml             # Python package configuration
├── docs/
│   └── N8N_INTEGRATION.md     # N8N automation guide
└── .env.example               # Environment variables template
```

### Testing

The project includes comprehensive test scripts for all major components:

```bash
# Run all tests
make test

# Individual component tests
make test-scraper       # Test Reddit scraper (RSS/PRAW)
make test-classifier    # Test Claude classification
make test-analyzer      # Test metrics generation
make test-e2e          # Test full pipeline
make test-e2e-compare  # Test multi-subreddit comparison

# Or run tests directly
python test_scraper.py
python test_classifier.py
python test_analyzer.py
python test_e2e.py
python test_all_subreddits.py
```

### Makefile Commands

Convenient shortcuts for common tasks:

```bash
make help      # Show all available commands
make install   # Install dependencies
make dev       # Install in development mode
make scan      # Quick scan (5 posts from r/ClaudeAI)
make compare   # Compare all subreddits
make config    # Show current configuration
make clean     # Remove caches and generated files
```

## Cost Estimates

### Without Cache
- **Reddit API**: Free (RSS mode) or Free (PRAW with rate limits)
- **Anthropic API**: ~$0.10 per 100 posts (Haiku at $0.80/1M input tokens)
- **First-time setup**: $5 free credits from Anthropic covers 5,000+ posts

### With MariaDB Cache
- **First scan**: Same as above (~$0.10 per 100 posts)
- **Subsequent scans**: **70-80% reduction** in API costs
- **Example**: 100 posts, 80 cached → **$0.02** instead of $0.10
- **Cache maintenance**: Negligible (local MariaDB/MySQL database)

## Usage Examples

### Reddit Examples
```bash
# Quick scan of r/ClaudeAI (5 posts, no details)
make scan

# Full scan with 100 posts (uses cache automatically)
./reddit-analyzer scan ClaudeAI --limit 100

# Analyze top posts from the past month
./reddit-analyzer scan ClaudeAI --sort top --time-filter month --limit 50

# Compare all configured subreddits
./reddit-analyzer compare --limit 30

# Export results to JSON
./reddit-analyzer scan ClaudeAI --limit 50 --export-json

# Bypass cache (force re-classification)
./reddit-analyzer scan ClaudeAI --limit 30 --no-cache

# Scan specific subreddit (not in config)
./reddit-analyzer scan LocalLLaMA --limit 30
```

### HackerNews Examples
```bash
# Scan with specific keywords
./reddit-analyzer scan-hn -k claude -k anthropic --limit 20

# Use default keywords from config
./reddit-analyzer scan-hn --limit 50

# Scan for AI discussions (new stories)
./reddit-analyzer scan-hn -k ai -k "machine learning" --sort new --limit 30

# Export HN analysis to JSON
./reddit-analyzer scan-hn -k llm --export-json

# Bypass cache for fresh analysis
./reddit-analyzer scan-hn -k claude --no-cache
```

### Database & History
```bash
# View scan history (all sources)
./reddit-analyzer history

# Filter history by subreddit
./reddit-analyzer history ClaudeAI --limit 20

# Check cache statistics
./reddit-analyzer cache-stats
```

## Extending the Project

See [handover_ver2.md](handover_ver2.md) and [CLAUDE.md](CLAUDE.md) for detailed architecture and implementation notes.

**Possible enhancements:**
- Add HTML export for reports (JSON export currently supported)
- Add more red flag patterns (currently 6 patterns implemented)
- Create a web interface / dashboard for real-time monitoring
- Add trend analysis and visualization from scan history
- Implement alerting when signal ratio drops below threshold
- Add support for filtering by date range in history
- Add more content sources (blogs, newsletters, etc.)
- Multi-language digest support (currently Spanish only)

## License

MIT
