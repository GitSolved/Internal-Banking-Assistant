/**
 * Mode Selector JavaScript Module
 * 
 * Handles mode selection button coloring and management for the Internal Assistant UI.
 * Extracted from ui.py lines 2222-2533 during Phase 0.7 refactoring.
 */

// Dynamic Button Coloring for Mode Selection
function updateModeButtonColors(activeMode) {
    console.log('Updating mode button colors for:', activeMode);
    const selectors = ['.mode-selector', '.chat-mode-selector'];
    
    selectors.forEach(selector => {
        const radioButtons = document.querySelectorAll(`${selector} input[type="radio"]`);
        const labels = document.querySelectorAll(`${selector} label`);
    
    // Force a slight delay to ensure DOM is ready
    setTimeout(() => {
        radioButtons.forEach((radio, index) => {
            const label = labels[index];
            if (label) {
                // Remove existing dynamic classes
                label.classList.remove('mode-active', 'mode-inactive');
                
                // Determine if this is the active mode
                const isDocumentMode = radio.value.includes('RAG Mode');
                const isGeneralMode = radio.value.includes('General LLM');
                const shouldBeActive = (activeMode === 'document' && isDocumentMode) || 
                                      (activeMode === 'general' && isGeneralMode) ||
                                      radio.checked;
                
                console.log('Radio:', radio.value, 'Checked:', radio.checked, 'Should be active:', shouldBeActive);
                
                if (shouldBeActive) {
                    // Active mode - blue coloring
                    label.classList.add('mode-active');
                    console.log('Applied mode-active to:', radio.value);
                } else {
                    // Inactive mode - green coloring
                    label.classList.add('mode-inactive');
                    console.log('Applied mode-inactive to:', radio.value);
                }
            }
        });
    }, 10);
}

// Initialize button colors on page load
function initializeModeButtonColors() {
    console.log('Initializing mode button colors');
    const selectors = ['.mode-selector', '.chat-mode-selector'];
    
    selectors.forEach(selector => {
        const checkedRadio = document.querySelector(`${selector} input[type="radio"]:checked`);
        if (checkedRadio) {
            console.log('Found checked radio:', checkedRadio.value);
            if (checkedRadio.value.includes('RAG Mode')) {
                updateModeButtonColors('document');
            } else if (checkedRadio.value.includes('General LLM')) {
                updateModeButtonColors('general');
            }
        }
    });
}

// Force button colors to persist - continuous monitoring
function ensureButtonColorsPersist() {
    const selectors = ['.mode-selector', '.chat-mode-selector'];
    
    selectors.forEach(selector => {
        const checkedRadio = document.querySelector(`${selector} input[type="radio"]:checked`);
        if (checkedRadio) {
            const activeLabel = checkedRadio.nextElementSibling;
            if (activeLabel && !activeLabel.classList.contains('mode-active')) {
                console.log('Forcing mode-active class on checked radio');
                activeLabel.classList.remove('mode-inactive');
                activeLabel.classList.add('mode-active');
            }
        }
    });
}

// Mode-specific controls visibility and functionality
function toggleModeControls(mode) {
    const generalControls = document.querySelector('[data-testid*="general_controls"]') || 
                           document.querySelector('div:has(> div:contains("General LLM Tools"))');
    const documentControls = document.querySelector('[data-testid*="document_controls"]') ||
                            document.querySelector('div:has(> div:contains("Document Assistant Tools"))');
    
    if (mode === 'general') {
        if (generalControls) generalControls.style.display = 'block';
        if (documentControls) documentControls.style.display = 'none';
    } else if (mode === 'document') {
        if (generalControls) generalControls.style.display = 'none';
        if (documentControls) documentControls.style.display = 'block';
    }
}

// Keyboard shortcuts
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + 1 = Document Assistant
        if ((e.ctrlKey || e.metaKey) && e.key === '1') {
            e.preventDefault();
            const docRadio = document.querySelector('input[value*="Document Assistant"]');
            if (docRadio) {
                docRadio.click();
                showKeyboardShortcutFeedback('Document Assistant Mode');
            }
        }
        // Ctrl/Cmd + 2 = General Assistant  
        else if ((e.ctrlKey || e.metaKey) && e.key === '2') {
            e.preventDefault();
            const genRadio = document.querySelector('input[value*="General Assistant"]');
            if (genRadio) {
                genRadio.click();
                showKeyboardShortcutFeedback('General Assistant Mode');
            }
        }
        // Ctrl/Cmd + / = Show keyboard shortcuts help
        else if ((e.ctrlKey || e.metaKey) && e.key === '/') {
            e.preventDefault();
            showKeyboardShortcuts();
        }
    });
}

function showKeyboardShortcutFeedback(mode) {
    // Create temporary feedback notification
    const feedback = document.createElement('div');
    feedback.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 9999;
        background: #4CAF50; color: white; padding: 12px 16px;
        border-radius: 6px; font-size: 14px; font-weight: 500;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transform: translateX(100%); transition: transform 0.3s ease;
    `;
    feedback.textContent = `Switched to ${mode}`;
    document.body.appendChild(feedback);
    
    setTimeout(() => feedback.style.transform = 'translateX(0)', 100);
    setTimeout(() => {
        feedback.style.transform = 'translateX(100%)';
        setTimeout(() => document.body.removeChild(feedback), 300);
    }, 2000);
}

function showKeyboardShortcuts() {
    // Create keyboard shortcuts modal
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 10000;
        background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center;
    `;
    
    const content = document.createElement('div');
    content.style.cssText = `
        background: white; padding: 24px; border-radius: 12px; max-width: 400px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    `;
    
    content.innerHTML = `
        <h3 style="margin: 0 0 16px 0; color: #333;">⌨️ Keyboard Shortcuts</h3>
        <div style="line-height: 1.6; color: #555;">
            <div><strong>Ctrl/Cmd + 1</strong> - Document Assistant Mode</div>
            <div><strong>Ctrl/Cmd + 2</strong> - General Assistant Mode</div>
            <div><strong>Ctrl/Cmd + /</strong> - Show this help</div>
            <div style="margin-top: 12px; font-size: 13px; color: #888;">
                Click anywhere outside to close
            </div>
        </div>
    `;
    
    modal.appendChild(content);
    document.body.appendChild(modal);
    
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    });
}

// Mode confirmation dialog functionality
let pendingModeSwitch = null;

function showModeConfirmation(targetMode) {
    const confirmDialog = document.querySelector('[data-testid*="mode_confirm_dialog"]');
    if (confirmDialog) {
        confirmDialog.style.display = 'block';
        pendingModeSwitch = targetMode;
    }
}

// Update description based on selected mode
function setupModeDescriptionHandler() {
    const updateModeDescription = () => {
        const selectors = ['.mode-selector', '.chat-mode-selector'];
        const radioButtons = [];
        
        selectors.forEach(selector => {
            const buttons = document.querySelectorAll(`${selector} input[type="radio"]`);
            radioButtons.push(...buttons);
        });
        const docDesc = document.querySelector('.doc-mode-desc');
        const genDesc = document.querySelector('.general-mode-desc');
        
        radioButtons.forEach(radio => {
            radio.addEventListener('change', function() {
                // Hide any open help sections when switching modes
                const helpSections = document.querySelectorAll('[id$="-help"]');
                helpSections.forEach(section => section.style.display = 'none');
                
                if (this.value.includes('RAG Mode')) {
                    docDesc.style.display = 'block';
                    genDesc.style.display = 'none';
                    updateContextualSuggestions('document');
                    updateModeButtonColors('document');
                    if (typeof toggleModeControls === 'function') {
                        toggleModeControls('document');
                    }
                } else if (this.value.includes('General LLM')) {
                    docDesc.style.display = 'none';
                    genDesc.style.display = 'block';
                    updateContextualSuggestions('general');
                    updateModeButtonColors('general');
                    if (typeof toggleModeControls === 'function') {
                        toggleModeControls('general');
                    }
                }
            });
        });
        
        // Set initial state
        const checkedRadio = document.querySelector('.mode-selector input[type="radio"]:checked');
        if (checkedRadio) {
            if (checkedRadio.value.includes('Document Assistant')) {
                docDesc.style.display = 'block';
                genDesc.style.display = 'none';
                updateContextualSuggestions('document');
                updateModeButtonColors('document');
                if (typeof toggleModeControls === 'function') {
                    toggleModeControls('document');
                }
            } else {
                docDesc.style.display = 'none';
                genDesc.style.display = 'block';
                updateContextualSuggestions('general');
                updateModeButtonColors('general');
                if (typeof toggleModeControls === 'function') {
                    toggleModeControls('general');
                }
            }
        }
        
        // Initialize button colors on page load
        initializeModeButtonColors();
        
        // Ensure button colors are applied after DOM is fully rendered
        setTimeout(() => {
            initializeModeButtonColors();
            ensureButtonColorsPersist();
        }, 100);
        
        // Continuous monitoring to ensure colors persist
        setInterval(() => {
            ensureButtonColorsPersist();
        }, 500);
    };
    
    // Add tooltips to radio button labels
    const addTooltips = () => {
        const labels = document.querySelectorAll('.mode-selector label');
        labels.forEach(label => {
            const input = label.querySelector('input');
            if (input && !label.querySelector('.tooltip')) {
                const tooltip = document.createElement('div');
                tooltip.className = 'tooltip';
                
                if (input.value.includes('Document Assistant')) {
                    tooltip.textContent = 'Search your documents for specific information and analysis';
                } else if (input.value.includes('General LLM')) {
                    tooltip.textContent = 'Quick answers using AI knowledge - no document search';
                }
                
                label.appendChild(tooltip);
            }
        });
    };
    
    // Call immediately and after delays to ensure DOM is ready
    updateModeDescription();
    addTooltips();
    setTimeout(() => {
        updateModeDescription();
        addTooltips();
    }, 100);
    setTimeout(() => {
        updateModeDescription();
        addTooltips();
    }, 500); // Additional delay for Gradio initialization
}

// Handle confirmation dialog buttons
function setupConfirmationDialogHandlers() {
    document.addEventListener('click', function(e) {
        if (e.target.id === 'confirm-mode-switch' && pendingModeSwitch) {
            // Complete the mode switch
            toggleModeControls(pendingModeSwitch);
            updateModeButtonColors(pendingModeSwitch);
            const confirmDialog = document.querySelector('[data-testid*="mode_confirm_dialog"]');
            if (confirmDialog) confirmDialog.style.display = 'none';
            pendingModeSwitch = null;
        } else if (e.target.id === 'cancel-mode-switch') {
            // Cancel the mode switch - revert radio button
            const confirmDialog = document.querySelector('[data-testid*="mode_confirm_dialog"]');
            if (confirmDialog) confirmDialog.style.display = 'none';
            pendingModeSwitch = null;
        }
    });
}

// Initialize mode selector functionality when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Mode selector module initialized');
    
    setupModeDescriptionHandler();
    initializeKeyboardShortcuts();
    setupConfirmationDialogHandlers();
    
    // Initialize button colors
    initializeModeButtonColors();
});