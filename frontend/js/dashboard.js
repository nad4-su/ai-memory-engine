/**
 * Dashboard Logic
 * Displays system status, today's suggestions, and top interests
 */

let refreshInterval;

document.addEventListener('DOMContentLoaded', async () => {
    await loadDashboard();
    
    // Auto-refresh every 30 seconds
    refreshInterval = setInterval(loadDashboard, 30000);
    
    // Setup manual refresh button
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
            setLoading(refreshBtn, true);
            await loadDashboard();
            refreshBtn.innerHTML = '🔄 Refresh';
            refreshBtn.disabled = false;
        });
    }
});

/**
 * Load all dashboard data
 */
async function loadDashboard() {
    try {
        await Promise.all([
            loadSystemStatus(),
            loadTodaySuggestions(),
            loadTopInterests(),
        ]);
    } catch (error) {
        handleError(error, 'Dashboard');
    }
}

/**
 * Load system status
 */
async function loadSystemStatus() {
    try {
        const status = await api.getSystemStatus();
        
        document.getElementById('llm-status').textContent = status.llm_connected ? 'Connected' : 'Disconnected';
        document.getElementById('llm-status').className = status.llm_connected ? 'badge-success' : 'badge-danger';
        
        document.getElementById('memory-count').textContent = formatNumber(status.total_memories || 0);
        
        const lastAnalysis = status.last_profiling ? formatDate(status.last_profiling) : 'Never';
        document.getElementById('last-analysis').textContent = lastAnalysis;
        
    } catch (error) {
        console.error('Failed to load system status:', error);
        document.getElementById('llm-status').textContent = 'Unknown';
        document.getElementById('llm-status').className = 'badge-warning';
    }
}

/**
 * Load today's suggestions
 */
async function loadTodaySuggestions() {
    try {
        const suggestions = await api.getSuggestions(10);
        const container = document.getElementById('suggestions-container');
        
        if (!suggestions || suggestions.length === 0) {
            container.innerHTML = `
                <div class="card">
                    <p style="text-align: center; color: var(--text-secondary);">
                        No suggestions available yet. Run the Advisor to generate suggestions.
                    </p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = suggestions.map(s => createSuggestionCard(s)).join('');
        
        // Attach feedback listeners
        attachFeedbackListeners();
        
    } catch (error) {
        console.error('Failed to load suggestions:', error);
        document.getElementById('suggestions-container').innerHTML = `
            <div class="alert alert-warning">
                Failed to load suggestions. Please check if the Advisor service is running.
            </div>
        `;
    }
}

/**
 * Create suggestion card HTML
 */
function createSuggestionCard(suggestion) {
    const categoryColors = {
        learning: 'info',
        productivity: 'success',
        wellness: 'warning',
        relationship: 'danger',
    };
    
    const badgeClass = categoryColors[suggestion.category] || 'info';
    
    return `
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">${suggestion.title}</h3>
                <span class="card-badge badge-${badgeClass}">${suggestion.category}</span>
            </div>
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                ${suggestion.content}
            </p>
            ${suggestion.reasoning ? `
                <details style="margin-bottom: 1rem;">
                    <summary style="cursor: pointer; color: var(--accent);">Why this suggestion?</summary>
                    <p style="margin-top: 0.5rem; color: var(--text-secondary); font-size: 0.875rem;">
                        ${suggestion.reasoning}
                    </p>
                </details>
            ` : ''}
            <div class="flex-between">
                <span style="font-size: 0.875rem; color: var(--text-secondary);">
                    ${formatDate(suggestion.created_at)}
                </span>
                <div class="flex-gap">
                    <button class="btn-icon btn-success feedback-btn" data-id="${suggestion.id}" data-feedback="positive" title="Helpful">
                        👍
                    </button>
                    <button class="btn-icon btn-danger feedback-btn" data-id="${suggestion.id}" data-feedback="negative" title="Not helpful">
                        👎
                    </button>
                </div>
            </div>
        </div>
    `;
}

/**
 * Attach feedback button listeners
 */
function attachFeedbackListeners() {
    document.querySelectorAll('.feedback-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const id = e.currentTarget.dataset.id;
            const feedback = e.currentTarget.dataset.feedback;
            
            try {
                await api.submitFeedback(id, feedback);
                showToast('Thank you for your feedback!', 'success');
                
                // Disable both buttons for this suggestion
                const card = e.currentTarget.closest('.card');
                card.querySelectorAll('.feedback-btn').forEach(b => b.disabled = true);
                
            } catch (error) {
                handleError(error, 'Submit Feedback');
            }
        });
    });
}

/**
 * Load top interests
 */
async function loadTopInterests() {
    try {
        const interests = await api.getInterests(5);
        const container = document.getElementById('interests-container');
        
        if (!interests || interests.length === 0) {
            container.innerHTML = `
                <p style="text-align: center; color: var(--text-secondary);">
                    No interests detected yet. The system will learn from your interactions.
                </p>
            `;
            return;
        }
        
        container.innerHTML = interests.map(interest => `
            <div style="margin-bottom: 1rem;">
                <div class="flex-between mb-1">
                    <span style="font-weight: 600;">${interest.name}</span>
                    <span style="font-size: 0.875rem; color: var(--text-secondary);">
                        ${getTrendIcon(interest.trend)} ${Math.round(interest.strength * 100)}%
                    </span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${interest.strength * 100}%"></div>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load interests:', error);
        document.getElementById('interests-container').innerHTML = `
            <p style="color: var(--text-secondary);">Unable to load interests.</p>
        `;
    }
}

/**
 * Get trend icon
 */
function getTrendIcon(trend) {
    if (trend > 0) return '↑';
    if (trend < 0) return '↓';
    return '→';
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});
