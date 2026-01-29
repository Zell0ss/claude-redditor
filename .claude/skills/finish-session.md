# Finish Session Skill

## Name
`finish-session` (invoke with `/finish-session` or `/eof`)

## Aliases
- `/eof`
- `/finish-session`
- `/session-end`

## Description
End-of-session workflow: Update documentation, commit changes, and push to repository.

## When to Use
Run this at the end of a work session to ensure all documentation is up-to-date before closing.

## Instructions

When this skill is invoked, perform the following tasks in order:

### 1. Analyze ALL Uncommitted Changes
**IMPORTANT**: First, get a complete picture of ALL changes (from any source: this session, other Claude instances, manual edits, etc.)

```bash
# See what files changed
git status

# See detailed diff statistics
git diff --stat

# See actual changes (summary)
git diff --name-only
```

**Analyze the output to identify**:
- Which files were modified/added/deleted
- Which areas of the project were affected:
  - CLI code (`src/claude_redditor/cli/`, `src/claude_redditor/*.py`)
  - Core logic (`src/claude_redditor/classifier.py`, `digest.py`, etc.)
  - Web viewer (`web/src/`, `web/astro.config.mjs`)
  - Database/models (`src/claude_redditor/db/`)
  - Configuration (`pyproject.toml`, `package.json`)
  - Documentation files themselves

**Read the actual diffs** for significant changes to understand WHAT was changed:
```bash
git diff src/
git diff web/
```

### 2. Read Documentation Standards
After understanding what changed, read the documentation standards:
```
Read: /data/ClaudeRedditor/.github/prompts/DOCUMENTATION_PROMPT.md
```

### 3. Determine Which Documentation Needs Updating

**Based on git diff analysis**, decide which documentation files need updates:

#### Decision Matrix

| If changes affect... | Then update... | Example changes |
|---------------------|----------------|-----------------|
| CLI commands (`cli/*.py`) | CLAUDE.md (commands section), README.md (if new command), QUICKSTART.md (if affects tutorial) | Added new command, changed command flags |
| Core logic (`classifier.py`, `digest.py`, `analyzer.py`) | ARCHITECTURE.md (component responsibilities, data flow), BRIEFING.md (how it works) | Changed classification logic, modified digest generation |
| Database models (`db/models.py`) | ARCHITECTURE.md (database schema section) | Added new table, modified columns |
| Project structure (new directories/modules) | CLAUDE.md (FILES section), ARCHITECTURE.md (project structure), BRIEFING.md | Added new module, restructured directories |
| Configuration (`.env`, `config.yaml`) | QUICKSTART.md (configuration step), README.md (requirements), BRIEFING.md (configuration section) | New environment variables, changed config format |
| Web viewer (`web/src/`) | web/README.md, CLAUDE.md (web section if exists) | New web components, changed UI |
| Architectural decisions | ARCHITECTURE.md (key decisions section) | Chose a new approach, changed a design pattern |
| Dependencies (`requirements.txt`, `package.json`) | README.md (requirements), BRIEFING.md (tech stack) | Added new major library |

**Output a summary** of what documentation will be updated and why, before proceeding.

### 4. Update Documentation Files

Now update the identified files following DOCUMENTATION_PROMPT.md standards:

#### For CLI Project (`/data/ClaudeRedditor/`)
- **CLAUDE.md** - Quick Context, command list, file references
- **README.md** - Major features, requirements
- **ARCHITECTURE.md** - Design decisions, data flow, components
- **BRIEFING.md** - How it works, tech stack, use cases
- **QUICKSTART.md** - Installation, setup, first use

#### For Web Viewer (`/data/ClaudeRedditor/web/`)
- **web/README.md** - Web features, setup
- Any relevant web documentation

### 5. Documentation Update Guidelines

Follow the standards from DOCUMENTATION_PROMPT.md:
- Keep README concise (elevator pitch + quick start)
- Document "why" decisions in ARCHITECTURE.md
- Update CLAUDE.md with new commands, file locations, or design decisions
- Ensure BRIEFING.md reflects current state for Claude-to-Claude transfer

### 6. Review Changes
Show the user what documentation was updated:
```bash
git diff --stat
git diff CLAUDE.md README.md ARCHITECTURE.md BRIEFING.md web/README.md
```

**Ask user**: "I've updated the documentation. Please review the changes above. Should I proceed with commit and push? (yes/no)"

If user says no, stop here and let them review/edit manually.

### 7. Commit Changes
Create a commit with clear message:
```bash
git add .
git commit -m "$(cat <<'EOF'
docs: Update documentation after session changes

- Updated [list specific changes made]
- Refreshed [specific documentation files]

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

### 8. Push to Repository
```bash
git push origin main
```

If push fails (e.g., upstream changes), inform user and suggest:
```bash
git pull --rebase origin main
git push origin main
```

### 9. Summary
Provide the user with a final summary:
- **Code files modified**: [list from git diff]
- **Documentation updated**: [list files updated]
- **Commit**: [commit hash and message]
- **Push status**: Success / Failed with reason
- **Session finalized**: ✓

## Important Notes

- **Always read DOCUMENTATION_PROMPT.md first** to ensure standards are followed
- **Only update files that need updating** - don't make unnecessary changes
- **Review before committing** - show user the diff and confirm it looks correct
- **Handle errors gracefully** - if push fails (e.g., conflicts), inform user
- **Be thorough but concise** - update what changed, not everything

## Error Handling

If errors occur:
- **Documentation update fails**: Show error, allow manual fixes
- **Commit fails**: Check if there are actually changes to commit
- **Push fails**: Check for upstream changes, suggest `git pull --rebase`

## Example Usage

```
User: /finish-session
Assistant: I'll finalize this session by analyzing changes and updating documentation.

Step 1: Analyzing ALL uncommitted changes...
[Runs: git status, git diff --stat, git diff --name-only]

Found changes in:
- src/claude_redditor/digest.py (modified)
- ARCHITECTURE.md (modified)
- .claude/skills/finish-session.md (new file)

Step 2: Reading documentation standards...
[Reads DOCUMENTATION_PROMPT.md]

Step 3: Determining which documentation needs updates...

Analysis:
- digest.py: Core logic changed → Update ARCHITECTURE.md ✓ (already done)
- New skill added → Update CLAUDE.md (add to commands)
- Architectural decision documented → ARCHITECTURE.md already updated ✓

Will update: CLAUDE.md (add finish-session command)

Step 4: Updating CLAUDE.md...
[Updates CLAUDE.md with new /finish-session command in CLI section]

Step 5: Reviewing changes...
[Shows git diff]

I've updated the documentation. Please review the changes above. 
Should I proceed with commit and push? (yes/no)

User: yes

Step 6: Committing changes...
✓ Committed: docs: Add finish-session skill and update ARCHITECTURE (a1b2c3d)

Step 7: Pushing to repository...
✓ Pushed to origin/main

Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Code files modified:
  - src/claude_redditor/digest.py
  - .claude/skills/finish-session.md (new)

Documentation updated:
  - ARCHITECTURE.md (digest generation pipeline)
  - CLAUDE.md (added /finish-session command)

Commit: a1b2c3d - docs: Add finish-session skill and update ARCHITECTURE
Push status: ✓ Success

Session finalized! ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
