/**
 * API Client for AI Memory Engine
 * Handles all API requests to backend services
 */

const API_BASE = '/api/v1';

class APIClient {
    constructor() {
        this.baseUrl = API_BASE;
    }

    /**
     * Generic fetch wrapper with error handling
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    // ==================== Health & Status ====================
    
    async getHealth() {
        return this.request('/health');
    }

    async getSystemStatus() {
        return this.request('/status');
    }

    // ==================== Ingest ====================
    
    async ingestConversation(data) {
        return this.request('/ingest/conversation', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async ingestDocument(data) {
        return this.request('/ingest/document', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async ingestBookmark(data) {
        return this.request('/ingest/bookmark', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async triggerDataCollection() {
        return this.request('/ingest/trigger', {
            method: 'POST',
        });
    }

    // ==================== Search ====================
    
    async searchMemories(query, filters = {}) {
        const params = new URLSearchParams({
            query,
            ...filters,
        });
        return this.request(`/search?${params}`);
    }

    async getMemoryById(id) {
        return this.request(`/memories/${id}`);
    }

    // ==================== Profile ====================
    
    async getProfile() {
        return this.request('/profile');
    }

    async getInterests(limit = 10) {
        return this.request(`/profile/interests?limit=${limit}`);
    }

    async getBehaviorPatterns() {
        return this.request('/profile/patterns');
    }

    async getDecisionStyle() {
        return this.request('/profile/decision-style');
    }

    async triggerProfiling() {
        return this.request('/profile/trigger', {
            method: 'POST',
        });
    }

    // ==================== Advisor ====================
    
    async getSuggestions(limit = 10) {
        return this.request(`/suggestions?limit=${limit}`);
    }

    async getSuggestionById(id) {
        return this.request(`/suggestions/${id}`);
    }

    async submitFeedback(suggestionId, feedback) {
        return this.request(`/suggestions/${suggestionId}/feedback`, {
            method: 'POST',
            body: JSON.stringify({ feedback }),
        });
    }

    async getSuggestionHistory(filters = {}) {
        const params = new URLSearchParams(filters);
        return this.request(`/suggestions/history?${params}`);
    }

    async triggerAdvisor() {
        return this.request('/suggestions/trigger', {
            method: 'POST',
        });
    }

    // ==================== Settings ====================
    
    async getConfig() {
        return this.request('/config');
    }

    async getScheduleStatus() {
        return this.request('/schedule/status');
    }
}

// Create global instance
const api = new APIClient();

// ==================== Utility Functions ====================

/**
 * Format date to readable string
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

/**
 * Format number with thousand separator
 */
function formatNumber(num) {
    return num.toLocaleString('en-US');
}

/**
 * Truncate text with ellipsis
 */
function truncate(text, maxLength = 100) {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength).trim() + '...';
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type}`;
    toast.textContent = message;
    toast.style.position = 'fixed';
    toast.style.top = '20px';
    toast.style.right = '20px';
    toast.style.zIndex = '9999';
    toast.style.minWidth = '300px';
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Show loading state
 */
function setLoading(element, isLoading) {
    if (isLoading) {
        element.disabled = true;
        element.innerHTML = '<span class="loading"></span> Loading...';
    } else {
        element.disabled = false;
    }
}

/**
 * Handle API errors gracefully
 */
function handleError(error, context = '') {
    console.error(`Error in ${context}:`, error);
    showToast(error.message || 'An error occurred', 'danger');
}
