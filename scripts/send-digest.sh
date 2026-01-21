#!/bin/bash
# Send latest digest by email
#
# Usage:
#   ./scripts/send-digest.sh <project>
#
# Example:
#   ./scripts/send-digest.sh claudeia

set -e

# Configuration
PROJECT="${1:-}"
EMAIL="zelloss@gmail.com"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DIGESTS_DIR="$ROOT_DIR/outputs/digests"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_info() {
    echo -e "${YELLOW}→${NC} $1"
}

# Validate project parameter
if [ -z "$PROJECT" ]; then
    log_error "Project parameter required"
    echo "Usage: $0 <project>"
    echo "Example: $0 claudeia"
    exit 1
fi

# Find latest digest for the project
LATEST_DIGEST=$(ls -t "$DIGESTS_DIR"/digest_"${PROJECT}"_*.md 2>/dev/null | head -1)

if [ -z "$LATEST_DIGEST" ]; then
    log_error "No digest found for project: $PROJECT"
    exit 1
fi

FILENAME=$(basename "$LATEST_DIGEST")
log_info "Found latest digest: $FILENAME"

# Extract date from filename for subject
DATE=$(echo "$FILENAME" | grep -oP '\d{4}-\d{2}-\d{2}')
SUBJECT="[$PROJECT] Digest $DATE"

# Send email
log_info "Sending email to $EMAIL..."
if mail -s "$SUBJECT" "$EMAIL" < "$LATEST_DIGEST"; then
    log_success "Email sent successfully"
else
    log_error "Failed to send email"
    exit 1
fi
