# JavaScript Management Module

This directory contains the JavaScript management infrastructure for the Internal Assistant UI, created as part of Phase 0.7 of the UI refactoring roadmap.

## Purpose
Extract and modularize ~1,850 lines of embedded JavaScript from ui.py to achieve better maintainability and further reduce the main UI file size.

## Structure

```
Javascript/
├── __init__.py           # Module initialization
├── js_manager.py         # JavaScript loading and injection manager
├── README.md            # This file
└── modules/             # JavaScript modules
    ├── ui_common.js     # Shared utility functions
    ├── collapsible.js   # Document organization (~1,000 lines)
    └── mode_selector.js # Mode button management (~300 lines)
```

## Modules

### js_manager.py
- `JSManager` class - Similar to CSSManager, handles loading JavaScript modules
- Methods:
  - `load_module(module_name)` - Load a specific JavaScript file
  - `get_script_tags()` - Generate HTML script tags for all modules
  - `get_inline_scripts()` - Get combined JavaScript for inline inclusion
  - `clear_cache()` - Clear the JavaScript cache

### modules/ui_common.js
- Shared utility functions
- DOM helpers (ready, safeQuerySelector)
- Logging utilities
- Debounce function

### modules/collapsible.js
- Document organization functionality
- `toggleSection(header)` - Toggle individual sections
- `toggleAllSections(button)` - Expand/collapse all sections
- Extracted from ui.py lines 680-702 and 1173-2119

### modules/mode_selector.js
- Mode selection button management
- `updateModeButtonColors(activeMode)` - Update button colors based on active mode
- Extracted from ui.py lines 2222-2533

## Usage

In ui.py:
```python
from tools.Javascript.js_manager import JSManager

# In UI class constructor
self.js_manager = JSManager()

# In Gradio interface
gr.HTML(self.js_manager.get_script_tags())
```

## Impact
- Removes ~1,850 lines from ui.py
- Reduces ui.py from 3,226 to ~1,400 lines
- Achieves 78% total reduction from original 6,357 lines
- Improves maintainability and code organization