# Diagnostic Test Instructions - Persistence Bug

**Version:** v5_DIAGNOSTIC_LOGGING_2025-10-12

## Purpose

Identify why documents upload successfully but don't persist after server restart. The diagnostic logging will reveal whether the issue is in:
1. **Persist failure** - Files not being written to disk
2. **Load failure** - Files exist but not loading on startup
3. **Path mismatch** - Writing to different location than reading from
4. **Race condition** - Timing issue with persistence

## Test Procedure

### Step 1: Restart Server with Diagnostic Code

```bash
# Kill any running servers
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *internal*"

# Start fresh server
poetry run make run
```

**Look for in startup logs:**
```
🔧 [CODE_VERSION] ingest_component.py loaded: v5_DIAGNOSTIC_LOGGING_2025-10-12
🔧 [CODE_VERSION] This version includes comprehensive diagnostic logging for persistence debugging
[LOAD_PATH] Storage context persist dir: ...
[LOAD_PATH] Looking for docstore.json at: ...
[LOAD_PATH] ✅ Docstore file exists, size: X bytes
[LOAD_PATH] Docstore contains X ref_doc_info entries in file
[LOAD_PATH] ✅ After load: index.docstore has X ref_doc_info entries in memory
```

**Critical Question 1:** Do the file count and memory count MATCH after load?
- If YES: Load is working correctly
- If NO: Load is failing - file has more entries than memory

### Step 2: Note Baseline Document Count

Open UI: http://localhost:8001

**Document current state:**
- Header shows: "📄 X Documents"
- Note the number: ________

### Step 3: Upload 2 Test Files

Create test files:
```bash
echo "Test document 1" > test_doc_1.txt
echo "Test document 2" > test_doc_2.txt
```

Upload both files via UI.

**Immediately check header:**
- Should show: "📄 (X+2) Documents"
- Does it update? YES / NO

### Step 4: Check Upload Logs

Search latest log file for diagnostic markers:

```bash
# Get latest log
$LOG = Get-ChildItem local_data\logs\SessionLog*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1

# Check if persist was called
Select-String -Path $LOG -Pattern "\[PERSIST_CALLSTACK\]"

# Check persist path
Select-String -Path $LOG -Pattern "\[PERSIST_PATH\]"

# Check if persist succeeded
Select-String -Path $LOG -Pattern "\[PERSIST_SUCCESS\]"

# Check if persist failed
Select-String -Path $LOG -Pattern "\[PERSIST_FAILURE\]"

# Check final verification
Select-String -Path $LOG -Pattern "\[DEBUG\] FINAL VERIFICATION"
```

**Critical Questions:**

**Q2:** Is `[PERSIST_CALLSTACK]` present?
- If NO: **_save_index() is NOT being called!**
- If YES: Continue to Q3

**Q3:** What path is shown in `[PERSIST_PATH]`?
- Path: ________________________________
- Compare with `[LOAD_PATH]` from startup
- Do they MATCH? YES / NO

**Q4:** Is `[PERSIST_SUCCESS]` shown for both persist calls?
- storage_context.persist(): YES / NO
- docstore.persist(): YES / NO

**Q5:** Does `[PERSIST_FAILURE]` appear?
- If YES: **Persist is failing!** Check exception details
- If NO: Persist succeeded, continue to Q6

**Q6:** What does `[DEBUG] FINAL VERIFICATION` show?
- Memory count: ________
- File count: ________
- Do they MATCH? YES / NO

**Q7:** What is the file size after persist?
- File size: ________ bytes
- If 0 bytes: **File is EMPTY - persist not working!**
- If >0 bytes but small: **File has data but maybe not all documents**

### Step 5: Verify File Manually

```bash
# Check if file exists
Test-Path local_data\internal_assistant\docstore.json

# Check file size
(Get-Item local_data\internal_assistant\docstore.json).Length

# Count ref_doc_info entries
$data = Get-Content local_data\internal_assistant\docstore.json | ConvertFrom-Json
$data."docstore/ref_doc_info".PSObject.Properties.Count
```

**Critical Question 8:** How many entries in file?
- Count: ________
- Should be: X + 2 (baseline + 2 uploads)
- Actual vs Expected: ________

### Step 6: Restart Server and Check Load

```bash
# Restart server
Ctrl+C to stop
poetry run make run
```

**Look for in logs:**
```
[LOAD_PATH] Docstore contains X ref_doc_info entries in file
[LOAD_PATH] ✅ After load: index.docstore has Y ref_doc_info entries in memory
```

**Critical Question 9:** Do file count (X) and memory count (Y) match?
- File has: ________
- Memory has: ________
- Match? YES / NO

**Critical Question 10:** Does header show correct count?
- Header shows: ________
- Should be: ________ (baseline + 2)
- Correct? YES / NO

## Diagnosis Matrix

### Scenario A: Persist NOT Called
**Symptoms:**
- No `[PERSIST_CALLSTACK]` in logs
- No `[PERSIST_PATH]` messages

**Diagnosis:** `_save_index()` is not being called by upload flow

**Fix:** Check upload code path, ensure `_save_docs()` calls `_save_index()`

### Scenario B: Persist Fails
**Symptoms:**
- `[PERSIST_CALLSTACK]` present
- `[PERSIST_FAILURE]` shown
- Exception in logs

**Diagnosis:** Permission issue, disk full, or API error

**Fix:** Check exception details, fix underlying issue

### Scenario C: Persist Succeeds but File Empty
**Symptoms:**
- `[PERSIST_SUCCESS]` shown
- File size = 0 bytes
- `[DEBUG] FINAL VERIFICATION` shows 0 in file

**Diagnosis:** Persist API succeeds but writes nothing

**Fix:** Bug in LlamaIndex persist implementation or docstore is empty before persist

### Scenario D: Path Mismatch
**Symptoms:**
- `[PERSIST_PATH]` shows path A
- `[LOAD_PATH]` shows path B
- File exists but wrong location

**Diagnosis:** Storage context configured with different paths

**Fix:** Ensure consistent `local_data_path` usage

### Scenario E: Persist Works, Load Fails
**Symptoms:**
- File has N entries (correct)
- After load, memory has <N entries
- `[LOAD_PATH]` shows mismatch

**Diagnosis:** `load_index_from_storage()` not loading docstore properly

**Fix:** Check storage_context initialization, ensure docstore is loaded

### Scenario F: Memory-Disk Mismatch
**Symptoms:**
- Memory shows X documents
- File shows Y documents (Y < X)
- `[DEBUG] ❌ MISMATCH` in logs

**Diagnosis:** Persist writes less than what's in memory

**Fix:** Bug in docstore.persist() or ref_doc_info not fully populated before persist

## Expected Results

**If everything works correctly:**

1. ✅ Upload 2 files → Header shows +2
2. ✅ `[PERSIST_CALLSTACK]` appears
3. ✅ `[PERSIST_SUCCESS]` for both persist calls
4. ✅ File size increases by several KB
5. ✅ `[DEBUG] ✅ Memory and disk counts MATCH`
6. ✅ Restart server → `[LOAD_PATH]` shows same count in file and memory
7. ✅ Header still shows correct total count

## Collecting Results

After completing the test, collect:

1. **Startup logs** (from Step 1):
   - Version marker
   - Load path and counts

2. **Upload logs** (from Step 4):
   - Persist callstack
   - Persist path
   - Success/failure messages
   - Final verification

3. **File verification** (from Step 5):
   - File exists: YES/NO
   - File size: ______ bytes
   - Entry count: ______

4. **Reload logs** (from Step 6):
   - Load count from file
   - Load count in memory
   - Match: YES/NO

5. **UI verification**:
   - Header count after upload: ________
   - Header count after restart: ________
   - Correct: YES/NO

Share these results to diagnose the issue!
