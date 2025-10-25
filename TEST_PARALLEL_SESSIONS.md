# Testing Parallel Claude Code Sessions - Hands-On Guide

This guide walks you through testing the parallel session infrastructure yourself.

## Prerequisites Check

```bash
# 1. Make sure you're on main branch
git branch
# Should show: * main

# 2. Make sure everything is committed
git status
# Should show: "nothing to commit, working tree clean" or only untracked files

# 3. Check available commands
make list-sessions
# Should display WORK_LOG.md content
```

## Test 1: Create Your First Parallel Session

### Step 1: Start a new session
```bash
make new-session name=test-auth component=server
```

**Expected Output:**
- ✅ Script creates branch `session-YYYYMMDD-test-auth`
- ✅ Updates WORK_LOG.md with session details
- ✅ Shows colorful success message
- ✅ Provides next steps

### Step 2: Verify branch was created
```bash
git branch
```

**Expected Output:**
```
  main
* session-20251025-test-auth  # <-- You should be on this branch
```

### Step 3: Check WORK_LOG was updated
```bash
tail -10 WORK_LOG.md
```

**Expected Output:**
```
### Session: test-auth
- **Branch**: `session-20251025-test-auth`
- **Component**: server
- **Started**: 2025-10-25 XX:XX:XX
- **Status**: IN PROGRESS
```

### Step 4: Clean up test session
```bash
# Switch back to main
git checkout main

# Delete test branch
git branch -D session-20251025-test-auth

# Restore WORK_LOG.md
git restore WORK_LOG.md
```

**✅ Test 1 Complete!** The session creation script works.

---

## Test 2: Run Multiple Servers on Different Ports

### Terminal 1: Start first server (default port)
```bash
# Make sure you're on main
git checkout main

# Start server on default port 8001
poetry run make run
```

**Expected Output:**
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

**Leave this terminal running!**

### Terminal 2: Start second server (custom port)
```bash
# Open a NEW terminal window
cd /Users/QH37/Internal-Banking-Assistant

# Start server on port 8002
UVICORN_PORT=8002 poetry run python -m internal_assistant
```

**Expected Output:**
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8002
```

### Terminal 3: Verify both servers are running
```bash
# Open another terminal
lsof -i :8001
lsof -i :8002
```

**Expected Output:**
```
# Should show Python processes on both ports
```

### Test the servers
```bash
# Terminal 3: Test both servers
curl http://localhost:8001/health
curl http://localhost:8002/health
```

**Expected Output:**
```json
{"status":"ok"}
{"status":"ok"}
```

### Clean up
```bash
# In Terminal 1: Press Ctrl+C to stop server
# In Terminal 2: Press Ctrl+C to stop server
```

**✅ Test 2 Complete!** Multiple servers can run simultaneously.

---

## Test 3: Simulate Real Parallel Development

This simulates having 2 Claude Code sessions working simultaneously.

### Session A: Backend Feature (Terminal 1)
```bash
# Create backend feature branch
make new-session name=add-user-api component=server

# You're now on: session-YYYYMMDD-add-user-api
git branch

# Create a test file to simulate work
echo "# User API Feature" > BACKEND_WORK.md

# Commit the work
git add BACKEND_WORK.md
git commit -m "Session A: Working on user API"

# Check status
git log --oneline -1
```

### Session B: Frontend Feature (Terminal 2)
```bash
# In a NEW terminal, create frontend feature branch
cd /Users/QH37/Internal-Banking-Assistant
make new-session name=improve-feeds-ui component=ui

# You're now on: session-YYYYMMDD-improve-feeds-ui
git branch

# Create a test file to simulate work
echo "# Feeds UI Improvements" > FRONTEND_WORK.md

# Commit the work
git add FRONTEND_WORK.md
git commit -m "Session B: Working on feeds UI"

# Check status
git log --oneline -1
```

### View All Sessions (Terminal 3)
```bash
# In another terminal
cd /Users/QH37/Internal-Banking-Assistant

# List all branches
git branch -a

# Check WORK_LOG
make list-sessions
```

**Expected Output:**
```
  main
  session-20251025-add-user-api
* session-20251025-improve-feeds-ui
```

### Merge Sessions Back (Simulate Completion)
```bash
# Terminal 1: Merge Session A
git checkout main
git merge session-20251025-add-user-api --no-ff -m "Merge backend feature"

# Terminal 2: Merge Session B
git checkout main
git merge session-20251025-improve-feeds-ui --no-ff -m "Merge frontend feature"

# Clean up branches
git branch -d session-20251025-add-user-api
git branch -d session-20251025-improve-feeds-ui

# Remove test files
git rm BACKEND_WORK.md FRONTEND_WORK.md
git commit -m "Clean up test files"

# Restore WORK_LOG
git restore WORK_LOG.md
```

**✅ Test 3 Complete!** Parallel sessions can work independently and merge cleanly.

---

## Test 4: Port Conflict Detection

### Step 1: Start server on port 8001
```bash
# Terminal 1
poetry run make run
# Leave it running
```

### Step 2: Try to create session while server is running
```bash
# Terminal 2
make new-session name=test-conflict component=server
```

**Expected Output:**
```
⚠️  Port 8001 is in use
   You can use UVICORN_PORT=8002 for this session
```

### Step 3: Clean up
```bash
# Terminal 1: Ctrl+C to stop server
# Terminal 2:
git checkout main
git branch -D session-20251025-test-conflict
git restore WORK_LOG.md
```

**✅ Test 4 Complete!** Port conflict detection works.

---

## Test 5: Using Different Environments

Test data isolation with PGPT_PROFILES:

```bash
# Terminal 1: Local environment
PGPT_PROFILES=local poetry run make run
# Check logs: should use local settings

# Terminal 2: Test environment
PGPT_PROFILES=test poetry run make run
# Check logs: should use test settings

# Terminal 3: Verify different configs loaded
cat config/environments/local.yaml
cat config/environments/test.yaml
```

**✅ Test 5 Complete!** Environment isolation works.

---

## Quick Self-Test Checklist

Run through these quickly to verify everything works:

- [ ] `make list-sessions` - Shows WORK_LOG.md
- [ ] `make new-session name=test component=test` - Creates branch
- [ ] `git branch` - Shows new branch
- [ ] `tail WORK_LOG.md` - Shows session entry
- [ ] `git checkout main` - Returns to main
- [ ] `git branch -D session-*-test` - Deletes test branch
- [ ] `git restore WORK_LOG.md` - Restores clean state
- [ ] `poetry run make run` - Server starts on 8001
- [ ] `UVICORN_PORT=8002 poetry run python -m internal_assistant` - Server starts on 8002
- [ ] `lsof -i :8001` - Shows running server
- [ ] Ctrl+C - Stops servers

---

## Troubleshooting Your Tests

### Issue: "make: command not found"
**Solution:**
```bash
# Use script directly
./scripts/start_parallel_session.sh test-name component
```

### Issue: "Permission denied" on script
**Solution:**
```bash
chmod +x scripts/start_parallel_session.sh
```

### Issue: Port already in use
**Solution:**
```bash
# Find and kill process
lsof -i :8001
kill -9 <PID>

# Or use different port
UVICORN_PORT=8002 poetry run make run
```

### Issue: Branch already exists
**Solution:**
```bash
# Delete old branch
git branch -D session-YYYYMMDD-name
# Try again
```

### Issue: Uncommitted changes warning
**Solution:**
```bash
# Stash changes
git stash

# Or commit them
git add .
git commit -m "Save work in progress"
```

---

## Advanced Testing

### Test Multiple Claude Sessions (Requires Multiple Terminals)

**Terminal 1:**
```bash
make new-session name=session1 component=server
# Tell NEW Claude instance: "Work on server improvements on this branch"
poetry run make run
```

**Terminal 2:**
```bash
make new-session name=session2 component=ui
# Tell ANOTHER Claude instance: "Work on UI improvements on this branch"
UVICORN_PORT=8002 poetry run python -m internal_assistant
```

**Terminal 3:**
```bash
make new-session name=session3 component=tests
# Tell THIRD Claude instance: "Add tests on this branch"
poetry run pytest tests -v
```

Each Claude session works independently!

---

## Success Criteria

You've successfully tested the parallel session setup if:

✅ You can create new session branches with one command
✅ WORK_LOG.md automatically updates with session info
✅ Multiple servers can run on different ports
✅ Port conflict detection warns you appropriately
✅ Different branches can work independently
✅ Sessions can merge back to main cleanly
✅ Environment isolation works with PGPT_PROFILES

---

## Getting Help

If tests fail:
1. Check [docs/developer/parallel-sessions.md](docs/developer/parallel-sessions.md)
2. Review [CLAUDE.md](CLAUDE.md) Parallel Development section
3. Check `git status` and `git branch`
4. Verify you're in the correct directory
5. Ensure Poetry environment is activated

## Clean Up After Testing

```bash
# Remove all test branches
git checkout main
git branch | grep session- | xargs git branch -D

# Restore WORK_LOG
git restore WORK_LOG.md

# Remove test files if created
git clean -fd

# Verify clean state
git status
```

**Happy Testing!** 🚀
