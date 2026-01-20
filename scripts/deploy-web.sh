#!/bin/bash
# Deploy web viewer to Cloudflare Pages
# Called by n8n after digest generation
#
# Usage:
#   ./scripts/deploy-web.sh
#
# Requirements:
#   - CLOUDFLARE_API_TOKEN environment variable set
#   - npm and wrangler installed
#
# Exit codes:
#   0 - Success
#   1 - Build failed
#   2 - Deploy failed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
WEB_DIR="$ROOT_DIR/web"

# Ensure PATH includes node/npm from nvm for non-interactive shells
# Explicit path for this server's nvm installation
export PATH="/home/ubuntu/.nvm/versions/node/v22.18.0/bin:$PATH:/usr/local/bin:/usr/bin"

# Load environment from .env if CLOUDFLARE_API_TOKEN not set
# This handles non-interactive shells (n8n, cron, etc.)
if [ -z "$CLOUDFLARE_API_TOKEN" ] && [ -f "$ROOT_DIR/.env" ]; then
    export $(grep -E '^CLOUDFLARE_API_TOKEN=' "$ROOT_DIR/.env" | xargs)
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log_success() {
    log "${GREEN}✓${NC} $1"
}

log_error() {
    log "${RED}✗${NC} $1"
}

# Check requirements
if [ -z "$CLOUDFLARE_API_TOKEN" ]; then
    log_error "CLOUDFLARE_API_TOKEN not set"
    exit 2
fi

if ! command -v npm &> /dev/null; then
    log_error "npm not found"
    exit 1
fi

# Build
log "Building web viewer..."
cd "$WEB_DIR"

if npm run build; then
    log_success "Build complete"
else
    log_error "Build failed"
    exit 1
fi

# Deploy
log "Deploying to Cloudflare Pages..."
if npx wrangler pages deploy dist/ --project-name=clauderedditor-web; then
    log_success "Deploy complete"
else
    log_error "Deploy failed"
    exit 2
fi

log_success "Web viewer deployed successfully"
