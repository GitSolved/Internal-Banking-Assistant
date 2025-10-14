/**
 * Collapsible Sections JavaScript Module
 * 
 * Handles document organization and collapsible functionality for the Internal Assistant UI.
 * Extracted from ui.py lines 680-702 and 1173-2119 during Phase 0.7 refactoring.
 */

// Enhanced Document Organization JavaScript Functions with Event Delegation
function toggleSection(header) {
    const section = header.parentElement;
    const icon = header.querySelector('.collapsible-icon');
    const content = section.querySelector('.collapsible-content');
    
    if (!section || !icon || !content) {
        console.warn('toggleSection: required elements not found', {section, icon, content, header});
        return;
    }
    
    console.log('Toggling section:', section, 'Current collapsed state:', section.classList.contains('collapsed'));
    
    // Prevent double-clicking during animation
    if (section.classList.contains('expanding') || section.classList.contains('collapsing')) {
        return;
    }
    
    const isCollapsing = !section.classList.contains('collapsed');
    
    if (isCollapsing) {
        // Collapsing the section
        section.classList.add('collapsing');
        section.classList.remove('expanding');
        
        // Update icon immediately
        icon.textContent = '▶';
        
        // Start collapse animation
        setTimeout(() => {
            section.classList.add('collapsed');
            section.classList.remove('collapsing');
        }, 400); // Match CSS transition duration
        
    } else {
        // Expanding the section  
        section.classList.add('expanding');
        section.classList.remove('collapsing');
        section.classList.remove('collapsed');
        
        // Update icon immediately
        icon.textContent = '▼';
        
        // End expand animation
        setTimeout(() => {
            section.classList.remove('expanding');
        }, 400); // Match CSS transition duration
    }
    
    // Enhanced visual feedback with pulse effect
    icon.style.color = '#00A3FF';
    icon.style.textShadow = '0 0 8px rgba(0, 163, 255, 0.8)';
    
    setTimeout(() => {
        icon.style.color = '';
        icon.style.textShadow = '';
    }, 400);
    
    console.log('Section toggle completed:', section.classList.contains('collapsed') ? 'collapsed' : 'expanded');
}

// Global event delegation for collapsible headers
function setupEventDelegation() {
    // Remove any existing event listeners to prevent duplicates
    if (window.collapsibleHandler) {
        document.removeEventListener('click', window.collapsibleHandler);
    }
    
    // DISABLED: Commenting out second event handler for dropdown debugging  
    window.collapsibleHandler = function(e) {
        // ALL EVENT HANDLING DISABLED FOR DROPDOWN TESTING
        console.log('Second event handler called but DISABLED for dropdown debugging');
        return; // Do nothing
        
        /*
        // Debug logging for dropdown issues
        if (e.target.tagName === 'SELECT' || e.target.closest('select') || e.target.closest('[role="listbox"]') || e.target.closest('[role="combobox"]')) {
            console.log('Dropdown click detected (handler 2), allowing default behavior');
            return;
        }
        
        // Skip if clicking on ANY form elements or Gradio components
        if (e.target.closest('input, select, button, textarea, [role="button"], [role="listbox"], [role="combobox"], [class*="dropdown"], [class*="gradio"], [class*="svelte"]')) {
            console.log('Form element click detected (handler 2), allowing default behavior');
            return;
        }
        
        // Check if clicked element is a collapsible header or inside one
        const header = e.target.closest('.collapsible-header');
        if (header) {
            console.log('Collapsible header click detected (handler 2), preventing default');
            e.preventDefault();
            e.stopPropagation();
            toggleSection(header);
        }
        */
    };
    
    document.addEventListener('click', window.collapsibleHandler);
}

// Initialize collapsible sections
function initializeCollapsibleSections() {
    const sections = document.querySelectorAll('.collapsible-section');
    console.log('Initializing collapsible sections, found:', sections.length);
    
    sections.forEach((section, index) => {
        const icon = section.querySelector('.collapsible-icon');
        const header = section.querySelector('.collapsible-header');
        const content = section.querySelector('.collapsible-content');
        
        console.log(`Section ${index}:`, {
            section: section.classList.toString(),
            hasIcon: !!icon,
            hasHeader: !!header,
            hasContent: !!content
        });
        
        if (icon && header && content) {
            // Ensure proper initial state
            if (section.classList.contains('collapsed')) {
                icon.textContent = '▶';
                // Let CSS handle the transform via .collapsed .collapsible-icon
            } else {
                icon.textContent = '▼';
                // Let CSS handle the transform (default state)
            }
            
            // Remove any inline styles that might interfere with CSS
            icon.style.transform = '';
            icon.style.transition = '';
            icon.style.color = '';
            icon.style.textShadow = '';
            
            // Ensure header is clickable
            header.style.cursor = 'pointer';
            
            // Add aria attributes for accessibility
            const isCollapsed = section.classList.contains('collapsed');
            header.setAttribute('role', 'button');
            header.setAttribute('aria-expanded', !isCollapsed);
            header.setAttribute('aria-controls', `collapsible-content-${index}`);
            content.setAttribute('id', `collapsible-content-${index}`);
            
            console.log(`Section ${index} initialized:`, isCollapsed ? 'collapsed' : 'expanded');
        } else {
            console.warn(`Section ${index} missing required elements`);
        }
    });
    
    console.log('All collapsible sections initialized successfully');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        console.log('DOM Content Loaded - Setting up collapsible sections');
        
        setupEventDelegation();
        initializeCollapsibleSections();
        
        // Re-initialize after delays to handle dynamically loaded content
        setTimeout(() => {
            initializeCollapsibleSections();
        }, 500);
        setTimeout(() => {
            initializeCollapsibleSections();
        }, 1000);
        setTimeout(() => {
            initializeCollapsibleSections();
        }, 2000);
    });
} else {
    // DOM already loaded
    console.log('DOM already loaded - Setting up collapsible sections immediately');
    
    setupEventDelegation();
    initializeCollapsibleSections();
    
    // Re-initialize after delays
    setTimeout(() => {
        initializeCollapsibleSections();
    }, 500);
    setTimeout(() => {
        initializeCollapsibleSections();
    }, 1000);
}