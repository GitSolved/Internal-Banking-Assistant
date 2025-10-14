// ================================================================
// FORCE DARK THEME - JavaScript Runtime Override
// ================================================================
// 
// This script forces a dark theme by directly manipulating the DOM
// and CSS styles at runtime. This is a backup to the CSS approach
// and ensures that even dynamically generated content gets the dark theme.
// ================================================================

(function() {
    'use strict';
    
    // Function to force dark theme on all elements
    function forceDarkTheme() {
        // Force body and html to be black
        document.documentElement.style.setProperty('background', '#000000', 'important');
        document.documentElement.style.setProperty('background-color', '#000000', 'important');
        document.body.style.setProperty('background', '#000000', 'important');
        document.body.style.setProperty('background-color', '#000000', 'important');
        
        // Force all divs to be black
        const allDivs = document.querySelectorAll('div');
        allDivs.forEach(div => {
            div.style.setProperty('background-color', '#000000', 'important');
            div.style.setProperty('color', '#ffffff', 'important');
        });
        
        // Force Gradio containers to be black
        const gradioContainers = document.querySelectorAll('.gradio-container, .gradio-app, .gradio-interface');
        gradioContainers.forEach(container => {
            container.style.setProperty('background', '#000000', 'important');
            container.style.setProperty('background-color', '#000000', 'important');
            container.style.setProperty('color', '#ffffff', 'important');
        });
        
        // Force panels to be dark grey
        const panels = document.querySelectorAll('.gradio-panel, .gradio-box, .gradio-form, .gradio-padded, .gradio-group');
        panels.forEach(panel => {
            panel.style.setProperty('background', '#1a1a1a', 'important');
            panel.style.setProperty('background-color', '#1a1a1a', 'important');
            panel.style.setProperty('color', '#ffffff', 'important');
            panel.style.setProperty('border', '1px solid #333333', 'important');
        });
        
        // Force header to be black
        const headers = document.querySelectorAll('.header-container, .header-logo, .header-title, .header-subtitle');
        headers.forEach(header => {
            header.style.setProperty('background', '#000000', 'important');
            header.style.setProperty('background-color', '#000000', 'important');
            header.style.setProperty('color', '#ffffff', 'important');
        });
        
        // Force all text to be white
        const textElements = document.querySelectorAll('p, div, span, h1, h2, h3, h4, h5, h6, label, li, td, th, tr');
        textElements.forEach(element => {
            element.style.setProperty('color', '#ffffff', 'important');
        });
        
        // Force input fields to have dark backgrounds
        const inputs = document.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.style.setProperty('background-color', '#232526', 'important');
            input.style.setProperty('color', '#ffffff', 'important');
            input.style.setProperty('border', '1px solid #333333', 'important');
        });
        
        // Force buttons to have white text
        const buttons = document.querySelectorAll('button');
        buttons.forEach(button => {
            button.style.setProperty('color', '#ffffff', 'important');
        });
        
        // Force links to be blue
        const links = document.querySelectorAll('a');
        links.forEach(link => {
            link.style.setProperty('color', '#0077BE', 'important');
        });
    }
    
    // Function to observe DOM changes and apply dark theme to new elements
    function observeAndForceDark() {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            // Apply dark theme to new elements
                            node.style.setProperty('background-color', '#000000', 'important');
                            node.style.setProperty('color', '#ffffff', 'important');
                            
                            // If it's a panel, make it dark grey
                            if (node.classList && (
                                node.classList.contains('gradio-panel') ||
                                node.classList.contains('gradio-box') ||
                                node.classList.contains('gradio-form') ||
                                node.classList.contains('gradio-padded') ||
                                node.classList.contains('gradio-group')
                            )) {
                                node.style.setProperty('background-color', '#1a1a1a', 'important');
                                node.style.setProperty('border', '1px solid #333333', 'important');
                            }
                        }
                    });
                }
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
    // Apply dark theme immediately
    forceDarkTheme();
    
    // Apply dark theme after DOM is fully loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', forceDarkTheme);
    } else {
        forceDarkTheme();
    }
    
    // Apply dark theme after window loads (for dynamically loaded content)
    window.addEventListener('load', forceDarkTheme);
    
    // Start observing for new elements
    observeAndForceDark();
    
    // Apply dark theme every 2 seconds as a safety net
    setInterval(forceDarkTheme, 2000);
    
    console.log('Force Dark Theme JavaScript loaded and active');
})();
