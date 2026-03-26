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
                const result = await api.request('/profiler/analyze', { method: 'POST' });
                showToast('분석 완료! 프로필을 새로고침합니다.', 'success');
                setTimeout(() => loadProfile(), 1000);
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
                    아직 관심사가 감지되지 않았습니다. 대화가 쌓이면 자동으로 학습합니다.
                </p>
            `;
            return;
        }
        
        container.innerHTML = interests.map(interest => {
            const name = interest.topic || interest.name || 'Unknown';
            const strength = interest.intensity || interest.strength || 0;
            const trend = interest.trend || 'stable';
            const category = interest.category || '';
            const mentions = interest.mention_count || 0;
            
            return `
                <div class="card">
                    <div class="flex-between mb-2">
                        <h3 style="font-size: 1.125rem; font-weight: 600;">${name}</h3>
                        <span class="card-badge badge-info">
                            ${getTrendIcon(trend)} ${Math.round(strength * 100)}%
                        </span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${strength * 100}%"></div>
                    </div>
                    <div style="margin-top: 0.75rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
                        ${category ? `<span class="tag">${category}</span>` : ''}
                        ${mentions > 0 ? `<span class="tag">언급 ${mentions}회</span>` : ''}
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Failed to load interests:', error);
        document.getElementById('interests-list').innerHTML = `
            <div class="alert alert-warning">관심사 로드에 실패했습니다.</div>
        `;
    }
}

/**
 * Load behavior patterns
 */
async function loadBehaviorPatterns() {
    try {
        // profiler/status에서 last_analysis 결과를 가져옴
        const status = await api.request('/profiler/status');
        const container = document.getElementById('patterns-container');
        const lastAnalysis = status?.last_analysis;
        
        if (!lastAnalysis || !lastAnalysis.result || !lastAnalysis.result.patterns) {
            container.innerHTML = `
                <p style="color: var(--text-secondary);">아직 패턴이 감지되지 않았습니다. "Run Analysis"를 실행해보세요.</p>
            `;
            return;
        }
        
        const patterns = lastAnalysis.result.patterns;
        
        // Activity heatmap from active_hours
        const heatmapEl = document.getElementById('activity-heatmap');
        if (heatmapEl && patterns.active_hours) {
            const activityData = {};
            patterns.active_hours.forEach(h => { activityData[h] = (activityData[h] || 0) + 1; });
            heatmapEl.innerHTML = createActivityHeatmap(activityData);
        } else if (heatmapEl) {
            heatmapEl.innerHTML = '<p style="color: var(--text-secondary);">데이터 수집 중...</p>';
        }
        
        // Peak hours
        const peakEl = document.getElementById('peak-hours');
        if (peakEl && patterns.active_hours) {
            peakEl.textContent = patterns.active_hours.map(h => `${h}:00`).join(', ');
        } else if (peakEl) {
            peakEl.textContent = '-';
        }
        
        // Preferred topics
        const topicsEl = document.getElementById('preferred-topics');
        if (topicsEl && patterns.preferred_topics) {
            topicsEl.innerHTML = patterns.preferred_topics.map(t => `<span class="tag">${t}</span>`).join('');
        } else if (topicsEl) {
            topicsEl.textContent = '-';
        }
        
    } catch (error) {
        console.error('Failed to load patterns:', error);
        const container = document.getElementById('patterns-container');
        if (container) {
            container.innerHTML = `
                <p style="color: var(--text-secondary);">패턴 로드에 실패했습니다.</p>
            `;
        }
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
        const status = await api.request('/profiler/status');
        const container = document.getElementById('decision-style');
        const lastAnalysis = status?.last_analysis;
        
        const decisionStyle = lastAnalysis?.result?.patterns?.decision_style;
        
        if (!decisionStyle || decisionStyle === 'unknown') {
            container.innerHTML = `
                <p style="color: var(--text-secondary);">데이터가 충분하지 않아 의사결정 스타일을 판단할 수 없습니다.</p>
            `;
            return;
        }
        
        const styles = {
            '빠른결정': { icon: '⚡', title: '빠른 결정형', description: '빠르게 판단하고 즉시 실행하는 스타일입니다.' },
            '숙고형': { icon: '🤔', title: '숙고형', description: '신중하게 분석하고 검토한 후 결정하는 스타일입니다.' },
            '위임형': { icon: '🤝', title: '위임형', description: '다른 사람의 의견을 구하고 협력적으로 결정하는 스타일입니다.' },
            'analytical': { icon: '📊', title: 'Analytical', description: '데이터 기반으로 철저히 분석 후 결정합니다.' },
            'intuitive': { icon: '💡', title: 'Intuitive', description: '경험과 직감을 신뢰하여 결정합니다.' },
            'balanced': { icon: '⚖️', title: 'Balanced', description: '논리와 직감을 균형 있게 활용합니다.' },
        };
        
        const styleInfo = styles[decisionStyle] || { icon: '🧠', title: decisionStyle, description: '' };
        
        container.innerHTML = `
            <div class="card">
                <div style="text-align: center; padding: 1rem;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">${styleInfo.icon}</div>
                    <h3 style="font-size: 1.5rem; margin-bottom: 0.5rem;">${styleInfo.title}</h3>
                    <p style="color: var(--text-secondary);">${styleInfo.description}</p>
                </div>
            </div>
        `;
        
    } catch (error) {
        console.error('Failed to load decision style:', error);
        const el = document.getElementById('decision-style');
        if (el) {
            el.innerHTML = `<p style="color: var(--text-secondary);">의사결정 스타일을 판단할 수 없습니다.</p>`;
        }
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
