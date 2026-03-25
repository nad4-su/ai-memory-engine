/**
 * Profile Logic
 * Displays user interests, patterns, and decision style
 */

document.addEventListener('DOMContentLoaded', async () => {
    await loadProfile();
    
    // Setup trigger button
    const triggerBtn = document.getElementById('trigger-profiling');
    if (triggerBtn) {
        triggerBtn.addEventListener('click', async () => {
            setLoading(triggerBtn, true);
            try {
                await api.triggerProfiling();
                showToast('Profiling triggered successfully', 'success');
                setTimeout(() => loadProfile(), 2000);
            } catch (error) {
                handleError(error, 'Trigger Profiling');
            } finally {
                triggerBtn.innerHTML = '🔄 Run Analysis';
                triggerBtn.disabled = false;
            }
        });
    }
});

/**
 * Load profile data
 */
async function loadProfile() {
    try {
        await Promise.all([
            loadInterests(),
            loadBehaviorPatterns(),
            loadDecisionStyle(),
        ]);
    } catch (error) {
        handleError(error, 'Profile');
    }
}

/**
 * Load interests
 */
async function loadInterests() {
    try {
        const interests = await api.getInterests(20);
        const container = document.getElementById('interests-list');
        
        if (!interests || interests.length === 0) {
            container.innerHTML = `
                <p style="text-align: center; color: var(--text-secondary); padding: 2rem;">
                    No interests detected yet. The system will learn from your interactions over time.
                </p>
            `;
            return;
        }
        
        container.innerHTML = interests.map(interest => `
            <div class="card">
                <div class="flex-between mb-2">
                    <h3 style="font-size: 1.125rem; font-weight: 600;">${interest.name}</h3>
                    <span class="card-badge badge-info">
                        ${getTrendIcon(interest.trend)} ${Math.round(interest.strength * 100)}%
                    </span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${interest.strength * 100}%"></div>
                </div>
                ${interest.keywords ? `
                    <div style="margin-top: 0.75rem;">
                        ${interest.keywords.map(kw => `<span class="tag">${kw}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load interests:', error);
        document.getElementById('interests-list').innerHTML = `
            <div class="alert alert-warning">Failed to load interests.</div>
        `;
    }
}

/**
 * Load behavior patterns
 */
async function loadBehaviorPatterns() {
    try {
        const patterns = await api.getBehaviorPatterns();
        const container = document.getElementById('patterns-container');
        
        if (!patterns) {
            container.innerHTML = `
                <p style="color: var(--text-secondary);">No patterns detected yet.</p>
            `;
            return;
        }
        
        // Activity heatmap
        if (patterns.activity_by_hour) {
            const heatmap = createActivityHeatmap(patterns.activity_by_hour);
            document.getElementById('activity-heatmap').innerHTML = heatmap;
        }
        
        // Peak hours
        if (patterns.peak_hours) {
            document.getElementById('peak-hours').textContent = 
                patterns.peak_hours.map(h => `${h}:00`).join(', ');
        }
        
        // Preferred topics
        if (patterns.preferred_topics) {
            document.getElementById('preferred-topics').innerHTML = 
                patterns.preferred_topics.map(t => `<span class="tag">${t}</span>`).join('');
        }
        
    } catch (error) {
        console.error('Failed to load patterns:', error);
        document.getElementById('patterns-container').innerHTML = `
            <p style="color: var(--text-secondary);">Unable to load patterns.</p>
        `;
    }
}

/**
 * Create activity heatmap
 */
function createActivityHeatmap(activityData) {
    const hours = Array.from({ length: 24 }, (_, i) => i);
    const maxActivity = Math.max(...Object.values(activityData));
    
    return `
        <div style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 0.25rem;">
            ${hours.map(hour => {
                const activity = activityData[hour] || 0;
                const intensity = maxActivity > 0 ? activity / maxActivity : 0;
                const bgColor = `rgba(59, 130, 246, ${0.2 + intensity * 0.8})`;
                
                return `
                    <div style="
                        background: ${bgColor};
                        padding: 0.5rem;
                        border-radius: 4px;
                        text-align: center;
                        font-size: 0.75rem;
                    " title="${hour}:00 - ${activity} activities">
                        ${hour}
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

/**
 * Load decision style
 */
async function loadDecisionStyle() {
    try {
        const style = await api.getDecisionStyle();
        const container = document.getElementById('decision-style');
        
        if (!style) {
            container.innerHTML = `
                <p style="color: var(--text-secondary);">Not enough data to determine decision style.</p>
            `;
            return;
        }
        
        const styles = {
            analytical: {
                icon: '📊',
                title: 'Analytical',
                description: 'You prefer data-driven decisions and thorough analysis.',
            },
            intuitive: {
                icon: '💡',
                title: 'Intuitive',
                description: 'You trust your gut feeling and experience.',
            },
            balanced: {
                icon: '⚖️',
                title: 'Balanced',
                description: 'You combine logic and intuition in decision-making.',
            },
            collaborative: {
                icon: '🤝',
                title: 'Collaborative',
                description: 'You value input from others before deciding.',
            },
        };
        
        const styleInfo = styles[style.type] || styles.balanced;
        
        container.innerHTML = `
            <div class="card">
                <div style="text-align: center; padding: 1rem;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">${styleInfo.icon}</div>
                    <h3 style="font-size: 1.5rem; margin-bottom: 0.5rem;">${styleInfo.title}</h3>
                    <p style="color: var(--text-secondary);">${styleInfo.description}</p>
                    ${style.confidence ? `
                        <div style="margin-top: 1rem;">
                            <span class="card-badge badge-info">
                                ${Math.round(style.confidence * 100)}% confidence
                            </span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
        
    } catch (error) {
        console.error('Failed to load decision style:', error);
        document.getElementById('decision-style').innerHTML = `
            <p style="color: var(--text-secondary);">Unable to determine decision style.</p>
        `;
    }
}

/**
 * Get trend icon
 */
function getTrendIcon(trend) {
    if (trend > 0.1) return '↑';
    if (trend < -0.1) return '↓';
    return '→';
}
