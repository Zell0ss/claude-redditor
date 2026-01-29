# ClaudeRedditor

Monitor Reddit/HN for AI posts, classify with Claude, generate Spanish newsletters.

## Quick Start

```bash
# Install
source .venv/bin/activate
pip install -e .

# Configure (add ANTHROPIC_API_KEY)
cp .env.example .env

# Scan & generate digest
./reddit-analyzer scan all --project claudeia --limit 50
./reddit-analyzer digest --project claudeia
```

## What It Does

- **Multi-source scraping**: Reddit (RSS/PRAW) + HackerNews (Firebase API)
- **AI classification**: Claude Haiku categorizes posts as SIGNAL/NOISE/META with multi-tier tags
- **Deep analysis**: 9-tier classification system for SIGNAL posts (tech stack, patterns, strategy)
- **Daily digest**: Auto-generates Spanish newsletter from top SIGNAL posts
- **Multi-project**: Isolated configs for different topics (AI podcast, wine blog)
- **Cost optimization**: MariaDB cache reduces API costs by 70-80%

## Documentation

- [Architecture](ARCHITECTURE.md) - How it works, key decisions
- [Quick Start](QUICKSTART.md) - Full tutorial (5 min)
- [Briefing](BRIEFING.md) - Project overview for Claude AI
- [How to Deploy](docs/HOW-TO-DEPLOY.md) - Cron/N8N automation
- [How to Add Project](docs/HOW-TO-ADD-PROJECT.md) - Create new topic

## Requirements

- Python 3.11+
- Anthropic API key (required)
- MariaDB (optional, recommended for caching)
- Reddit API credentials (optional, faster scraping)
