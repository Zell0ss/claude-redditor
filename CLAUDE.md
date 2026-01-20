# CLAUDE.md

## Quick Context

```
STATUS: ✅ Production | 8 CLI commands + bookmark subcommands | Multi-project | Multi-source | Multi-tags

FLOW: Scraper(Reddit/HN) → Cache(MariaDB) → Classifier(Claude) → Analyzer → Reporter/Digest/JSON

CLI: scan, scan-hn, compare, digest, config, init-db, history, cache-stats
     bookmark show|add|list|done|status

FILES:
├─ cli/                → CLI commands (Typer best practices)
│  ├─ __init__.py      → Main app, aggregates subcommands
│  ├─ scan.py          → scan, scan-hn, compare
│  ├─ digest_cmd.py    → digest command
│  ├─ bookmark.py      → bookmark show|add|list|done|status
│  ├─ db.py            → init-db, history, cache-stats
│  ├─ info.py          → config, version (auto-discovers projects)
│  └─ helpers.py       → Output formatting (Rich)
├─ classifier.py       → Classification logic (batch=20) + topic_tags/format_tag
├─ analyzer.py         → Metrics + CachedAnalysisEngine
├─ digest.py           → Newsletter (MD) + JSON export for web
├─ content_fetcher.py  → Fetch full content if truncated
├─ config.py           → Settings (pydantic-settings) - secrets only
├─ projects.py         → ProjectLoader - auto-discovers projects/
├─ db/repository.py    → All DB queries + bookmark CRUD
├─ db/models.py        → ORM models (RedditPost, Classification, ScanHistory, Bookmark)
├─ scrapers/           → reddit.py (RSS/PRAW), hackernews.py (Firebase)
├─ projects/           → Self-contained project definitions
│  ├─ claudeia/        → AI/LLM content (podcast)
│  │  ├─ config.yaml   → topic, subreddits, hn_keywords
│  │  └─ prompts/      → classify.md, digest.md
│  └─ wineworld/       → Wine industry (blog)
│     ├─ config.yaml
│     └─ prompts/

DESIGN:
- Multi-tags: topic_tags (array) + format_tag (single) per classification
- Truncation: SIGNAL/META=5000ch, NOISE/UNRELATED=500ch (in analyzer.py:363-371)
- Truncation detection: len(selftext)==5000 → fetch full content for digest
- Multi-project: --project flag, projects auto-discovered from src/claude_redditor/projects/
- Categories: 10 (3 SIGNAL, 3 NOISE, 2 META, 1 OTHER, 1 UNRELATED)
- Red flags: 6 patterns in core/enums.py
- Signal ratio excludes UNRELATED posts
- JSON digest: outputs/web/{date}.json + latest.json symlink
- Bookmarks: denormalized (story data copied at bookmark time)

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
./reddit-analyzer digest --project claudeia --format json  # JSON for web

# Bookmarks
./reddit-analyzer bookmark show latest
./reddit-analyzer bookmark add 2026-01-17-003 --note "Interesting"
./reddit-analyzer bookmark list --status to_read
./reddit-analyzer bookmark done 2026-01-17-003

# Database
./reddit-analyzer init-db
./reddit-analyzer config
```

## Key Files Reference

| Task | File(s) |
|------|---------|
| Add CLI command | `cli/` (new file or add to existing) |
| Modify classification | `src/claude_redditor/projects/{name}/prompts/classify.md` |
| Change categories/red flags | `core/enums.py` + project prompts |
| DB queries/cache | `db/repository.py` |
| Add scraper source | `scrapers/` (inherit from `base.py`) |
| Digest format | `src/claude_redditor/projects/{name}/prompts/digest.md` |
| Settings/env vars | `config.py` + `.env` (secrets only) |
| Add new project | `src/claude_redditor/projects/{name}/config.yaml` + `prompts/` |
| Bookmark commands | `cli/bookmark.py` + `db/repository.py` |
| JSON web output | `digest.py` (generate_json) → `outputs/web/` |
| CLI output formatting | `cli/helpers.py` |

## Non-Obvious Design Decisions

1. **Same post, different classifications**: Post can exist in multiple projects with different categories (topic-dependent classification)

2. **Selftext truncation happens AFTER classification**: Category determines truncation limit before DB save

3. **Digest only uses SIGNAL posts**: Filtered by `sent_in_digest_at IS NULL` to avoid duplicates

4. **RSS is default for Reddit**: PRAW only activates if `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` set

5. **HackerNews uses Firebase API**: No auth needed, 500 req/min limit

6. **Project isolation**: All tables have `project` column, queries always filter by project

7. **Projects as self-contained entities**: Each project in `src/claude_redditor/projects/` has its own config.yaml and prompts/. Zero code changes to add a new project.

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
```

Note: Project configuration (subreddits, topics, keywords) is now in `src/claude_redditor/projects/{name}/config.yaml`, not in `.env`.

## Common Tasks

**Add new red flag pattern:**
1. Edit `core/enums.py` → `RED_FLAG_PATTERNS`
2. Update project prompts if needed: `src/claude_redditor/projects/{name}/prompts/classify.md`

**Add new category:**
1. Edit `core/enums.py` → `CategoryEnum`
2. Update project prompts: `src/claude_redditor/projects/{name}/prompts/classify.md`
3. Run DB migration if storing in ENUM column

**Add new project:**
1. Create `src/claude_redditor/projects/{name}/config.yaml`:
   ```yaml
   name: myproject
   description: "My project description"
   topic: "Topic for classification context"
   sources:
     reddit:
       subreddits: [sub1, sub2]
     hackernews:
       keywords: [keyword1, keyword2]
   ```
2. Create `src/claude_redditor/projects/{name}/prompts/classify.md` (copy from existing project)
3. Create `src/claude_redditor/projects/{name}/prompts/digest.md` (copy from existing project)
4. Use `--project myproject` in CLI commands

**Debug classification:**
```bash
./reddit-analyzer scan ClaudeAI --limit 5 --no-cache
# Check outputs/classifications/ for raw JSON
```

**List available projects:**
```bash
./reddit-analyzer config
# Shows auto-discovered projects from src/claude_redditor/projects/ directory
```

For full documentation, see `README.md`.
