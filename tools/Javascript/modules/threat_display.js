/**
 * Threat Display JavaScript Module
 *
 * Handles expand/collapse functionality for Active Threats cards in the MITRE ATT&CK panel.
 * Extracted from display_utility.py lines 684-697 to fix dynamic JavaScript execution issues in Gradio.
 *
 * Author: Claude Code
 * Date: 2025-10-12
 * Issue: Show Attack Chain button was not responding due to inline JavaScript in Gradio HTML components
 */

/**
 * Expand a threat card to show full attack chain and mitigations
 * @param {number} threatIdx - The index of the threat card to expand
 */
function expandThreat(threatIdx) {
    console.log('expandThreat called for index:', threatIdx);

    // Collapse all other threats first
    document.querySelectorAll('.threat-card-expanded').forEach(el => {
        el.style.display = 'none';
        console.log('Collapsed expanded card:', el.id);
    });
    document.querySelectorAll('.threat-card-collapsed').forEach(el => {
        el.style.display = 'block';
        console.log('Showed collapsed card:', el.id);
    });

    // Expand the selected threat
    const collapsedCard = document.getElementById('threat-collapsed-' + threatIdx);
    const expandedCard = document.getElementById('threat-expanded-' + threatIdx);

    if (collapsedCard && expandedCard) {
        collapsedCard.style.display = 'none';
        expandedCard.style.display = 'block';
        console.log('Expanded threat card:', threatIdx);

        // Smooth scroll to the expanded card
        expandedCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
        console.error('Threat card elements not found:', {
            collapsedCard: collapsedCard,
            expandedCard: expandedCard,
            threatIdx: threatIdx
        });
    }
}

/**
 * Collapse an expanded threat card to show summary view
 * @param {number} threatIdx - The index of the threat card to collapse
 */
function collapseThreat(threatIdx) {
    console.log('collapseThreat called for index:', threatIdx);

    const expandedCard = document.getElementById('threat-expanded-' + threatIdx);
    const collapsedCard = document.getElementById('threat-collapsed-' + threatIdx);

    if (expandedCard && collapsedCard) {
        expandedCard.style.display = 'none';
        collapsedCard.style.display = 'block';
        console.log('Collapsed threat card:', threatIdx);

        // Smooth scroll to the collapsed card
        collapsedCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
        console.error('Threat card elements not found:', {
            expandedCard: expandedCard,
            collapsedCard: collapsedCard,
            threatIdx: threatIdx
        });
    }
}

/**
 * Initialize threat display functionality
 * This function is called when the DOM is ready or when content is dynamically loaded
 */
function initializeThreatDisplay() {
    console.log('Initializing threat display functionality');

    // Find all threat cards
    const collapsedCards = document.querySelectorAll('[id^="threat-collapsed-"]');
    const expandedCards = document.querySelectorAll('[id^="threat-expanded-"]');

    console.log('Found collapsed cards:', collapsedCards.length);
    console.log('Found expanded cards:', expandedCards.length);

    // Ensure collapsed cards are visible, expanded cards are hidden
    collapsedCards.forEach(card => {
        card.style.display = 'block';
    });
    expandedCards.forEach(card => {
        card.style.display = 'none';
    });

    console.log('Threat display initialized');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        console.log('DOM Content Loaded - Initializing threat display');
        initializeThreatDisplay();

        // Re-initialize after delays to handle dynamically loaded content
        setTimeout(() => {
            initializeThreatDisplay();
        }, 500);
        setTimeout(() => {
            initializeThreatDisplay();
        }, 1000);
        setTimeout(() => {
            initializeThreatDisplay();
        }, 2000);
    });
} else {
    // DOM already loaded
    console.log('DOM already loaded - Initializing threat display immediately');
    initializeThreatDisplay();

    // Re-initialize after delays to handle dynamically loaded content
    setTimeout(() => {
        initializeThreatDisplay();
    }, 500);
    setTimeout(() => {
        initializeThreatDisplay();
    }, 1000);
}

// Also reinitialize whenever the threat display is updated
// This handles cases where Gradio updates the HTML dynamically
const threatDisplayObserver = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        // Check if threat cards were added/modified
        if (mutation.addedNodes.length > 0) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1) { // Element node
                    if (node.id && (node.id.startsWith('threat-collapsed-') || node.id.startsWith('threat-expanded-'))) {
                        console.log('Threat card added/modified, reinitializing:', node.id);
                        setTimeout(() => initializeThreatDisplay(), 100);
                    }
                }
            });
        }
    });
});

// Start observing the document for threat card changes
if (document.body) {
    threatDisplayObserver.observe(document.body, {
        childList: true,
        subtree: true
    });
} else {
    setTimeout(() => {
        if (document.body) {
            threatDisplayObserver.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
    }, 1000);
}

console.log('Threat display module loaded');
