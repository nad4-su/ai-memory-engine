/**
 * History Logic
 * Displays suggestion history and feedback
 */

document.addEventListener('DOMContentLoaded', async () => {
    await loadHistory();
    
    // Setup filter
    const feedbackFilter = document.getElementById('feedback-filter');
    if (feedbackFilter) {
        feedbackFilter.addEventListener('change', loadHistory);
    }
});

/**
 * Load suggestion history
 */
async function loadHistory() {
    const feedbackFilter = document.getElementById('feedback-filter')?.value;
    const container = document.getElementById('history-table-body');
    
    // Show loading
    container.innerHTML = `
        <tr>
            <td colspan="5" style="text-align: center; padding: 2rem;">
                <span class="loading"></span>
                <p style="margin-top: 1rem;">Loading history...</p>
            </td>
        </tr>
    `;
    
    try {
        const filters = {};
        if (feedbackFilter && feedbackFilter !== 'all') {
            filters.feedback = feedbackFilter;
        }
        
        const history = await api.getSuggestionHistory(filters);
        
        displayHistory(history);
        
    } catch (error) {
        handleError(error, 'History');
        container.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 2rem; color: var(--danger);">
                    Failed to load history: ${error.message}
                </td>
            </tr>
        `;
    }
}

/**
 * Display history
 */
function displayHistory(history) {
    const container = document.getElementById('history-table-body');
    
    if (!history || history.length === 0) {
        container.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                    No history found.
                </td>
            </tr>
        `;
        return;
    }
    
    container.innerHTML = history.map(item => {
        const feedbackBadge = getFeedbackBadge(item.feedback);
        const categoryBadge = getCategoryBadge(item.category);
        
        return `
            <tr>
                <td>${formatDate(item.created_at)}</td>
                <td>
                    <strong>${item.title}</strong>
                    <br>
                    <small style="color: var(--text-secondary);">
                        ${truncate(item.content, 80)}
                    </small>
                </td>
                <td>${categoryBadge}</td>
                <td>${feedbackBadge}</td>
                <td>
                    <button class="btn-outline btn-icon" onclick="viewDetails('${item.id}')" title="View details">
                        👁️
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * Get feedback badge HTML
 */
function getFeedbackBadge(feedback) {
    if (!feedback) {
        return '<span class="card-badge badge-info">Pending</span>';
    }
    
    const badges = {
        positive: '<span class="card-badge badge-success">👍 Positive</span>',
        negative: '<span class="card-badge badge-danger">👎 Negative</span>',
    };
    
    return badges[feedback] || '<span class="card-badge badge-info">Unknown</span>';
}

/**
 * Get category badge HTML
 */
function getCategoryBadge(category) {
    const badges = {
        learning: '<span class="card-badge badge-info">Learning</span>',
        productivity: '<span class="card-badge badge-success">Productivity</span>',
        wellness: '<span class="card-badge badge-warning">Wellness</span>',
        relationship: '<span class="card-badge badge-danger">Relationship</span>',
    };
    
    return badges[category] || `<span class="card-badge badge-info">${category}</span>`;
}

/**
 * View suggestion details
 */
async function viewDetails(id) {
    try {
        const suggestion = await api.getSuggestionById(id);
        
        // Create modal
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            padding: 2rem;
        `;
        
        modal.innerHTML = `
            <div class="card" style="max-width: 600px; width: 100%; max-height: 80vh; overflow-y: auto;">
                <div class="card-header">
                    <h3 class="card-title">${suggestion.title}</h3>
                    <button onclick="this.closest('.card').parentElement.remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: var(--text-secondary);">
                        ✕
                    </button>
                </div>
                
                <div style="margin-bottom: 1rem;">
                    ${getCategoryBadge(suggestion.category)}
                    ${getFeedbackBadge(suggestion.feedback)}
                </div>
                
                <p style="margin-bottom: 1rem; line-height: 1.8;">
                    ${suggestion.content}
                </p>
                
                ${suggestion.reasoning ? `
                    <div class="alert alert-info">
                        <strong>Reasoning:</strong><br>
                        ${suggestion.reasoning}
                    </div>
                ` : ''}
                
                <div style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid var(--border); color: var(--text-secondary); font-size: 0.875rem;">
                    <strong>Created:</strong> ${formatDate(suggestion.created_at)}
                    ${suggestion.feedback_at ? `<br><strong>Feedback:</strong> ${formatDate(suggestion.feedback_at)}` : ''}
                </div>
            </div>
        `;
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
        
        document.body.appendChild(modal);
        
    } catch (error) {
        handleError(error, 'View Details');
    }
}
