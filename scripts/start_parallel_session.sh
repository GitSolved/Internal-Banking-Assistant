#!/bin/bash
# Helper script to start a new parallel Claude Code session
# Usage: ./scripts/start_parallel_session.sh <session-name> [component]
#
# Example:
#   ./scripts/start_parallel_session.sh add-auth server
#   ./scripts/start_parallel_session.sh fix-feeds ui

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check arguments
if [ -z "$1" ]; then
    echo -e "${RED}Error: Session name required${NC}"
    echo "Usage: $0 <session-name> [component]"
    echo ""
    echo "Examples:"
    echo "  $0 add-authentication server"
    echo "  $0 fix-feed-parsing ui"
    echo "  $0 update-docs docs"
    exit 1
fi

SESSION_NAME=$1
COMPONENT=${2:-general}
BRANCH_NAME="session-$(date +%Y%m%d)-${SESSION_NAME}"

echo -e "${BLUE}🚀 Starting new parallel Claude Code session${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Step 1: Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}⚠️  Warning: You have uncommitted changes${NC}"
    echo -e "${YELLOW}   Consider committing or stashing them first${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 2: Pull latest changes
echo -e "${BLUE}📥 Pulling latest changes from main...${NC}"
git fetch origin
git checkout main
git pull origin main

# Step 3: Create new branch
echo -e "${BLUE}🌿 Creating new branch: ${BRANCH_NAME}${NC}"
git checkout -b "${BRANCH_NAME}"

# Step 4: Check for port conflicts
echo -e "${BLUE}🔍 Checking for port conflicts...${NC}"
if lsof -i :8001 > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port 8001 is in use${NC}"
    echo -e "${YELLOW}   You can use UVICORN_PORT=8002 for this session${NC}"
fi

# Step 5: Update WORK_LOG.md
echo -e "${BLUE}📝 Updating WORK_LOG.md...${NC}"
cat >> WORK_LOG.md << EOF

### Session: ${SESSION_NAME}
- **Branch**: \`${BRANCH_NAME}\`
- **Component**: ${COMPONENT}
- **Started**: $(date +"%Y-%m-%d %H:%M:%S")
- **Status**: IN PROGRESS
EOF

# Step 6: Show summary
echo -e "${GREEN}✅ Session setup complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}Session Details:${NC}"
echo -e "  Branch: ${GREEN}${BRANCH_NAME}${NC}"
echo -e "  Component: ${GREEN}${COMPONENT}${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo -e "  1. Open new terminal or Claude Code session"
echo -e "  2. Tell Claude: ${YELLOW}\"Work on ${SESSION_NAME} on branch ${BRANCH_NAME}\"${NC}"
echo -e "  3. Use UVICORN_PORT=8002 if port 8001 is busy"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo -e "  View branch: ${YELLOW}git branch${NC}"
echo -e "  Check status: ${YELLOW}git status${NC}"
echo -e "  Switch back to main: ${YELLOW}git checkout main${NC}"
echo -e "  List sessions: ${YELLOW}cat WORK_LOG.md${NC}"
echo ""
