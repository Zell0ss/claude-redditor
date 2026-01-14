# N8N Integration Guide: Daily Digest Automation

This guide explains how to set up N8N to automatically generate and send the "La Gaceta IA" daily digest via email.

## Overview

The workflow will:
1. Run daily at a scheduled time
2. Execute the `reddit-analyzer digest` command
3. Read the generated markdown file
4. Send it via email

## Prerequisites

- N8N instance running (self-hosted or cloud)
- SSH access to the server where ClaudeRedditor is installed
- Email credentials (SMTP or service like Gmail, SendGrid)

---

## Workflow Setup

### Step 1: Schedule Trigger

Add a **Schedule Trigger** node:

| Setting | Value |
|---------|-------|
| Trigger Times | Custom (Cron) |
| Cron Expression | `0 9 * * *` |

This triggers the workflow every day at 9:00 AM. Adjust the time as needed.

---

### Step 2: Execute Command

Add an **Execute Command** node (or **SSH** node if N8N runs remotely):

**If N8N runs on the same server:**

| Setting | Value |
|---------|-------|
| Command | `cd /data/ClaudeRedditor && source .venv/bin/activate && ./reddit-analyzer digest --project claudeia --limit 15` |

**If N8N runs remotely (SSH node):**

| Setting | Value |
|---------|-------|
| Host | `your-server-ip` |
| Port | `22` |
| Username | `your-username` |
| Authentication | Private Key or Password |
| Command | `cd /data/ClaudeRedditor && source .venv/bin/activate && ./reddit-analyzer digest --project claudeia --limit 15` |

**Output:** The command outputs the file path on the last line, e.g.:
```
outputs/digests/digest_claudeia_2026-01-14_01.md
```

---

### Step 3: Extract File Path

Add a **Code** node to extract the file path from stdout:

```javascript
// Extract the last non-empty line (file path)
const stdout = $input.first().json.stdout || '';
const lines = stdout.trim().split('\n');
const filePath = lines[lines.length - 1].trim();

// Build absolute path
const absolutePath = filePath.startsWith('/')
  ? filePath
  : `/data/ClaudeRedditor/${filePath}`;

return [{
  json: {
    filePath: absolutePath,
    fileName: filePath.split('/').pop()
  }
}];
```

---

### Step 4: Read File

Add a **Read Binary File** node (or **Execute Command** with `cat`):

**Option A: Read Binary File node**

| Setting | Value |
|---------|-------|
| File Path | `{{ $json.filePath }}` |

**Option B: Execute Command with cat**

| Setting | Value |
|---------|-------|
| Command | `cat "{{ $json.filePath }}"` |

---

### Step 5: Send Email

Add an **Email Send** node (or service-specific node like Gmail, SendGrid):

**Using SMTP (Email Send node):**

| Setting | Value |
|---------|-------|
| From Email | `digest@yourdomain.com` |
| To Email | `your-email@example.com` |
| Subject | `La Gaceta IA - {{ new Date().toISOString().split('T')[0] }}` |
| Email Format | Text (Markdown) or HTML |
| Body | `{{ $json.data }}` (from Read File) or `{{ $('Read File').item.json.stdout }}` |

**For HTML emails:** You may want to add a **Markdown to HTML** conversion step using a Code node:

```javascript
// Simple markdown to HTML (or use a library)
const markdown = $input.first().json.data;

// Basic conversion (for better results, use a markdown library)
let html = markdown
  .replace(/^### (.*$)/gim, '<h3>$1</h3>')
  .replace(/^## (.*$)/gim, '<h2>$1</h2>')
  .replace(/^# (.*$)/gim, '<h1>$1</h1>')
  .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
  .replace(/\*(.*)\*/gim, '<em>$1</em>')
  .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2">$1</a>')
  .replace(/\n/gim, '<br>');

return [{ json: { html } }];
```

---

## Complete Workflow Diagram

```
┌─────────────────┐
│ Schedule Trigger│
│ (Daily 9:00 AM) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Execute Command │
│ reddit-analyzer │
│ digest ...      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Code Node     │
│ Extract file    │
│ path from stdout│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Read File       │
│ (markdown)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ (Optional)      │
│ Convert to HTML │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Send Email    │
└─────────────────┘
```

---

## Error Handling

### Add an IF node after Execute Command

Check if the command succeeded:

| Setting | Value |
|---------|-------|
| Condition | `{{ $json.exitCode }}` equals `0` |

**True branch:** Continue to Read File
**False branch:** Send error notification

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "No signal posts available" | No new posts to include | Run a scan first or wait for new content |
| Exit code 1 | Command failed | Check logs, ensure .env is configured |
| File not found | Path extraction failed | Verify the code node regex |

---

## Alternative: Full Scan + Digest Workflow

For a complete daily automation:

```
┌─────────────────┐
│ Schedule Trigger│
│ (Daily 8:00 AM) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Execute Command │
│ reddit-analyzer │
│ scan-hn ...     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Execute Command │
│ reddit-analyzer │
│ scan all ...    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Wait 5 minutes  │
│ (let scans run) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Execute Command │
│ reddit-analyzer │
│ digest ...      │
└────────┬────────┘
         │
         ▼
│ ... (rest of workflow)
```

**Commands:**

```bash
# Step 1: Scan HackerNews
cd /data/ClaudeRedditor && source .venv/bin/activate && ./reddit-analyzer scan-hn --project claudeia --limit 100

# Step 2: Scan Reddit
cd /data/ClaudeRedditor && source .venv/bin/activate && ./reddit-analyzer scan all --project claudeia --limit 50

# Step 3: Generate digest
cd /data/ClaudeRedditor && source .venv/bin/activate && ./reddit-analyzer digest --project claudeia --limit 15
```

---

## Testing

Before enabling the schedule:

1. **Manual trigger:** Click "Execute Workflow" in N8N
2. **Check output:** Verify each node produces expected data
3. **Test email:** Confirm email arrives with correct formatting

---

## Environment Variables

Ensure your server has these configured in `/data/ClaudeRedditor/.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...
MYSQL_HOST=localhost
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=reddit_analyzer
```

---

## Troubleshooting

### Command not found
```bash
# Ensure the venv is activated
source /data/ClaudeRedditor/.venv/bin/activate
which reddit-analyzer
```

### Permission denied
```bash
# Make sure the script is executable
chmod +x /data/ClaudeRedditor/reddit-analyzer
```

### Database connection failed
```bash
# Test MySQL connection
mysql -u your_user -p reddit_analyzer -e "SELECT 1"
```

---

## Support

For issues with:
- **ClaudeRedditor:** https://github.com/Zell0ss/claude-redditor/issues
- **N8N:** https://community.n8n.io/
