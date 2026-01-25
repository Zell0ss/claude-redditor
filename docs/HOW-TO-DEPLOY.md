# How to Deploy ClaudeRedditor

> Guide for automating daily execution.

---

## Option 1: Cron (Simple)

### Setup

```bash
# Edit crontab
crontab -e

# Add daily job at 8:00 AM
0 8 * * * /path/to/ClaudeRedditor/.venv/bin/python -m claude_redditor scan all --include-hn --project claudeia --limit 100 && /path/to/ClaudeRedditor/.venv/bin/python -m claude_redditor digest --project claudeia >> /var/log/clauderedditor.log 2>&1
```

### Verify

```bash
# Check cron is running
grep CRON /var/log/syslog

# Check output
tail -f /var/log/clauderedditor.log
```

---

## Option 2: N8N Workflow

### Prerequisites

- N8N instance running
- SSH access to server with ClaudeRedditor

### Workflow Setup

1. **Create new workflow** in N8N

2. **Add Schedule Trigger**:
   - Type: Cron
   - Expression: `0 8 * * *` (daily at 8:00)

3. **Add SSH node** (scan):
   - Command:
     ```bash
     cd /path/to/ClaudeRedditor && \
     source .venv/bin/activate && \
     ./reddit-analyzer scan all --include-hn --project claudeia --limit 100
     ```

4. **Add SSH node** (digest):
   - Command:
     ```bash
     cd /path/to/ClaudeRedditor && \
     source .venv/bin/activate && \
     ./reddit-analyzer digest --project claudeia
     ```

5. **Add Email node** (optional):
   - Send digest markdown as email body
   - Attach JSON for reference

### Workflow Diagram

```
[Schedule Trigger] → [SSH: Scan] → [SSH: Digest] → [Email (optional)]
```

---

## Option 3: Systemd Timer

### Create service file

```bash
# /etc/systemd/system/clauderedditor.service
[Unit]
Description=ClaudeRedditor Daily Scan and Digest
After=network.target mariadb.service

[Service]
Type=oneshot
User=your_user
WorkingDirectory=/path/to/ClaudeRedditor
ExecStart=/bin/bash -c 'source .venv/bin/activate && ./reddit-analyzer scan all --include-hn --project claudeia --limit 100 && ./reddit-analyzer digest --project claudeia'
StandardOutput=append:/var/log/clauderedditor.log
StandardError=append:/var/log/clauderedditor.log

[Install]
WantedBy=multi-user.target
```

### Create timer file

```bash
# /etc/systemd/system/clauderedditor.timer
[Unit]
Description=Run ClaudeRedditor daily

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### Enable

```bash
sudo systemctl enable clauderedditor.timer
sudo systemctl start clauderedditor.timer

# Check status
systemctl status clauderedditor.timer
systemctl list-timers
```

---

## Environment Variables

Ensure the automation can access your `.env`:

```bash
# Option 1: Source .env in command
source /path/to/ClaudeRedditor/.env && ./reddit-analyzer ...

# Option 2: Systemd EnvironmentFile
[Service]
EnvironmentFile=/path/to/ClaudeRedditor/.env
```

---

## Monitoring

### Check last run

```bash
# Recent scans
./reddit-analyzer history --limit 5

# Cache stats (API savings)
./reddit-analyzer cache-stats
```

### Log rotation

```bash
# /etc/logrotate.d/clauderedditor
/var/log/clauderedditor.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

---

## Multi-Project Setup

Run multiple projects in sequence:

```bash
# Daily script
#!/bin/bash
set -e
cd /path/to/ClaudeRedditor
source .venv/bin/activate

# Project 1: AI content
./reddit-analyzer scan all --include-hn --project claudeia --limit 100
./reddit-analyzer digest --project claudeia

# Project 2: Wine content
./reddit-analyzer scan all --project wineworld --limit 50
./reddit-analyzer digest --project wineworld

echo "$(date): All projects processed" >> /var/log/clauderedditor.log
```

---

## Troubleshooting

### "Command not found"

Use full paths:
```bash
/path/to/ClaudeRedditor/.venv/bin/python -m claude_redditor ...
```

### "Database connection failed"

Ensure MariaDB is running before the job:
```bash
# Systemd: Add dependency
After=mariadb.service
```

### "API rate limited"

Reduce `--limit` or add delay between projects:
```bash
./reddit-analyzer scan ... --limit 50
sleep 60
./reddit-analyzer digest ...
```

---

## Related

- [Quick Start](../QUICKSTART.md) - First setup
- [Architecture](../ARCHITECTURE.md) - System overview
