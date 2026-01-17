# CLAUDE.md

## Quick Context

```
STATUS: ✅ Production | 8 CLI commands | Multi-project | Multi-source

FLOW: Scraper(Reddit/HN) → Cache(MariaDB) → Classifier(Claude) → Analyzer → Reporter/Digest

CLI: scan, scan-hn, compare, digest, config, init-db, history, cache-stats

FILES:
├─ cli.py              → Entry point, all commands
├─ classifier.py       → Classification logic (batch=20)
├─ analyzer.py         → Metrics + CachedAnalysisEngine
├─ digest.py           → Newsletter generation (Spanish)
├─ content_fetcher.py  → Fetch full content if truncated
├─ config.py           → Settings (pydantic-settings)
├─ db/repository.py    → All DB queries
├─ scrapers/           → reddit.py (RSS/PRAW), hackernews.py (Firebase)
├─ prompts/            → classify_posts.md, digest_article.md

DESIGN:
- Truncation: SIGNAL/META=5000ch, NOISE/UNRELATED=500ch (in analyzer.py:363-371)
- Truncation detection: len(selftext)==5000 → fetch full content for digest
- Multi-project: --project flag, isolated by `project` column in all tables
- Categories: 10 (3 SIGNAL, 3 NOISE, 2 META, 1 OTHER, 1 UNRELATED)
- Red flags: 6 patterns in core/enums.py
- Signal ratio excludes UNRELATED posts

DEPS: Anthropic API (req), MariaDB (opt but recommended), Reddit API (opt, RSS fallback)
```

## Development Commands

```bash
# Activate environment
source .venv/bin/activate

# Run CLI
./reddit-analyzer --help
./reddit-analyzer scan ClaudeAI --limit 20
./reddit-analyzer scan-hn -k claude --limit 20
./reddit-analyzer digest --project claudeia --dry-run

# Database
./reddit-analyzer init-db
./reddit-analyzer config
```

## Key Files Reference

| Task | File(s) |
|------|---------|
| Add CLI command | `cli.py` |
| Modify classification | `classifier.py` + `prompts/classify_posts.md` |
| Change categories/red flags | `core/enums.py` |
| DB queries/cache | `db/repository.py` |
| Add scraper source | `scrapers/` (inherit from `base.py`) |
| Digest format | `digest.py` + `prompts/digest_article.md` |
| Settings/env vars | `config.py` + `.env` |

## Non-Obvious Design Decisions

1. **Same post, different classifications**: Post can exist in multiple projects with different categories (topic-dependent classification)

2. **Selftext truncation happens AFTER classification**: Category determines truncation limit before DB save

3. **Digest only uses SIGNAL posts**: Filtered by `sent_in_digest_at IS NULL` to avoid duplicates

4. **RSS is default for Reddit**: PRAW only activates if `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` set

5. **HackerNews uses Firebase API**: No auth needed, 500 req/min limit

6. **Project isolation**: All tables have `project` column, queries always filter by project

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional (enables MariaDB cache - highly recommended)
MYSQL_HOST=localhost
MYSQL_USER=user
MYSQL_PASSWORD=pass
MYSQL_DATABASE=reddit_analyzer

# Optional (enables PRAW mode for Reddit - faster)
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...

# Multi-project config
CLAUDEIA_SUBREDDITS=ClaudeAI,Claude,ClaudeCode
CLAUDEIA_TOPIC="AI and Large Language Models..."
CLAUDEIA_HN_KEYWORDS=claude,anthropic,ai,llm

WINEWORLD_SUBREDDITS=wine,winemaking,sommelier
WINEWORLD_TOPIC="Wine industry, viticulture..."
WINEWORLD_HN_KEYWORDS=wine,viticulture,vineyard
```

## Common Tasks

**Add new red flag pattern:**
1. Edit `core/enums.py` → `RED_FLAG_PATTERNS`
2. Update `prompts/classify_posts.md` if needed

**Add new category:**
1. Edit `core/enums.py` → `CategoryEnum`
2. Update `prompts/classify_posts.md`
3. Run DB migration if storing in ENUM column

**Add new project:**
1. Add `{PROJECT}_SUBREDDITS`, `{PROJECT}_TOPIC`, `{PROJECT}_HN_KEYWORDS` to `.env`
2. Use `--project {project}` in CLI commands

**Debug classification:**
```bash
./reddit-analyzer scan ClaudeAI --limit 5 --no-cache
# Check outputs/classifications/ for raw JSON
```

For full documentation, see `README.md`.
