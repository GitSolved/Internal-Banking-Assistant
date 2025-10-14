/**
 * Resize Handlers JavaScript Module
 * 
 * Handles UI resize functionality for chat, internal, external sections.
 * Extracted from ui.py during Phase 0.7 refactoring - part of the large JavaScript block.
 */

// Chat Resize Functionality
function initializeChatResize() {
    const resizeHandle = document.getElementById('chat-resize-handle');
    const chatContainer = document.querySelector('.chat-container');
    
    if (!resizeHandle || !chatContainer) {
        console.log('Chat resize elements not found, retrying...');
        return false;
    }
    
    let isResizing = false;
    let startY = 0;
    let startHeight = 0;
    
    resizeHandle.addEventListener('mousedown', (e) => {
        isResizing = true;
        startY = e.clientY;
        startHeight = parseInt(window.getComputedStyle(chatContainer).height, 10);
        chatContainer.classList.add('resizing');
        
        // Prevent text selection during resize
        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'nw-resize';
        
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        
        const deltaY = e.clientY - startY;
        const newHeight = startHeight + deltaY;
        
        // Apply min/max height constraints
        const minHeight = 300;
        const maxHeight = window.innerHeight - 100;
        const constrainedHeight = Math.max(minHeight, Math.min(maxHeight, newHeight));
        
        chatContainer.style.height = constrainedHeight + 'px';
        
        // Also update the chatbot height to maintain proper scrolling
        const chatbot = chatContainer.querySelector('.main-chatbot, #chatbot');
        if (chatbot) {
            const headerHeight = 60; // Approximate header height
            const inputHeight = 120; // Increased for control buttons at bottom
            const availableHeight = constrainedHeight - headerHeight - inputHeight;
            chatbot.style.maxHeight = Math.max(400, availableHeight) + 'px';
            chatbot.style.height = 'auto'; // Allow flex growth
        }
    });
    
    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            chatContainer.classList.remove('resizing');
            document.body.style.userSelect = '';
            document.body.style.cursor = '';
            
            // Mark as manually resized to prevent automatic adjustment
            chatContainer.dataset.manuallyResized = 'true';
            
            // Save the new height to localStorage for persistence
            const currentHeight = chatContainer.style.height;
            if (currentHeight) {
                localStorage.setItem('chatContainerHeight', currentHeight);
            }
        }
    });
    
    // Restore saved height on load
    const savedHeight = localStorage.getItem('chatContainerHeight');
    if (savedHeight) {
        chatContainer.style.height = savedHeight;
        
        // Also update chatbot height
        const chatbot = chatContainer.querySelector('.main-chatbot, #chatbot');
        if (chatbot) {
            const headerHeight = 60;
            const inputHeight = 120; // Increased for control buttons at bottom
            const containerHeight = parseInt(savedHeight, 10);
            const availableHeight = containerHeight - headerHeight - inputHeight;
            chatbot.style.maxHeight = Math.max(400, availableHeight) + 'px';
            chatbot.style.height = 'auto'; // Allow flex growth
        }
    }
    
    console.log('Chat resize functionality initialized');
    return true;
}

// Internal Information Resize Functionality
function initializeInternalResize() {
    const resizeHandle = document.getElementById('internal-resize-handle');
    const container = document.querySelector('.file-management-section');
    
    if (!resizeHandle || !container) {
        console.log('Internal resize elements not found, retrying...');
        return false;
    }
    
    let isResizing = false;
    let startY = 0;
    let startHeight = 0;
    
    resizeHandle.addEventListener('mousedown', (e) => {
        isResizing = true;
        startY = e.clientY;
        startHeight = parseInt(window.getComputedStyle(container).height, 10);
        container.classList.add('resizing');
        
        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'nw-resize';
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        
        const deltaY = e.clientY - startY;
        const newHeight = startHeight + deltaY;
        const minHeight = 500; // Same as chat
        const maxHeight = window.innerHeight - 100;
        const constrainedHeight = Math.max(minHeight, Math.min(maxHeight, newHeight));
        
        container.style.height = constrainedHeight + 'px';
    });
    
    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            container.classList.remove('resizing');
            document.body.style.userSelect = '';
            document.body.style.cursor = '';
            
            const currentHeight = container.style.height;
            if (currentHeight) {
                localStorage.setItem('internalContainerHeight', currentHeight);
            }
        }
    });
    
    // Restore saved height
    const savedHeight = localStorage.getItem('internalContainerHeight');
    if (savedHeight) {
        container.style.height = savedHeight;
    }
    
    console.log('Internal resize functionality initialized');
    return true;
}

// External Information Resize Functionality
function initializeExternalResize() {
    const resizeHandle = document.getElementById('external-resize-handle');
    const container = document.querySelector('.external-info-section');
    
    if (!resizeHandle || !container) {
        console.log('External resize elements not found, retrying...');
        return false;
    }
    
    let isResizing = false;
    let startY = 0;
    let startHeight = 0;
    
    resizeHandle.addEventListener('mousedown', (e) => {
        isResizing = true;
        startY = e.clientY;
        startHeight = parseInt(window.getComputedStyle(container).height, 10);
        container.classList.add('resizing');
        
        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'nw-resize';
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        
        const deltaY = e.clientY - startY;
        const newHeight = startHeight + deltaY;
        const minHeight = 500; // Same as chat
        const maxHeight = window.innerHeight - 100;
        const constrainedHeight = Math.max(minHeight, Math.min(maxHeight, newHeight));
        
        container.style.height = constrainedHeight + 'px';
    });
    
    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            container.classList.remove('resizing');
            document.body.style.userSelect = '';
            document.body.style.cursor = '';
            
            const currentHeight = container.style.height;
            if (currentHeight) {
                localStorage.setItem('externalContainerHeight', currentHeight);
            }
        }
    });
    
    // Restore saved height
    const savedHeight = localStorage.getItem('externalContainerHeight');
    if (savedHeight) {
        container.style.height = savedHeight;
    }
    
    console.log('External resize functionality initialized');
    return true;
}

// Forum Resize Functionality
function initializeForumResize() {
    const container = document.querySelector('.forum-directory-section');
    if (!container) {
        console.log('Forum container not found');
        return false;
    }
    
    const handle = container.querySelector('.forum-resize-handle');
    if (!handle) {
        console.log('Forum resize handle not found');
        return false;
    }
    
    let isResizing = false;
    let startY = 0;
    let startHeight = 0;
    
    handle.addEventListener('mousedown', function(e) {
        e.preventDefault();
        isResizing = true;
        startY = e.clientY;
        startHeight = parseInt(window.getComputedStyle(container).height, 10);
        
        container.classList.add('resizing');
        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'row-resize';
    });
    
    document.addEventListener('mousemove', function(e) {
        if (!isResizing) return;
        
        const deltaY = e.clientY - startY;
        let newHeight = startHeight + deltaY;
        
        // Enforce min and max height
        newHeight = Math.max(200, Math.min(newHeight, window.innerHeight - 200));
        
        container.style.height = newHeight + 'px';
    });
    
    document.addEventListener('mouseup', function(e) {
        if (isResizing) {
            isResizing = false;
            container.classList.remove('resizing');
            document.body.style.userSelect = '';
            document.body.style.cursor = '';
            
            const currentHeight = container.style.height;
            if (currentHeight) {
                localStorage.setItem('forumContainerHeight', currentHeight);
            }
        }
    });
    
    // Restore saved height
    const savedHeight = localStorage.getItem('forumContainerHeight');
    if (savedHeight) {
        container.style.height = savedHeight;
    }
    
    console.log('Forum resize functionality initialized');
    return true;
}

// CVE Resize Functionality
function initializeCveResize() {
    const container = document.querySelector('.cve-tracking-section');
    if (!container) {
        console.log('CVE container not found');
        return false;
    }
    
    const handle = container.querySelector('.cve-resize-handle');
    if (!handle) {
        console.log('CVE resize handle not found');
        return false;
    }
    
    let isResizing = false;
    let startY = 0;
    let startHeight = 0;
    
    handle.addEventListener('mousedown', function(e) {
        e.preventDefault();
        isResizing = true;
        startY = e.clientY;
        startHeight = parseInt(window.getComputedStyle(container).height, 10);
        
        container.classList.add('resizing');
        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'row-resize';
    });
    
    document.addEventListener('mousemove', function(e) {
        if (!isResizing) return;
        
        const deltaY = e.clientY - startY;
        let newHeight = startHeight + deltaY;
        
        // Enforce min and max height
        newHeight = Math.max(200, Math.min(newHeight, window.innerHeight - 200));
        
        container.style.height = newHeight + 'px';
    });
    
    document.addEventListener('mouseup', function(e) {
        if (isResizing) {
            isResizing = false;
            container.classList.remove('resizing');
            document.body.style.userSelect = '';
            document.body.style.cursor = '';
            
            const currentHeight = container.style.height;
            if (currentHeight) {
                localStorage.setItem('cveContainerHeight', currentHeight);
            }
        }
    });
    
    // Restore saved height
    const savedHeight = localStorage.getItem('cveContainerHeight');
    if (savedHeight) {
        container.style.height = savedHeight;
    }
    
    console.log('CVE resize functionality initialized');
    return true;
}

// MITRE Resize Functionality
function initializeMitreResize() {
    const container = document.querySelector('.mitre-attack-section');
    if (!container) {
        console.log('MITRE container not found');
        return false;
    }
    
    const handle = container.querySelector('.mitre-resize-handle');
    if (!handle) {
        console.log('MITRE resize handle not found');
        return false;
    }
    
    let isResizing = false;
    let startY = 0;
    let startHeight = 0;
    
    handle.addEventListener('mousedown', function(e) {
        e.preventDefault();
        isResizing = true;
        startY = e.clientY;
        startHeight = parseInt(window.getComputedStyle(container).height, 10);
        
        container.classList.add('resizing');
        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'row-resize';
    });
    
    document.addEventListener('mousemove', function(e) {
        if (!isResizing) return;
        
        const deltaY = e.clientY - startY;
        let newHeight = startHeight + deltaY;
        
        // Enforce min and max height
        newHeight = Math.max(200, Math.min(newHeight, window.innerHeight - 200));
        
        container.style.height = newHeight + 'px';
    });
    
    document.addEventListener('mouseup', function(e) {
        if (isResizing) {
            isResizing = false;
            container.classList.remove('resizing');
            document.body.style.userSelect = '';
            document.body.style.cursor = '';
            
            const currentHeight = container.style.height;
            if (currentHeight) {
                localStorage.setItem('mitreContainerHeight', currentHeight);
            }
        }
    });
    
    // Restore saved height
    const savedHeight = localStorage.getItem('mitreContainerHeight');
    if (savedHeight) {
        container.style.height = savedHeight;
    }
    
    console.log('MITRE resize functionality initialized');
    return true;
}

// Make chat container responsive to content size
function initializeResponsiveChatContainer() {
    function adjustChatContainerHeight() {
        const chatContainer = document.querySelector('.chat-container');
        const chatMessages = document.querySelector('.chat-messages');
        const chatInterface = document.querySelector('.chat-interface');
        
        // Skip adjustment if container was manually resized
        if (chatContainer && chatContainer.dataset.manuallyResized === 'true') {
            return;
        }
        
        if (chatContainer && chatMessages) {
            // Calculate content height
            const messagesHeight = chatMessages.scrollHeight;
            const controlsHeight = 120; // Approximate height for input controls
            const padding = 32; // Container padding
            const totalContentHeight = messagesHeight + controlsHeight + padding;
            
            // Set container height based on content, respecting min/max limits
            const minHeight = 500;  // IMPROVED: Better minimum
            const maxHeight = window.innerHeight - 200;  // IMPROVED: Use more viewport space
            const newHeight = Math.max(minHeight, Math.min(totalContentHeight, maxHeight));
            
            chatContainer.style.height = newHeight + 'px';
        }
    }
    
    // Adjust on load and when content changes
    adjustChatContainerHeight();
    
    // Use MutationObserver to watch for chat content changes
    const chatMessages = document.querySelector('.chat-messages');
    if (chatMessages) {
        const observer = new MutationObserver(adjustChatContainerHeight);
        observer.observe(chatMessages, { 
            childList: true, 
            subtree: true, 
            characterData: true 
        });
    }
    
    // Adjust on window resize
    window.addEventListener('resize', adjustChatContainerHeight);
}

// Initialize all resize handlers when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Resize handlers module initialized');
    
    // Initialize all resize functions with delays to ensure DOM is ready
    setTimeout(() => {
        initializeChatResize();
        initializeInternalResize();
        initializeExternalResize();
        initializeForumResize();
        initializeCveResize();
        initializeMitreResize();
        initializeResponsiveChatContainer();
    }, 500);
    
    setTimeout(() => {
        initializeChatResize();
        initializeInternalResize();
        initializeExternalResize();
        initializeForumResize();
        initializeCveResize();
        initializeMitreResize();
        initializeResponsiveChatContainer();
    }, 1000);
    
    setTimeout(() => {
        initializeChatResize();
        initializeInternalResize();
        initializeExternalResize();
        initializeForumResize();
        initializeCveResize();
        initializeMitreResize();
        initializeResponsiveChatContainer();
    }, 2000);
});