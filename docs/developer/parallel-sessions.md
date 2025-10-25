# Parallel Claude Code Sessions Guide

This guide explains how to run multiple Claude Code sessions simultaneously on this codebase.

## Quick Start

### Method 1: Using Make Command (Recommended)

```bash
# Start a new parallel session
make new-session name=add-authentication component=server

# View all active sessions
make list-sessions
```

### Method 2: Manual Setup

```bash
# Pull latest changes
git pull origin main

# Create feature branch
git checkout -b feature/your-work

# Update WORK_LOG.md with your session info
# Start working!
```

## Common Scenarios

### Scenario 1: Multiple Features in Parallel

**Session 1 - Authentication**
```bash
make new-session name=add-auth component=server
# Tell Claude: "Add JWT authentication to the API"
```

**Session 2 - UI Improvements**
```bash
make new-session name=improve-feeds component=ui
# Tell Claude: "Improve the feed component UI"
```

**Session 3 - Documentation**
```bash
make new-session name=update-docs component=docs
# Tell Claude: "Update API documentation"
```

### Scenario 2: Bug Fixing + Feature Development

**Session 1 - Bug Fixes** (Higher priority)
```bash
git checkout -b hotfix/feed-parsing
# Tell Claude: "Fix the RSS feed parsing bug on this branch"
```

**Session 2 - New Feature**
```bash
git checkout -b feature/caching
# Tell Claude: "Add caching layer for API responses on this branch"
```

### Scenario 3: Testing Different Approaches

**Session 1 - Approach A**
```bash
git checkout -b experiment/redis-cache
# Tell Claude: "Implement caching using Redis"
```

**Session 2 - Approach B**
```bash
git checkout -b experiment/in-memory-cache
# Tell Claude: "Implement caching using in-memory store"
```

Later, compare results and merge the better approach.

## Port Management

If you need to run multiple servers simultaneously:

```bash
# Session 1: Default port
poetry run make run  # Port 8001

# Session 2: Custom port
UVICORN_PORT=8002 poetry run python -m internal_assistant

# Session 3: Another port
UVICORN_PORT=8003 poetry run python -m internal_assistant

# Check what's running
lsof -i :8001
lsof -i :8002
lsof -i :8003
```

## Environment Isolation

Use `PGPT_PROFILES` for different configurations:

```bash
# Session 1: Local development
PGPT_PROFILES=local poetry run make run

# Session 2: Testing environment
PGPT_PROFILES=test poetry run make run

# Session 3: Docker simulation
PGPT_PROFILES=docker poetry run make run
```

## Coordination Checklist

Before starting a new session:

- [ ] Pull latest changes: `git pull origin main`
- [ ] Check active branches: `git branch -a`
- [ ] Review WORK_LOG.md for ongoing work
- [ ] Create feature branch with descriptive name
- [ ] Update WORK_LOG.md with your session
- [ ] Check for port conflicts: `lsof -i :8001`

## Merging Work

When a session completes:

```bash
# Switch to main and update
git checkout main
git pull origin main

# Rebase your work on latest main
git checkout feature/your-branch
git rebase main

# Resolve any conflicts, then push
git push origin feature/your-branch

# Create PR
gh pr create --title "Your feature" --body "Description"
```

## Best Practices

### ✅ DO

- **Use feature branches** - One branch per session
- **Update WORK_LOG.md** - Keep team/sessions informed
- **Commit frequently** - Small, focused commits
- **Pull before pushing** - Stay synchronized
- **Document scope** - Clear descriptions in branch names

### ❌ DON'T

- **Work on main directly** - Always use branches
- **Modify same files** - Coordinate via WORK_LOG.md
- **Ignore conflicts** - Address immediately
- **Skip tests** - Run tests before merging
- **Force push** - Avoid rewriting shared history

## Troubleshooting

### Port Already in Use

```bash
# Find what's using the port
lsof -i :8001

# Kill the process
kill -9 <PID>

# Or use different port
UVICORN_PORT=8002 poetry run make run
```

### Merge Conflicts

```bash
# During rebase, if conflicts occur:
git status  # See conflicted files

# Edit files to resolve conflicts, then:
git add <resolved-files>
git rebase --continue

# Or abort and try different approach:
git rebase --abort
```

### Lost Track of Sessions

```bash
# View all branches
git branch -a

# Check WORK_LOG.md
cat WORK_LOG.md

# List recent commits
git log --oneline --all --graph -10
```

### Accidentally Committed to Wrong Branch

```bash
# Create new branch from current state
git branch feature/correct-branch

# Reset current branch
git reset --hard origin/main

# Switch to correct branch
git checkout feature/correct-branch
```

## Advanced: Component Isolation

Assign components to different sessions:

| Component | Path | Session Assignment |
|-----------|------|-------------------|
| Backend API | `internal_assistant/server/` | Session A |
| Frontend UI | `internal_assistant/ui/` | Session B |
| Testing | `tests/` | Session C |
| Documentation | `docs/` | Session D |
| Configuration | `config/` | Session E |

This minimizes conflicts and allows true parallel development.

## Examples

### Example 1: Adding New API Endpoint

```bash
# Session setup
make new-session name=add-user-endpoint component=server

# Tell Claude:
# "Create a new /api/users endpoint in internal_assistant/server/
#  Add service in users_service.py
#  Add router in users_router.py
#  Include tests in tests/server/users/
#  Work on branch session-20251025-add-user-endpoint"
```

### Example 2: Fixing UI Bug

```bash
# Session setup
make new-session name=fix-feed-display component=ui

# Tell Claude:
# "Fix the feed display bug in internal_assistant/ui/components/feeds/
#  The issue is in external_info.py where feeds aren't rendering correctly
#  Work on branch session-20251025-fix-feed-display"
```

### Example 3: Documentation Update

```bash
# Session setup
make new-session name=api-docs component=docs

# Tell Claude:
# "Update API documentation in docs/developer/
#  Add examples for new endpoints
#  Update screenshots
#  Work on branch session-20251025-api-docs"
```

## Session Templates

### Feature Development Template

```markdown
### Session: [Feature Name]
- **Branch**: `feature/[name]`
- **Component**: [component]
- **Started**: [timestamp]
- **Status**: IN PROGRESS
- **Files**:
  - [ ] Create service: `internal_assistant/server/[name]/[name]_service.py`
  - [ ] Create router: `internal_assistant/server/[name]/[name]_router.py`
  - [ ] Add tests: `tests/server/[name]/test_[name].py`
  - [ ] Update docs: `docs/developer/[name].md`
- **ETA**: [hours]
```

### Bug Fix Template

```markdown
### Session: [Bug Description]
- **Branch**: `fix/[issue]`
- **Component**: [component]
- **Started**: [timestamp]
- **Status**: IN PROGRESS
- **Issue**: [description]
- **Files**:
  - [ ] Fix in: [file path]
  - [ ] Add test: [test file]
  - [ ] Update changelog
- **ETA**: [hours]
```

## Resources

- [CLAUDE.md](../../CLAUDE.md) - Main development guide
- [WORK_LOG.md](../../WORK_LOG.md) - Active session tracker
- [Git Branching Guide](https://git-scm.com/book/en/v2/Git-Branching-Branching-Workflows)
