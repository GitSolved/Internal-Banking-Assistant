/**
 * UI Common JavaScript Module
 * 
 * Shared utility functions and common functionality for the Internal Assistant UI.
 * Extracted from ui.py during Phase 0.7 refactoring.
 */

// Common utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// DOM ready helper
function ready(fn) {
    if (document.readyState !== 'loading') {
        fn();
    } else {
        document.addEventListener('DOMContentLoaded', fn);
    }
}

// Safe element query
function safeQuerySelector(selector, parent = document) {
    try {
        return parent.querySelector(selector);
    } catch (e) {
        console.warn('Invalid selector:', selector, e);
        return null;
    }
}

// Safe element query all
function safeQuerySelectorAll(selector, parent = document) {
    try {
        return parent.querySelectorAll(selector);
    } catch (e) {
        console.warn('Invalid selector:', selector, e);
        return [];
    }
}

// Console logging wrapper for debugging
const UILogger = {
    debug: function(...args) {
        if (window.DEBUG_MODE) {
            console.log('[UI Debug]', ...args);
        }
    },
    info: function(...args) {
        console.info('[UI Info]', ...args);
    },
    warn: function(...args) {
        console.warn('[UI Warning]', ...args);
    },
    error: function(...args) {
        console.error('[UI Error]', ...args);
    }
};

// Export for use in other modules (if using module system)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        debounce,
        ready,
        safeQuerySelector,
        safeQuerySelectorAll,
        UILogger
    };
}