# Page Refresh Fix - Document Count Not Updating

**Date:** 2025-10-12
**Status:** ✅ IMPLEMENTED

## Problem Summary

Documents were persisting correctly to disk (proven by server restart showing correct count), but when users refreshed the browser page (F5), the header count would revert to the old value instead of showing the current count from the database.

**User's Test Results:**
1. Server starts → 29 documents
2. Upload 4 files → Shows 33 documents ✅
3. **Refresh page (F5)** → Shows 29 documents ❌ (lost 4!)
4. Refresh again → Still 29 ❌
5. **Restart server** → Shows 33 documents ✅ (persistence works!)

## Root Cause

The `model_status_display` Gradio HTML component was initialized once with a static value when the server started, and this value persisted across page refreshes:

```python
# Line ~1660 in ui.py
model_status_display = gr.HTML(
    value=self._doc_state_manager.get_model_status(),  # ← Called ONCE at server startup
)
```

**Timeline of the bug:**
1. **Server starts** → `get_model_status()` called → Returns "29 documents" → Component created
2. **Upload 4 files** → Event handler updates component → Shows "33 documents" ✅
3. **User refreshes page (F5)** → Browser reloads → Gradio re-renders with ORIGINAL value "29 documents" ❌
4. **Server restarts** → `get_model_status()` called again → Returns "33 documents" (loaded from disk) → Component recreated ✅

The component value was set once at server startup and cached across all page refreshes until the server restarted.

## The Fix

Added a Gradio `.load()` event handler that refreshes the document status whenever the page loads.

### Code Changes

**File:** `internal_assistant/ui/ui.py` (lines 2907-2936)

**Added:**
```python
# CRITICAL FIX: Refresh document count on page load
def refresh_document_status_on_page_load():
    """Refresh document count and library when page loads.

    This ensures the header shows the current document count
    even after page refresh (F5), by querying the database
    instead of using the cached value from server startup.
    """
    logger.info("🔄 [PAGE_LOAD] Page loaded, refreshing document status...")
    updated_model_status = self._doc_state_manager.get_model_status()
    updated_file_list = self._doc_utility_builder.format_file_list()
    updated_document_library = self._doc_library_builder.get_document_library_html()
    logger.info("✅ [PAGE_LOAD] Document status refreshed")

    return (
        updated_model_status,
        updated_file_list,
        updated_document_library,
    )

# Register page load event for document status refresh
blocks.load(
    fn=refresh_document_status_on_page_load,
    outputs=[
        model_status_display,
        ingested_dataset,
        document_library_content,
    ],
)
```

### How It Works

**Before the fix:**
```
Page Load → Use cached value from server startup → Show old count
```

**After the fix:**
```
Page Load → Trigger .load() event → Query database via get_model_status() → Show current count
```

The `.load()` event ensures the header ALWAYS reflects the current database state on every page load by:
1. Calling `get_model_status()` which queries `ingest_service.list_ingested()`
2. Counting the actual documents in the database
3. Updating the `model_status_display` component with the current count

## Testing Instructions

### Test 1: Page Refresh After Upload
```
1. Note current document count (e.g., 29)
2. Upload 4 files
3. ✅ Header should show 33 (29 + 4)
4. Press F5 to refresh page
5. ✅ Header should STILL show 33 (not revert to 29)
6. Upload 2 more files
7. ✅ Header should show 35
8. Refresh page again
9. ✅ Header should show 35
```

### Test 2: Server Restart
```
1. Upload 5 files → Note count (e.g., 38)
2. Restart server (Ctrl+C then `poetry run make run`)
3. ✅ Header should show 38 (persistence works)
4. Refresh page
5. ✅ Header should STILL show 38 (not revert to old value)
```

### Test 3: Multiple Browser Tabs
```
1. Open UI in two tabs
2. Tab 1: Upload 3 files
3. Tab 1: Shows +3 documents ✅
4. Tab 2: Refresh page (F5)
5. Tab 2: Should show +3 documents ✅
```

### Test 4: Verify Logs
```
# After refreshing page, check logs for:
grep "\[PAGE_LOAD\]" local_data/logs/SessionLog*.log

# Should see:
🔄 [PAGE_LOAD] Page loaded, refreshing document status...
✅ [PAGE_LOAD] Document status refreshed
```

## Expected Results

After this fix:
- ✅ Upload files → Header updates immediately
- ✅ **Refresh page (F5) → Header shows current count from database**
- ✅ Restart server → Header shows persisted count
- ✅ Multiple tabs → All show same count after refresh
- ✅ No more "lost documents" on page refresh

## Related Fixes

This fix complements the earlier work:

1. **Document persistence fix** (v4 - ingest_component.py:121-125)
   - Added explicit `docstore.persist()` call
   - Ensures documents write to disk

2. **ref_doc_info population fix** (v4 - ingest_component.py:232-266)
   - Manually populates `ref_doc_info` for Qdrant
   - Fixes document enumeration

3. **Upload header update fix** (UI_HEADER_COUNT_FIX.md)
   - Added `model_status_display` to upload event outputs
   - Updates header on upload

4. **Page refresh fix** (this fix)
   - Added `.load()` event to refresh on page load
   - Fixes stale count after page refresh

All four fixes together ensure:
- Documents persist to disk ✅
- Documents appear in UI after upload ✅
- Header updates on upload ✅
- **Header updates on page refresh ✅** ← NEW

## Technical Notes

**Why Gradio doesn't auto-refresh:**

Gradio components are initialized once with a `value` parameter. This value persists across page refreshes within the same server session because:
- The server maintains the UI state in memory
- Page refresh re-renders the UI but uses the cached component state
- Only server restart recreates components with fresh values

**The `.load()` event:**

Gradio's `.load()` event fires when:
- Page first loads
- User refreshes the page (F5)
- User navigates back to the page

This makes it perfect for ensuring components show current data on every page view.

**Performance consideration:**

The `.load()` event queries the database on every page load. This is acceptable because:
- Query is fast (just counting documents)
- Page loads are infrequent (user action)
- Ensures data consistency is worth the small cost

## Summary

**Problem:** Page refresh showed stale document count from server startup instead of current count from database.

**Cause:** Gradio HTML component initialized once with static value that persisted across page refreshes.

**Solution:** Added `.load()` event that queries database and updates component on every page load.

**Result:** Header now shows accurate, real-time document count that persists across uploads, deletes, page refreshes, and server restarts. ✅
