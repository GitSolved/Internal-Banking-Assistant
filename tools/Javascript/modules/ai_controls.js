/**
 * AI Controls JavaScript Module
 * 
 * Handles AI control movement and document management debugging for the Internal Assistant UI.
 * Extracted from ui.py lines 1161-2107 during Phase 0.7 refactoring.
 */

// Move AI configuration controls to sidebar
function moveAIControlsToSidebar() {
    // Move AI mode selector
    const modeSelector = document.querySelector('.mode-selector');
    const aiModeTarget = document.getElementById('ai-mode-selector');
    if (modeSelector && aiModeTarget) {
        aiModeTarget.appendChild(modeSelector.parentElement);
    }
    
    // Move model selection
    const modelSelector = document.querySelector('.model-selector');
    const modelTarget = document.getElementById('model-selector');
    if (modelSelector && modelTarget) {
        modelTarget.appendChild(modelSelector.parentElement);
    }
    
    // Move writing style selector
    const writingStyleSelector = document.querySelector('.writing-style-selector');
    const writingStyleTarget = document.getElementById('writing-style-selector');
    if (writingStyleSelector && writingStyleTarget) {
        writingStyleTarget.appendChild(writingStyleSelector.parentElement);
    }
    
    // Move temperature control
    const temperatureControl = document.querySelector('.temperature-control');
    const temperatureTarget = document.getElementById('temperature-selector');
    if (temperatureControl && temperatureTarget) {
        temperatureTarget.appendChild(temperatureControl.parentElement);
    }
}

// Debug Document Management section visibility
function debugDocumentManagement() {
    const docSection = document.querySelector('.file-management-section');
    const uploadButton = document.getElementById('upload-files');
    const fileList = document.querySelector('.file-list-display');
    
    console.log('Document Management Debug:');
    console.log('- Section found:', !!docSection);
    console.log('- Upload button found:', !!uploadButton);
    console.log('- File list found:', !!fileList);
    
    if (docSection) {
        console.log('- Section visible:', window.getComputedStyle(docSection).display !== 'none');
        console.log('- Section height:', window.getComputedStyle(docSection).height);
        console.log('- Section position:', docSection.getBoundingClientRect());
        
        // Force visibility if hidden
        docSection.style.display = 'block';
        docSection.style.visibility = 'visible';
        docSection.style.opacity = '1';
    }
}

// Initialize AI controls functionality when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('AI controls module initialized');
    
    // Execute with delays to handle dynamically loaded content
    setTimeout(() => {
        moveAIControlsToSidebar();
        debugDocumentManagement();
    }, 500);
    
    setTimeout(() => {
        moveAIControlsToSidebar();
        debugDocumentManagement();
    }, 1000);
    
    setTimeout(() => {
        moveAIControlsToSidebar();
        debugDocumentManagement();
    }, 2000);
});