/**
 * Search Logic
 * Semantic search across memories
 */

let searchTimeout;

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const sourceFilter = document.getElementById('source-filter');
    
    // Search on button click
    searchBtn?.addEventListener('click', performSearch);
    
    // Search on Enter key
    searchInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    // Debounced search on input
    searchInput?.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(performSearch, 500);
    });
    
    // Filter change
    sourceFilter?.addEventListener('change', performSearch);
});

/**
 * Perform search
 */
async function performSearch() {
    const query = document.getElementById('search-input')?.value.trim();
    const source = document.getElementById('source-filter')?.value;
    const resultsContainer = document.getElementById('results-container');
    const searchBtn = document.getElementById('search-btn');
    
    if (!query) {
        resultsContainer.innerHTML = `
            <div class="card">
                <p style="text-align: center; color: var(--text-secondary);">
                    Enter a search query to find relevant memories.
                </p>
            </div>
        `;
        return;
    }
    
    // Show loading
    resultsContainer.innerHTML = `
        <div class="card" style="text-align: center;">
            <span class="loading"></span>
            <p style="margin-top: 1rem;">Searching...</p>
        </div>
    `;
    
    try {
        const filters = {};
        if (source && source !== 'all') {
            filters.source = source;
        }
        
        const results = await api.searchMemories(query, filters);
        
        displayResults(results);
        
    } catch (error) {
        handleError(error, 'Search');
        resultsContainer.innerHTML = `
            <div class="alert alert-danger">
                Search failed: ${error.message}
            </div>
        `;
    }
}

/**
 * Display search results
 */
function displayResults(results) {
    const container = document.getElementById('results-container');
    
    if (!results || results.length === 0) {
        container.innerHTML = `
            <div class="card">
                <p style="text-align: center; color: var(--text-secondary);">
                    No results found. Try a different query.
                </p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = results.map(result => createResultCard(result)).join('');
}

/**
 * Create result card HTML
 */
function createResultCard(result) {
    const sourceIcons = {
        conversation: '💬',
        document: '📄',
        bookmark: '🔖',
    };
    
    const icon = sourceIcons[result.source] || '📌';
    const relevance = Math.round(result.score * 100);
    
    return `
        <div class="card">
            <div class="card-header">
                <div>
                    <span style="font-size: 1.5rem; margin-right: 0.5rem;">${icon}</span>
                    <span class="card-title">${result.title || 'Untitled'}</span>
                </div>
                <span class="card-badge badge-info">${relevance}% match</span>
            </div>
            
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                ${truncate(result.content, 200)}
            </p>
            
            <div class="flex-between">
                <div>
                    ${result.tags ? result.tags.map(tag => `<span class="tag">${tag}</span>`).join('') : ''}
                </div>
                <span style="font-size: 0.875rem; color: var(--text-secondary);">
                    ${formatDate(result.created_at)}
                </span>
            </div>
            
            ${result.metadata ? `
                <details style="margin-top: 1rem;">
                    <summary style="cursor: pointer; color: var(--accent); font-size: 0.875rem;">
                        View metadata
                    </summary>
                    <pre style="background: var(--bg-primary); padding: 0.75rem; border-radius: var(--radius); margin-top: 0.5rem; font-size: 0.875rem; overflow-x: auto;">
${JSON.stringify(result.metadata, null, 2)}
                    </pre>
                </details>
            ` : ''}
        </div>
    `;
}

/**
 * Clear search
 */
function clearSearch() {
    document.getElementById('search-input').value = '';
    document.getElementById('source-filter').value = 'all';
    document.getElementById('results-container').innerHTML = `
        <div class="card">
            <p style="text-align: center; color: var(--text-secondary);">
                Enter a search query to find relevant memories.
            </p>
        </div>
    `;
}
