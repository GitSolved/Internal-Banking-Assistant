/**
 * Document Management JavaScript Module
 * 
 * Handles document filtering, selection, and management functionality for the Internal Assistant UI.
 * Extracted from ui.py lines 687-1134 during Phase 0.7 refactoring.
 */

// Global variable for active filters
let activeFilters = ['all'];

// Toggle folder visibility
function toggleFolder(folderItem) {
    const content = folderItem.nextElementSibling;
    const icon = folderItem.querySelector('.collapsible-icon');
    
    if (content.style.display === 'none' || content.style.display === '') {
        content.style.display = 'block';
        icon.textContent = '▼';
    } else {
        content.style.display = 'none';
        icon.textContent = '▶';
    }
}

// Toggle filter buttons
function toggleFilter(filterBtn) {
    const filterType = filterBtn.getAttribute('data-filter');
    
    // Handle 'all' filter specially
    if (filterType === 'all') {
        // Clear all other filters and activate 'all'
        document.querySelectorAll('.filter-tag').forEach(btn => btn.classList.remove('active'));
        filterBtn.classList.add('active');
        activeFilters = ['all'];
    } else {
        // Remove 'all' filter if it's active
        const allBtn = document.querySelector('.filter-tag[data-filter="all"]');
        if (allBtn) allBtn.classList.remove('active');
        
        // Toggle this filter
        if (filterBtn.classList.contains('active')) {
            filterBtn.classList.remove('active');
            activeFilters = activeFilters.filter(f => f !== filterType);
        } else {
            filterBtn.classList.add('active');
            activeFilters.push(filterType);
        }
        
        // If no filters are active, activate 'all'
        if (activeFilters.length === 0) {
            if (allBtn) allBtn.classList.add('active');
            activeFilters = ['all'];
        }
    }
    
    filterDocuments();
}

// Filter documents based on search query and active filters
function filterDocuments() {
    const searchQuery = document.getElementById('doc-search')?.value.toLowerCase() || '';
    const documentItems = document.querySelectorAll('.document-item:not(.folder-item)');
    const folderItems = document.querySelectorAll('.folder-item');
    
    let visibleCounts = {};
    
    documentItems.forEach(item => {
        const filename = item.getAttribute('data-filename') || '';
        const filetype = item.getAttribute('data-type') || '';
        const itemText = item.textContent.toLowerCase();
        
        // Check if item matches search query
        const matchesSearch = searchQuery === '' || 
            filename.toLowerCase().includes(searchQuery) || 
            itemText.includes(searchQuery);
        
        // Check if item matches active filters
        let matchesFilter = false;
        if (activeFilters.includes('all')) {
            matchesFilter = true;
        } else {
            matchesFilter = activeFilters.some(filter => {
                switch (filter) {
                    case 'pdf': return filetype === 'pdf';
                    case 'excel': return filetype === 'excel';
                    case 'word': return filetype === 'word';
                    case 'recent': return item.classList.contains('recent-doc-item');
                    case 'analyzed': return item.textContent.includes('analyzed');
                    case 'pending': return item.textContent.includes('pending');
                    default: return false;
                }
            });
        }
        
        // Show/hide item based on filters
        const shouldShow = matchesSearch && matchesFilter;
        item.style.display = shouldShow ? 'flex' : 'none';
        
        // Count visible items per folder
        if (shouldShow) {
            const folder = item.closest('.folder-content')?.previousElementSibling;
            if (folder && folder.classList.contains('folder-item')) {
                const folderName = folder.getAttribute('data-folder');
                visibleCounts[folderName] = (visibleCounts[folderName] || 0) + 1;
            }
        }
    });
    
    // Update folder counts and visibility
    folderItems.forEach(folder => {
        const folderName = folder.getAttribute('data-folder');
        const count = visibleCounts[folderName] || 0;
        const folderContent = folder.nextElementSibling;
        
        // Update count in folder title
        const titleSpan = folder.querySelector('span:nth-child(2)');
        if (titleSpan) {
            const baseName = folderName;
            titleSpan.textContent = `${baseName} (${count})`;
        }
        
        // Hide folder if no visible items
        folder.style.display = count > 0 ? 'flex' : 'none';
        if (count === 0 && folderContent) {
            folderContent.style.display = 'none';
            const icon = folder.querySelector('.collapsible-icon');
            if (icon) icon.textContent = '▶';
        }
    });
}

// Select a document item
function selectDocument(docItem) {
    // Remove previous selection
    document.querySelectorAll('.document-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    // Add selection to clicked item
    docItem.classList.add('selected');
    
    // Store selected document info
    const filename = docItem.getAttribute('data-filename');
    console.log('Selected document:', filename);
}

// Analyze a document
function analyzeDocument(filename) {
    console.log('Analyzing document:', filename);
    // Add your analyze logic here
    alert(`Starting analysis of: ${filename}`);
}

// Share a document
function shareDocument(filename) {
    console.log('Sharing document:', filename);
    // Add your share logic here
    alert(`Sharing: ${filename}`);
}

// Expand the Document Library section
function expandDocumentLibrary() {
    // Expand the Document Library section
    const docLibSection = document.querySelector('.collapsible-section');
    if (docLibSection && docLibSection.classList.contains('collapsed')) {
        const header = docLibSection.querySelector('.collapsible-header');
        if (header && typeof toggleSection === 'function') toggleSection(header);
    }
    
    // Clear filters to show all documents
    document.querySelectorAll('.filter-tag').forEach(btn => btn.classList.remove('active'));
    const allBtn = document.querySelector('.filter-tag[data-filter="all"]');
    if (allBtn) allBtn.classList.add('active');
    activeFilters = ['all'];
    filterDocuments();
}

// Start new document analysis
function startNewAnalysis() {
    console.log('Starting new analysis...');
    
    // Get selected documents or all documents
    const selectedDocs = document.querySelectorAll('.document-item.selected');
    if (selectedDocs.length === 0) {
        alert('Please select documents to analyze, or the system will analyze all documents.');
    } else {
        const filenames = Array.from(selectedDocs).map(doc => doc.getAttribute('data-filename')).join(', ');
        alert(`Starting analysis for: ${filenames}`);
    }
    
    // Show processing queue and expand it
    const queueSection = document.querySelector('.collapsible-section:has(#processing-queue-content)');
    if (queueSection && queueSection.classList.contains('collapsed')) {
        const header = queueSection.querySelector('.collapsible-header');
        if (header && typeof toggleSection === 'function') toggleSection(header);
    }
}

// Bulk process documents
function bulkProcess() {
    console.log('Starting bulk processing...');
    
    const totalDocs = document.querySelectorAll('.document-item:not(.folder-item)').length;
    if (totalDocs === 0) {
        alert('No documents available for bulk processing. Please upload documents first.');
        return;
    }
    
    const confirmation = confirm(`Start bulk processing for ${totalDocs} documents? This may take some time.`);
    if (confirmation) {
        alert(`Bulk processing started for ${totalDocs} documents. Check the Processing Queue for status updates.`);
        
        // Show processing queue
        const queueSection = document.querySelector('.collapsible-section:has(#processing-queue-content)');
        if (queueSection && queueSection.classList.contains('collapsed')) {
            const header = queueSection.querySelector('.collapsible-header');
            if (header && typeof toggleSection === 'function') toggleSection(header);
        }
    }
}

// Export documents
function exportDocuments() {
    console.log('Exporting documents...');
    
    const selectedDocs = document.querySelectorAll('.document-item.selected');
    const exportCount = selectedDocs.length > 0 ? selectedDocs.length : document.querySelectorAll('.document-item:not(.folder-item)').length;
    
    if (exportCount === 0) {
        alert('No documents available for export. Please upload documents first.');
        return;
    }
    
    const formats = ['PDF Report', 'Excel Spreadsheet', 'JSON Data', 'CSV File'];
    const selectedFormat = prompt(`Choose export format for ${exportCount} documents:\n1. PDF Report\n2. Excel Spreadsheet\n3. JSON Data\n4. CSV File\n\nEnter number (1-4):`);
    
    if (selectedFormat && selectedFormat >= 1 && selectedFormat <= 4) {
        const formatName = formats[selectedFormat - 1];
        alert(`Preparing ${formatName} export for ${exportCount} documents. Download will start shortly.`);
    }
}

// Update document library content
function updateLibraryContent() {
    const libraryContainer = document.getElementById('document-library-content');
    if (libraryContainer) {
        console.log('Library content update requested');
    }
}

// Pagination functionality
function setupPaginationHandler() {
    window.changePage = function(page, filterType, searchQuery) {
        console.log('Changing page to:', page, 'Filter:', filterType, 'Search:', searchQuery);
        
        // Find filter buttons by their text content
        const buttons = Array.from(document.querySelectorAll('button'));
        let targetButton = null;
        
        switch(filterType) {
            case 'all':
                targetButton = buttons.find(btn => btn.textContent.trim() === 'All');
                break;
            case 'pdf':
                targetButton = buttons.find(btn => btn.textContent.trim() === 'PDF');
                break;
            case 'excel':
                targetButton = buttons.find(btn => btn.textContent.trim() === 'Excel');
                break;
            case 'word':
                targetButton = buttons.find(btn => btn.textContent.trim() === 'Word');
                break;
            case 'recent':
                targetButton = buttons.find(btn => btn.textContent.trim() === 'Recent');
                break;
            case 'analyzed':
                targetButton = buttons.find(btn => btn.textContent.trim() === 'Analyzed');
                break;
        }
        
        // Update search input if needed
        const searchInput = document.querySelector('input[placeholder*="Search documents"]');
        if (searchInput && searchQuery !== searchInput.value) {
            searchInput.value = searchQuery;
            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
        
        // Trigger the filter button click
        if (targetButton) {
            targetButton.click();
        } else {
            console.warn('Could not find filter button for:', filterType);
        }
    };
}

// Initialize document management functionality when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Document management module initialized');
    
    // Setup pagination handler
    setupPaginationHandler();
    
    // Initialize filters
    filterDocuments();
});