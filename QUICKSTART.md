# ClaudeRedditor - Quick Start

> From zero to first digest in 5 minutes.

---

## Prerequisites

- Python 3.11+
- Anthropic API key ([console.anthropic.com](https://console.anthropic.com))
- (Optional) MariaDB for caching

---

## Step 1: Install

```bash
git clone https://github.com/your-user/ClaudeRedditor.git
cd ClaudeRedditor
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

**Expected output**:
```
Successfully installed claude-redditor
```

---

## Step 2: Configure

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

**Minimum .env**:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
```

**Optional (recommended)**:
```bash
MYSQL_HOST=localhost
MYSQL_USER=reddit_analyzer
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=reddit_analyzer
```

---

## Step 3: Initialize Database (if using MariaDB)

```bash
./reddit-analyzer init-db
```

**Expected output**:
```
✓ Connection test passed
✓ Database schema initialized
  Host: localhost:3306
  Database: reddit_analyzer
✓ Database ready!
```

Skip this step if not using MariaDB (will work without cache, but higher API costs).

---

## Step 4: Scan Posts

```bash
./reddit-analyzer scan ClaudeAI --project claudeia --limit 20
```

**Expected output**:
```
Scanning r/ClaudeAI...

  Source       Fetched   Classified   Cached   Signal%
  r/ClaudeAI   20        15           5        45.0%

✓ Scan complete! 15 new classifications.
```

**What happened**:
- Fetched 20 posts from r/ClaudeAI
- 5 were already in cache (skipped)
- 15 new posts classified by Claude
- 45% were SIGNAL (useful content)

---

## Step 5: Generate Digest

```bash
./reddit-analyzer digest --project claudeia
```

**Expected output**:
```
Generating digest for claudeia...

  Processing 7 SIGNAL posts...
  ✓ Generated 7 articles

Output:
  📄 outputs/digests/digest_2026-01-24_01.md
  📊 outputs/web/claudeia_2026-01-24_01.json

✓ Digest complete!
```

**Your newsletter is ready!** Open the markdown file to read.

---

## What's Next?

### Scan more sources

```bash
# All subreddits in project
./reddit-analyzer scan all --project claudeia --limit 50

# Include HackerNews
./reddit-analyzer scan all --include-hn --project claudeia

# Just HackerNews
./reddit-analyzer scan-hn --project claudeia
```

### View available commands

```bash
./reddit-analyzer --help
./reddit-analyzer config  # Shows projects and settings
```

### Bookmark interesting stories

```bash
./reddit-analyzer bookmark show latest
./reddit-analyzer bookmark add 2026-01-24_01_003 --note "Try this prompt"
```

---

## Common Issues

### "MySQL not configured"

Add these to your `.env`:
```bash
MYSQL_HOST=localhost
MYSQL_USER=your_user
MYSQL_PASSWORD=your_pass
MYSQL_DATABASE=reddit_analyzer
```

Or run without database (higher API costs, no cache).

### "No posts found"

Check the subreddit exists and has recent posts:
```bash
./reddit-analyzer scan ClaudeAI --limit 5 --no-cache
```

### "API key invalid"

Verify your `ANTHROPIC_API_KEY` in `.env` starts with `sk-ant-`.

---

## Next Steps

- [Architecture](ARCHITECTURE.md) - Understand the system
- [How to Deploy](docs/HOW-TO-DEPLOY.md) - Automate with cron/N8N
- [How to Add Project](docs/HOW-TO-ADD-PROJECT.md) - Create new topic

---

*Total time: ~5 minutes*
