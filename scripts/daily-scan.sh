#!/bin/bash
# Daily scan automation script
# Scans sources, generates digest, and deploys web viewer
#
# Usage:
#   ./scripts/daily-scan.sh [--project PROJECT]
#
# Add to crontab:
#   0 7 * * * /data/ClaudeRedditor/scripts/daily-scan.sh >> /data/ClaudeRedditor/logs/daily.log 2>&1

set -e

# Configuration
PROJECT="${1:-claudeia}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$ROOT_DIR/logs/$(date +%Y-%m-%d).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_success() {
    log "${GREEN}✓${NC} $1"
}

log_error() {
    log "${RED}✗${NC} $1"
}

log_info() {
    log "${YELLOW}→${NC} $1"
}

# Start
log "=========================================="
log "Starting daily digest for project: $PROJECT"
log "=========================================="

cd "$ROOT_DIR"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    log_success "Virtual environment activated"
else
    log_error "Virtual environment not found at .venv/"
    exit 1
fi

# Scan Reddit subreddits (configured per project)
log_info "Scanning Reddit..."
if ./reddit-analyzer scan all --project "$PROJECT" --limit 50; then
    log_success "Reddit scan complete"
else
    log_error "Reddit scan failed"
fi

# Scan HackerNews (configured per project)
log_info "Scanning HackerNews..."
if ./reddit-analyzer scan-hn --project "$PROJECT" --limit 30; then
    log_success "HackerNews scan complete"
else
    log_error "HackerNews scan failed"
fi

log "=========================================="
log_success "Daily scan complete!"
log "=========================================="
