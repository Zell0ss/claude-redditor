# CLAUDE.md

## Quick Context

```
STATUS: ✅ Production | 9 CLI commands + bookmark + podcast subcommands | Multi-project | Multi-source | Multi-tags | Web viewer | Podcast pipeline (Editor + Guionista + Intro/Outro)

FLOW: Scraper(Reddit/HN) → Cache(MariaDB) → Classifier(Claude) → Analyzer → Reporter/Digest/JSON → Web(Astro)
      Podcast: digest.json → [1.Editor] → episode.json → [2.Guionista + 3.Intro/Outro] → dialog.json → [4-5. futuro]

CLI: scan, compare, digest, config, init-db, history, cache-stats, regenerate-json
     bookmark show|add|list|done|status
     podcast edit|script

FILES:
Root Level:
├─ CLAUDE.md, ARCHITECTURE.md, BRIEFING.md, README.md → Documentation
├─ QUICKSTART.md, TAGGING_SYSTEM.md, Makefile         → Guides + commands
├─ reddit-analyzer                                     → CLI entry point
├─ pyproject.toml                                      → Python project config
└─ test_cli.py, test_hn_scraper.py                    → Test files

src/claude_redditor/
├─ analyzer.py         → Metrics + CachedAnalysisEngine
├─ classifier.py       → Classification logic (batch=20) + topic_tags/format_tag
├─ config.py           → Settings (pydantic-settings) - secrets only
├─ content_fetcher.py  → Fetch full content if truncated
├─ digest.py           → Newsletter (MD) + JSON export for web
├─ projects.py         → ProjectLoader - auto-discovers projects/
├─ reporter.py         → Report generation
├─ cli/                → CLI commands (Typer best practices)
│  ├─ __init__.py      → Main app, aggregates subcommands
│  ├─ scan.py          → scan, scan-hn, compare
│  ├─ digest_cmd.py    → digest command
│  ├─ bookmark.py      → bookmark show|add|list|done|status
│  ├─ db.py            → init-db, history, cache-stats, regenerate-json
│  ├─ info.py          → config, version (auto-discovers projects)
│  ├─ helpers.py       → Output formatting (Rich)
│  ├─ podcast.py       → podcast edit|script subcommands
│  └─ podcast_helpers.py → Shared helpers: find_digest, load_prompt, call_and_parse, estimate_cost
├─ core/               → Core definitions
│  ├─ enums.py         → CategoryEnum, RED_FLAG_PATTERNS, etc.
│  └─ models.py        → Core data models
├─ db/                 → Database layer
│  ├─ connection.py    → Database connection management
│  ├─ models.py        → ORM models (RedditPost, Classification, ScanHistory, Bookmark)
│  └─ repository.py    → All DB queries + bookmark CRUD
├─ scrapers/           → Data scrapers
│  ├─ base.py          → Base scraper class
│  ├─ reddit.py        → Reddit scraper (RSS/PRAW)
│  └─ hackernews.py    → HackerNews scraper (Firebase)
└─ projects/           → Self-contained project definitions
   ├─ claudeia/        → AI/LLM content (podcast)
   │  ├─ config.yaml   → topic, subreddits, hn_keywords, podcast.editor/script/intro_outro
   │  └─ prompts/      → classify.md, digest.md, tagging.md, podcast_editor.md, podcast_script.md, podcast_intro_outro.md
   └─ wineworld/       → Wine industry (blog)
      ├─ config.yaml
      └─ prompts/      → classify.md, digest.md, tagging.md

web/                   → Astro static site for viewing digests
├─ astro.config.mjs, package.json, tsconfig.json → Configuration
├─ public/             → Static assets (favicon, images)
└─ src/
   ├─ components/      → BookmarkCard, StoryCard, SwarmBackground, TagBadge
   ├─ layouts/         → Layout.astro
   ├─ pages/           → index, bookmarks, digest/[id], story/[id]
   ├─ styles/          → global.css
   └─ types/           → digest.ts (TypeScript types for digest JSON)

Other Directories:
├─ outputs/            → Generated outputs (cache, classifications, digests, reports, web JSONs)
│                          outputs/podcast/{stem}_episode.json  ← Editor output (Stage 1)
│                          outputs/podcast/{stem}_dialog.json   ← Guionista+Intro/Outro output (Stages 2+3)
├─ scripts/            → Automation (daily-scan.sh, daily-digest.sh, deploy-web.sh, send-digest.sh)
├─ docs/               → HOW-TO-ADD-PROJECT.md, HOW-TO-DEPLOY.md
│  └─ plans/           → Handover docs per session (2026-04-27-handover.md, 2026-04-29-handover.md, 2026-05-04-handover.md)
├─ logs/               → Application logs (daily log files)
│                          logs/podcast/edit_{date}.log + script_{date}.log (structured JSON, one entry/block)
├─ tests/              → Test files + fixtures
└─ commenter_img/      → Branding/assets (commenter expressions)

DESIGN:
- Multi-tags: topic_tags (array) + format_tag (single) per classification
- Truncation: SIGNAL/META=5000ch, NOISE/UNRELATED=500ch (in analyzer.py:363-371)
- Truncation detection: len(selftext)==5000 → fetch full content for digest
- Multi-project: --project flag, projects auto-discovered from src/claude_redditor/projects/
- Categories: 10 (3 SIGNAL, 3 NOISE, 2 META, 1 OTHER, 1 UNRELATED)
- Red flags: 6 patterns in core/enums.py
- Signal ratio excludes UNRELATED posts
- JSON digest: outputs/web/{project}_{date}.json + latest.json symlink
- Digest default: --format both (generates markdown + JSON)
- Bookmarks: denormalized (story data copied at bookmark time)
- Web viewer: Astro static site reads JSONs from outputs/web/

DEPS: Anthropic API (req), MariaDB (opt but recommended), Reddit API (opt, RSS fallback)
```

## Development Commands

```bash
# Activate environment
source .venv/bin/activate

# Run CLI
./reddit-analyzer --help
./reddit-analyzer scan claudeia --limit 20                         # All sources (Reddit + HN)
./reddit-analyzer scan claudeia --source reddit --limit 50         # Reddit only
./reddit-analyzer scan claudeia --source hackernews --limit 20     # HackerNews only
./reddit-analyzer compare claudeia --limit 30                      # Compare subreddits
./reddit-analyzer digest --project claudeia --dry-run
./reddit-analyzer digest --project claudeia  # Generates both markdown + JSON by default

# Regenerate historical JSONs from DB
./reddit-analyzer regenerate-json --project claudeia --date all

# Web viewer (Astro)
cd web && npm run dev    # http://localhost:4321
cd web && npm run build  # Static build to web/dist/

# Bookmarks
./reddit-analyzer bookmark show latest
./reddit-analyzer bookmark add 2026-01-17-003 --note "Interesting"
./reddit-analyzer bookmark list --status to_read
./reddit-analyzer bookmark done 2026-01-17-003

# Database
./reddit-analyzer init-db
./reddit-analyzer config

# Podcast pipeline
./reddit-analyzer podcast edit --project claudeia             # Stage 1: episode plan
./reddit-analyzer podcast edit --project claudeia --dry-run  # Preview without saving
./reddit-analyzer podcast script --project claudeia          # Stages 2+3: full dialog + intro/outro
./reddit-analyzer podcast script --project claudeia --dry-run                # Preview without saving
./reddit-analyzer podcast script --project claudeia --blocks 2,3 --force    # Regenerate subset (skips intro/outro)
./reddit-analyzer podcast audio --project claudeia           # Stages 4+5: MP3 via Deepgram TTS
./reddit-analyzer podcast audio --project claudeia --date 2026-04-27 --digest-id 01  # Specific episode
```

## Claude Code: End of Session Workflow

**When the user says**: "Please finalize this session" / "End of session" / "Update docs and commit"

**You must**:
1. **Read** `.claude/skills/finish-session.md` (217 lines of detailed instructions)
2. **Follow** all 9 steps exactly as documented in that file
3. This includes:
   - Analyzing ALL git changes (from any source: this session, other Claudes, manual edits)
   - Reading `.github/prompts/DOCUMENTATION_PROMPT.md` standards
   - Using the decision matrix to determine what docs to update
   - Updating CLAUDE.md, ARCHITECTURE.md, BRIEFING.md, README.md as needed
   - Showing diff and asking for confirmation before commit/push

**File location**: `.claude/skills/finish-session.md`

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
| Regenerate JSONs | `cli/db.py` (regenerate-json command) |
| Web viewer | `web/` (Astro + Tailwind) |
| CLI output formatting | `cli/helpers.py` |
| Podcast Editor stage | `cli/podcast.py` (edit cmd) + `projects/{name}/prompts/podcast_editor.md` |
| Podcast Script stage | `cli/podcast.py` (script cmd) + `projects/{name}/prompts/podcast_script.md` |
| Podcast Intro/Outro stage | `cli/podcast.py` (script cmd, tras bloques) + `projects/{name}/prompts/podcast_intro_outro.md` |
| Podcast Audio stage | `cli/podcast.py` (audio cmd) + Deepgram TTS API |
| Shared podcast helpers | `cli/podcast_helpers.py` |
| Podcast config | `projects/{name}/config.yaml` → sección `podcast.editor` + `podcast.script` + `podcast.intro_outro` |

## Non-Obvious Design Decisions

1. **Same post, different classifications**: Post can exist in multiple projects with different categories (topic-dependent classification)

2. **Selftext truncation happens AFTER classification**: Category determines truncation limit before DB save

3. **Digest only uses SIGNAL posts**: Filtered by `sent_in_digest_at IS NULL` to avoid duplicates

4. **RSS is default for Reddit**: PRAW only activates if `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` set

5. **HackerNews uses Firebase API**: No auth needed, 500 req/min limit

6. **Project isolation**: All tables have `project` column, queries always filter by project

7. **Projects as self-contained entities**: Each project in `src/claude_redditor/projects/` has its own config.yaml and prompts/. Zero code changes to add a new project.

8. **JSON filename matches digest numbering**: `outputs/web/{project}_{date}-{NN}.json` with story IDs like `{date}-{NN}-{idx}` for cross-referencing with markdown digests

9. **Digest generates both formats by default**: `--format both` is the default, creating markdown + JSON in one command

10. **regenerate-json reconstructs from DB**: Historical JSONs can be backfilled from `sent_in_digest_at` timestamps in classifications table

11. **Classifier handles API refusals**: If a batch is refused, retries with individual posts and skips problematic content

12. **Category auto-correction**: Invalid LLM categories (discussion, news, etc.) are auto-mapped to valid ones (see `CATEGORY_CORRECTIONS` in classifier.py)

13. **Podcast naming mirrors digest stem**: `claudeia_2026-04-27_01.json` → `_01_episode.json` → `_01_dialog.json`. Siempre derivar paths desde el digest stem.

14. **Podcast pipeline es secuencial por diseño**: el Guionista llama a la API una vez por bloque; `previous_blocks_summary` se acumula en memoria dentro del run. No persiste entre ejecuciones.

15. **Modelos del podcast configurables por proyecto** en `config.yaml → podcast.editor/script/intro_outro`. Editor: temp=0.4 (consistencia entre días). Guionista e Intro/Outro: temp=0.7 (variación creativa).

16. **Intro/Outro es parte de `podcast script`, no un subcomando aparte**: se genera automáticamente después del bucle de bloques (Etapa 3). Si se usa `--blocks` con subset, se salta con aviso y los campos quedan `null` en el dialog.json.

17. **dialog.json schema completo**:
    ```json
    {
      "episode_id": "claudeia_2026-04-27_01",   // identidad, incluye sufijo _01
      "episode_title": "...",                    // copia del episode.json, conveniencia
      "generated_at": "2026-04-27T08:00:00Z",
      "intro": {                                 // null si falló o --blocks parcial
        "turns": [{"speaker": "javi"|"marta", "text": "...", "pause_after_ms": 0|300|700, "emphasis": [...]}]
      },
      "blocks": [
        {"block_id": "block_1", "block_summary": "...", "turns": [...]}
      ],
      "outro": { "turns": [...] }               // null si falló o --blocks parcial
    }
    ```

18. **`pause_after_ms` reservado para SSML futuro**: valores `0/300/700ms` están en todos los turns del dialog.json pero `podcast audio` los ignora en v1 (concatenación directa). Cuando Deepgram soporte SSML o se use TTS alternativo, convertir a `<break time="300ms"/>` o clips de silencio intercalados.

19. **`podcast audio` usa `--digest-id`** igual que `podcast script`, para desambiguar cuando hay varios episodios en un mismo día. Sin él, coge el último por orden alfabético.

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

# Required for podcast audio (Deepgram TTS)
DEEPGRAM_API_KEY=...
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
