#!/bin/bash
# Daily digest automation script
# Scans sources, generates digest, and deploys web viewer
#
# Usage:
#   ./scripts/daily-digest.sh [--project PROJECT] [--skip-deploy]
#
# Add to crontab:
#   0 7 * * * /data/ClaudeRedditor/scripts/daily-digest.sh >> /data/ClaudeRedditor/logs/daily.log 2>&1

set -e

# Configuration
PROJECT="${1:-claudeia}"
SKIP_DEPLOY="${2:-}"
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

# Scan all sources (Reddit + HackerNews, configured per project)
log_info "Scanning all sources..."
if ./reddit-analyzer scan "$PROJECT" --limit 50; then
    log_success "Scan complete"
else
    log_error "Scan failed"
fi

# Generate digest (markdown + JSON by default)
log_info "Generating digest..."
if ./reddit-analyzer digest --project "$PROJECT" --limit 15; then
    log_success "Digest generated"
else
    log_error "Digest generation failed"
    exit 1
fi

# Build and deploy web (unless --skip-deploy)
if [ "$SKIP_DEPLOY" != "--skip-deploy" ]; then
    log_info "Building web viewer..."
    cd web

    if npm run build; then
        log_success "Web build complete"
    else
        log_error "Web build failed"
        exit 1
    fi

    log_info "Deploying to Cloudflare Pages..."
    if npx wrangler pages deploy dist/ --project-name=clauderedditor-web; then
        log_success "Deploy complete"
    else
        log_error "Deploy failed"
        exit 1
    fi

    cd "$ROOT_DIR"
else
    log_info "Skipping deploy (--skip-deploy flag)"
fi

log "=========================================="
log_success "Daily digest complete!"
log "=========================================="
