# How to Add a New Project

> Guide to create a new project for monitoring another topic.

**Zero code changes required** - just create configuration files.

---

## Step 1: Create Project Directory

```bash
mkdir -p src/claude_redditor/projects/myproject/prompts
```

---

## Step 2: Create config.yaml

```bash
# src/claude_redditor/projects/myproject/config.yaml
```

```yaml
name: myproject
description: "Brief description of what this project monitors"

topic: "Detailed description of the topic for classification context"

sources:
  reddit:
    subreddits:
      - Subreddit1
      - Subreddit2
  hackernews:
    keywords:
      - keyword1
      - keyword2
      - "multi word keyword"
```

### Example: Wine Industry Project

```yaml
name: wineworld
description: "Wine industry content for La Gaceta del Vino"

topic: "Wine, viticulture, winemaking, tasting, and wine industry news"

sources:
  reddit:
    subreddits:
      - wine
      - winemaking
      - viticulture
  hackernews:
    keywords:
      - wine
      - vineyard
      - sommelier
```

---

## Step 3: Create classify.md Prompt

Copy from an existing project and adapt:

```bash
cp src/claude_redditor/projects/claudeia/prompts/classify.md \
   src/claude_redditor/projects/myproject/prompts/classify.md
```

### Customize Categories (Optional)

Edit the prompt to add topic-specific categories:

```markdown
### SIGNAL (Useful Content)
- **technical**: [Your definition for this topic]
- **troubleshooting**: [Your definition]
- **research_verified**: [Your definition]

### NOISE (Problematic Content)
- **mystical**: [Your definition]
- **unverified_claim**: [Your definition]
- **engagement_bait**: [Your definition]
```

### Customize Topic Tags (Optional)

```markdown
## Topic Tags (multi-select)

- `tasting`: Wine tasting notes, reviews
- `winemaking`: Production techniques
- `viticulture`: Grape growing, vineyard management
- `business`: Industry news, market trends
```

---

## Step 4: Create digest.md Prompt

Copy and adapt:

```bash
cp src/claude_redditor/projects/claudeia/prompts/digest.md \
   src/claude_redditor/projects/myproject/prompts/digest.md
```

### Customize Newsletter Name

Edit the digest prompt to change:
- Newsletter name (e.g., "Wine Weekly Digest")
- Tone and style
- Article format

---

## Step 5: Verify Project Discovery

```bash
./reddit-analyzer config
```

**Expected output**:
```
Projects (auto-discovered):
  • claudeia - AI and LLM content
  • wineworld - Wine industry content
  • myproject - Brief description  ← Your new project
```

---

## Step 6: Test Your Project

```bash
# Scan with your project
./reddit-analyzer scan Subreddit1 --project myproject --limit 10

# Check classifications
./reddit-analyzer history --project myproject

# Generate digest
./reddit-analyzer digest --project myproject --dry-run
```

---

## Project Structure Summary

```
src/claude_redditor/projects/myproject/
├── config.yaml           # Sources and topic definition
└── prompts/
    ├── classify.md       # Classification prompt (categories, red flags)
    └── digest.md         # Newsletter generation prompt
```

---

## Tips

### Keep Categories Consistent

The 10 base categories work for most topics:
- `technical`, `troubleshooting`, `research_verified` (SIGNAL)
- `mystical`, `unverified_claim`, `engagement_bait` (NOISE)
- `community`, `meme` (META)
- `outlier`, `unrelated`

Only customize if your topic has specific patterns.

### Topic Tags Are Project-Specific

Define tags relevant to your domain:
- AI project: `prompts`, `tools`, `models`, `research`
- Wine project: `tasting`, `winemaking`, `viticulture`, `business`

### Test with Small Batches

Start with `--limit 10` to verify classifications look correct.

### HackerNews Keywords

Use broad keywords - HN filtering is basic keyword matching:
- Good: `wine`, `vineyard`
- Too specific: `Napa Valley Cabernet 2024`

---

## Common Issues

### "Project not found"

Check:
1. Directory name matches `--project` flag
2. `config.yaml` exists and has valid YAML
3. `name:` in config.yaml matches directory name

### "No posts classified"

Check:
1. Subreddits exist and have posts
2. HN keywords match recent stories
3. Try without `--project` to debug

### Classifications seem wrong

1. Review `prompts/classify.md` definitions
2. Check `topic:` in config.yaml is clear
3. Run with `--no-cache` to force re-classification

---

## Related

- [Architecture](../ARCHITECTURE.md) - How classification works
- [Quick Start](../QUICKSTART.md) - First setup
