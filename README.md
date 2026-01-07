# Reddit Signal/Noise Analyzer

CLI tool to analyze Reddit posts from Claude/LLM subreddits, automatically classify them as Signal vs Noise, and generate insightful reports.

## Problem Solved

Claude/LLM subreddits contain mixed content - from useful technical guides to unfounded mystical theories. This tool automates the filtering process using Claude AI to classify posts and identify red flags.

## Features

- **Dual-Mode Scraping**: RSS mode (no auth) or PRAW mode (with auth)
- **AI Classification**: Uses Claude Haiku to classify posts into categories
- **Red Flag Detection**: Identifies problematic patterns (no sources, sensationalism, etc.)
- **Rich Reports**: Beautiful terminal output with tables and charts
- **Export Options**: JSON and HTML report generation

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

**Optional**: Add Reddit credentials for faster scraping (60 req/min vs 10 req/min):
```bash
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
```

Get Reddit credentials at: https://www.reddit.com/prefs/apps (create "script" type app)

### 3. Usage

```bash
# Analyze a single subreddit (simple)
./reddit-analyzer scan ClaudeAI

# Analyze with options
./reddit-analyzer scan ClaudeAI --limit 50 --sort top --time-filter week

# Analyze all configured subreddits
./reddit-analyzer scan all --limit 30 --export-json

# Compare multiple subreddits
./reddit-analyzer compare --limit 20

# Show configuration
./reddit-analyzer config

# Show version
./reddit-analyzer version
```

## Project Status

**Phase 1: Foundation** ✅ COMPLETE
- [x] Project structure
- [x] Core data models (RedditPost, Classification, AnalysisReport)
- [x] Configuration management (pydantic-settings)
- [x] Dual-mode scraper (RSS/PRAW)
- [x] Test with r/ClaudeAI

**Phase 2: Classification** ✅ COMPLETE
- [x] Classification prompt with detailed rules
- [x] Classifier with batch processing (20 posts per request)
- [x] Red flags detection (6 patterns)
- [x] Pydantic validation and error handling

**Phase 3: Analysis & Output** ✅ COMPLETE
- [x] Analysis engine (metrics, signal ratio, health grades)
- [x] Reporter (Rich terminal output with tables and charts)
- [x] JSON export functionality
- [x] CLI commands (Typer)

**Phase 4: Polish** 🚧 OPTIONAL
- [ ] Error handling and retries
- [ ] Progress indicators
- [ ] Tests with fixtures
- [ ] Documentation

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

### `version` - Version Info

```bash
./reddit-analyzer version
```

## Architecture

```
CLI (Typer)
    ↓
┌─────────┬──────────┐
│         │          │
Scraper → Classifier → Analyzer → Reporter
(RSS)     (Claude)    (Stats)    (Rich/JSON)
  ↓         ↓
Cache    Cache
```

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

## Data Models

### Categories

**SIGNAL** (useful content):
- `technical`: Prompts, workflows, functional code
- `troubleshooting`: Real problems + solutions
- `research_verified`: Papers/experiments with verifiable sources

**NOISE** (problematic content):
- `mystical`: Consciousness claims without evidence
- `unverified_claim`: Technical assertions without sources
- `engagement_bait`: Clickbait content

**META**:
- `community`: Subreddit discussion
- `meme`: Humor/entertainment

**OTHER**:
- `outlier`: Doesn't fit clearly

### Red Flags

- `no_source`: Scientific claims without citation
- `link_in_bio`: External content promotion
- `mystical_language`: Consciousness/spiritual terminology
- `precise_numbers_no_source`: Specific metrics without citation
- `cannot_explain`: "Researchers puzzled", "mysterious"
- `sensationalist`: "Shocking discovery", "you won't believe"

## Tech Stack

- **Python 3.11+**
- **PRAW** - Reddit API wrapper (optional)
- **feedparser** - RSS feed parsing (default mode)
- **Anthropic SDK** - Claude Haiku for classification
- **Typer** - CLI framework
- **Rich** - Beautiful terminal output
- **Pydantic** - Data validation and settings

## Development

### Project Structure

```
reddit-analyzer/
├── src/claude_redditor/
│   ├── core/
│   │   ├── models.py      # RedditPost, Classification, AnalysisReport
│   │   └── enums.py       # CategoryEnum, red flag patterns
│   ├── config.py          # Settings management
│   ├── scraper.py         # Dual-mode Reddit scraper
│   ├── classifier.py      # TODO: Claude classification
│   ├── analyzer.py        # TODO: Metrics generation
│   ├── reporter.py        # TODO: Output rendering
│   ├── cache.py           # TODO: Cache management
│   └── cli.py             # TODO: CLI entry point
├── prompts/               # TODO: Classification prompts
├── outputs/               # Cache, classifications, reports
└── tests/                 # TODO: Test fixtures
```

### Testing

```bash
# Test basic scraper
python test_scraper.py

# Test with ClaudeAI subreddit
python test_claude_subreddit.py
```

## Cost Estimates

- **Reddit API**: Free (RSS mode) or Free (PRAW with rate limits)
- **Anthropic API**: ~$0.10 per 100 posts (Haiku at $0.80/1M input tokens)
- **First-time setup**: $5 free credits from Anthropic covers 5,000+ posts

## Next Steps

See [handover_ver2.md](handover_ver2.md) for detailed implementation guidance.

1. Implement `classifier.py` with batch processing
2. Create classification prompt in `prompts/classify_posts.md`
3. Implement `analyzer.py` for metrics
4. Implement `reporter.py` for Rich output
5. Create CLI commands in `cli.py`

## License

MIT
