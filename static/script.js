/**
 * Medium Topic Generator - Frontend JavaScript
 * Handles form submission, WebSocket communication, and dynamic UI updates
 */

// DOM Elements
const elements = {
    form: document.getElementById('topicForm'),
    background: document.getElementById('background'),
    keywordsInput: document.getElementById('keywordsInput'),
    keywordsTags: document.getElementById('keywordsTags'),
    keywordsHidden: document.getElementById('keywords'),
    audience: document.getElementById('audience'),
    customAudience: document.getElementById('customAudience'),
    submitBtn: document.getElementById('submitBtn'),
    inputSection: document.getElementById('inputSection'),
    progressSection: document.getElementById('progressSection'),
    progressMessage: document.getElementById('progressMessage'),
    progressBar: document.getElementById('progressBar'),
    resultsSection: document.getElementById('resultsSection'),
    insightsContent: document.getElementById('insightsContent'),
    topicsGrid: document.getElementById('topicsGrid'),
    topicsMeta: document.getElementById('topicsMeta'),
    newSearchBtn: document.getElementById('newSearchBtn')
};

// State
let keywords = [];
let ws = null;
let currentTaskId = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initKeywordInput();
    initAudienceSelect();
    initForm();
    initNewSearchBtn();
    loadSavedPreferences();
});

// ============================================
// Keyword Tags Input
// ============================================

function initKeywordInput() {
    const container = elements.keywordsInput.parentElement;
    
    // Focus input when clicking container
    container.addEventListener('click', () => {
        elements.keywordsInput.focus();
    });
    
    // Handle keyboard input
    elements.keywordsInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            addKeyword(elements.keywordsInput.value);
        } else if (e.key === 'Backspace' && !elements.keywordsInput.value && keywords.length > 0) {
            removeKeyword(keywords.length - 1);
        }
    });
    
    // Handle blur - add any pending text
    elements.keywordsInput.addEventListener('blur', () => {
        if (elements.keywordsInput.value.trim()) {
            addKeyword(elements.keywordsInput.value);
        }
    });
}

function addKeyword(value) {
    const keyword = value.trim().toLowerCase();
    
    if (!keyword || keywords.includes(keyword) || keywords.length >= 10) {
        elements.keywordsInput.value = '';
        return;
    }
    
    keywords.push(keyword);
    updateKeywordsTags();
    elements.keywordsInput.value = '';
    updateHiddenKeywords();
}

function removeKeyword(index) {
    keywords.splice(index, 1);
    updateKeywordsTags();
    updateHiddenKeywords();
}

function updateKeywordsTags() {
    elements.keywordsTags.innerHTML = keywords.map((keyword, index) => `
        <span class="keyword-tag">
            ${escapeHtml(keyword)}
            <button type="button" class="remove-tag" onclick="removeKeyword(${index})">×</button>
        </span>
    `).join('');
}

function updateHiddenKeywords() {
    elements.keywordsHidden.value = keywords.join(',');
}

// ============================================
// Audience Select
// ============================================

function initAudienceSelect() {
    elements.audience.addEventListener('change', () => {
        if (elements.audience.value === 'custom') {
            elements.customAudience.classList.remove('hidden');
            elements.customAudience.focus();
        } else {
            elements.customAudience.classList.add('hidden');
            elements.customAudience.value = '';
        }
    });
}

// ============================================
// Form Submission
// ============================================

function initForm() {
    elements.form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Validate
        if (keywords.length === 0) {
            showToast('Please add at least one keyword', 'error');
            elements.keywordsInput.focus();
            return;
        }
        
        const background = elements.background.value.trim();
        if (background.length < 10) {
            showToast('Please provide more details about your background', 'error');
            elements.background.focus();
            return;
        }
        
        const audience = elements.audience.value === 'custom' 
            ? elements.customAudience.value.trim() 
            : elements.audience.value;
        
        // Save preferences
        savePreferences();
        
        // Start generation
        await startGeneration({
            background,
            keywords,
            target_audience: audience
        });
    });
}

async function startGeneration(data) {
    try {
        // Show progress section
        showSection('progress');
        resetProgress();
        
        // Submit request
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start generation');
        }
        
        const result = await response.json();
        currentTaskId = result.task_id;
        
        // Connect WebSocket for real-time updates
        connectWebSocket(currentTaskId);
        
        // Also poll as fallback
        startPolling(currentTaskId);
        
    } catch (error) {
        console.error('Error:', error);
        showToast(error.message, 'error');
        showSection('input');
    }
}

// ============================================
// WebSocket Connection
// ============================================

function connectWebSocket(taskId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${taskId}`;
    
    try {
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('WebSocket connected');
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        ws.onclose = () => {
            console.log('WebSocket closed');
        };
    } catch (error) {
        console.error('WebSocket connection failed:', error);
    }
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'progress':
            updateProgress(data.progress, data.message);
            break;
        case 'complete':
            if (data.status === 'success') {
                displayResults(data.result);
            } else {
                showToast(data.result?.error || 'Generation failed', 'error');
                showSection('input');
            }
            closeWebSocket();
            break;
        case 'error':
            showToast(data.message, 'error');
            showSection('input');
            closeWebSocket();
            break;
    }
}

function closeWebSocket() {
    if (ws) {
        ws.close();
        ws = null;
    }
}

// ============================================
// Polling Fallback
// ============================================

let pollingInterval = null;

function startPolling(taskId) {
    pollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/status/${taskId}`);
            if (!response.ok) return;
            
            const data = await response.json();
            
            if (data.status === 'pending') {
                updateProgress(data.progress, data.message);
            } else if (data.status === 'success') {
                stopPolling();
                displayResults(data.result);
            } else if (data.status === 'error') {
                stopPolling();
                showToast(data.message, 'error');
                showSection('input');
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 2000);
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

// ============================================
// Progress UI
// ============================================

function resetProgress() {
    elements.progressBar.style.width = '0%';
    elements.progressMessage.textContent = 'Starting analysis...';
    
    document.querySelectorAll('.progress-step').forEach(step => {
        step.classList.remove('active', 'completed');
    });
}

function updateProgress(progress, message) {
    elements.progressBar.style.width = `${progress}%`;
    elements.progressMessage.textContent = message;
    
    // Update step indicators
    const steps = ['search', 'research', 'analyze', 'generate', 'score'];
    const stepThresholds = [20, 40, 60, 80, 90];
    
    steps.forEach((step, index) => {
        const stepEl = document.querySelector(`[data-step="${step}"]`);
        if (stepEl) {
            if (progress >= stepThresholds[index]) {
                stepEl.classList.remove('active');
                stepEl.classList.add('completed');
            } else if (progress >= (stepThresholds[index - 1] || 0)) {
                stepEl.classList.add('active');
            }
        }
    });
}

// ============================================
// Results Display
// ============================================

function displayResults(result) {
    stopPolling();
    closeWebSocket();
    
    // Display trend insights
    displayInsights(result.trend_insights);
    
    // Display topics
    displayTopics(result.topics);
    
    // Update meta
    const metadata = result.metadata || {};
    elements.topicsMeta.textContent = `Analyzed ${metadata.web_results_count || 0} web results and ${metadata.arxiv_papers_count || 0} research papers`;
    
    // Show results section
    showSection('results');
    
    showToast('Topics generated successfully!', 'success');
}

function displayInsights(insights) {
    if (!insights) {
        elements.insightsContent.innerHTML = '<p class="text-muted">No insights available</p>';
        return;
    }
    
    const categories = [
        { key: 'hot_topics', label: '🔥 Hot Topics', color: '#ef4444' },
        { key: 'emerging_trends', label: '📈 Emerging Trends', color: '#22c55e' },
        { key: 'content_gaps', label: '💡 Content Gaps', color: '#f59e0b' },
        { key: 'research_frontiers', label: '🔬 Research Frontiers', color: '#8b5cf6' }
    ];
    
    elements.insightsContent.innerHTML = categories.map(cat => {
        const items = insights[cat.key] || [];
        if (items.length === 0) return '';
        
        return `
            <div class="insight-item" style="border-left-color: ${cat.color}">
                <div class="insight-label">${cat.label}</div>
                <div class="insight-tags">
                    ${items.slice(0, 4).map(item => `<span class="insight-tag">${escapeHtml(item)}</span>`).join('')}
                </div>
            </div>
        `;
    }).join('');
}

function displayTopics(topics) {
    if (!topics || topics.length === 0) {
        elements.topicsGrid.innerHTML = '<p class="text-muted">No topics generated</p>';
        return;
    }
    
    elements.topicsGrid.innerHTML = topics.map((scoredTopic, index) => {
        const topic = scoredTopic.topic || scoredTopic;
        const scores = scoredTopic.scores || {};
        const overall = scoredTopic.overall_score || 0;
        const rank = scoredTopic.rank || index + 1;
        const reasoning = scoredTopic.reasoning || '';
        const recommendations = scoredTopic.recommendations || [];
        
        const rankClass = rank === 1 ? 'gold' : rank === 2 ? 'silver' : rank === 3 ? 'bronze' : '';
        const scoreClass = getScoreClass(overall);
        const dashOffset = 157 - (157 * overall / 100);
        
        return `
            <article class="topic-card rank-${rank}" style="animation-delay: ${index * 0.1}s">
                <button class="copy-btn" onclick="copyTopic(this, ${index})" title="Copy topic">📋</button>
                
                <div class="topic-header">
                    <span class="topic-rank ${rankClass}">#${rank}</span>
                    <h3 class="topic-title">${escapeHtml(topic.title || 'Untitled')}</h3>
                </div>
                
                ${topic.hook ? `<p class="topic-hook">"${escapeHtml(topic.hook)}"</p>` : ''}
                
                <p class="topic-description">${escapeHtml(topic.description || '')}</p>
                
                <div class="topic-meta">
                    ${topic.article_type ? `<span class="topic-tag"><span class="topic-tag-icon">📝</span>${escapeHtml(topic.article_type)}</span>` : ''}
                    ${topic.estimated_read_time ? `<span class="topic-tag"><span class="topic-tag-icon">⏱️</span>${escapeHtml(topic.estimated_read_time)}</span>` : ''}
                    ${topic.target_audience ? `<span class="topic-tag"><span class="topic-tag-icon">👥</span>${escapeHtml(topic.target_audience)}</span>` : ''}
                </div>
                
                <div class="topic-scores">
                    <div class="overall-score">
                        <div class="score-circle">
                            <svg viewBox="0 0 56 56">
                                <circle class="score-bg" cx="28" cy="28" r="25"></circle>
                                <circle class="score-fill ${scoreClass}" cx="28" cy="28" r="25" style="stroke-dashoffset: ${dashOffset}"></circle>
                            </svg>
                            <span class="score-value">${Math.round(overall)}</span>
                        </div>
                        <span class="score-label">Overall Score</span>
                    </div>
                    
                    <div class="score-breakdown">
                        <div class="score-item">
                            <div class="score-item-value">${scores.trend_score || 0}</div>
                            <div class="score-item-label">📈 Trend</div>
                        </div>
                        <div class="score-item">
                            <div class="score-item-value">${scores.uniqueness_score || 0}</div>
                            <div class="score-item-label">✨ Unique</div>
                        </div>
                        <div class="score-item">
                            <div class="score-item-value">${scores.engagement_score || 0}</div>
                            <div class="score-item-label">💬 Engage</div>
                        </div>
                        <div class="score-item">
                            <div class="score-item-value">${scores.author_fit_score || 0}</div>
                            <div class="score-item-label">👤 Fit</div>
                        </div>
                        <div class="score-item">
                            <div class="score-item-value">${scores.research_depth_score || 0}</div>
                            <div class="score-item-label">📚 Research</div>
                        </div>
                    </div>
                </div>
                
                ${(topic.unique_angle || reasoning || recommendations.length) ? `
                <div class="topic-details">
                    <button class="details-toggle" onclick="toggleDetails(this)">
                        <span>Show more details</span>
                        <span class="toggle-icon">▼</span>
                    </button>
                    <div class="details-content">
                        ${topic.unique_angle ? `
                        <div class="detail-section">
                            <div class="detail-label">Unique Angle</div>
                            <div class="detail-content">${escapeHtml(topic.unique_angle)}</div>
                        </div>
                        ` : ''}
                        ${reasoning ? `
                        <div class="detail-section">
                            <div class="detail-label">Why This Topic</div>
                            <div class="detail-content">${escapeHtml(reasoning)}</div>
                        </div>
                        ` : ''}
                        ${recommendations.length ? `
                        <div class="detail-section">
                            <div class="detail-label">Recommendations</div>
                            <ul class="recommendations-list">
                                ${recommendations.map(rec => `<li>${escapeHtml(rec)}</li>`).join('')}
                            </ul>
                        </div>
                        ` : ''}
                    </div>
                </div>
                ` : ''}
            </article>
        `;
    }).join('');
}

function getScoreClass(score) {
    if (score >= 80) return 'excellent';
    if (score >= 60) return 'good';
    if (score >= 40) return 'average';
    return 'below';
}

// ============================================
// UI Helpers
// ============================================

function showSection(section) {
    elements.inputSection.classList.toggle('hidden', section !== 'input');
    elements.progressSection.classList.toggle('hidden', section !== 'progress');
    elements.resultsSection.classList.toggle('hidden', section !== 'results');
    
    // Scroll to top on section change
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function initNewSearchBtn() {
    elements.newSearchBtn.addEventListener('click', () => {
        showSection('input');
        elements.background.focus();
    });
}

function toggleDetails(button) {
    const content = button.nextElementSibling;
    const isOpen = content.classList.toggle('open');
    button.querySelector('span:first-child').textContent = isOpen ? 'Hide details' : 'Show more details';
    button.querySelector('.toggle-icon').textContent = isOpen ? '▲' : '▼';
}

function copyTopic(button, index) {
    const topic = document.querySelectorAll('.topic-card')[index];
    const title = topic.querySelector('.topic-title').textContent;
    const hook = topic.querySelector('.topic-hook')?.textContent || '';
    const description = topic.querySelector('.topic-description').textContent;
    
    const text = `${title}\n\n${hook}\n\n${description}`;
    
    navigator.clipboard.writeText(text).then(() => {
        button.classList.add('copied');
        button.textContent = '✓';
        setTimeout(() => {
            button.classList.remove('copied');
            button.textContent = '📋';
        }, 2000);
    });
}

// ============================================
// Toast Notifications
// ============================================

function showToast(message, type = 'info') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ============================================
// Local Storage
// ============================================

function savePreferences() {
    const prefs = {
        background: elements.background.value,
        keywords: keywords,
        audience: elements.audience.value,
        customAudience: elements.customAudience.value
    };
    localStorage.setItem('topicGenPrefs', JSON.stringify(prefs));
}

function loadSavedPreferences() {
    try {
        const saved = localStorage.getItem('topicGenPrefs');
        if (!saved) return;
        
        const prefs = JSON.parse(saved);
        
        if (prefs.background) {
            elements.background.value = prefs.background;
        }
        
        if (prefs.keywords && Array.isArray(prefs.keywords)) {
            keywords = prefs.keywords;
            updateKeywordsTags();
            updateHiddenKeywords();
        }
        
        if (prefs.audience) {
            elements.audience.value = prefs.audience;
            if (prefs.audience === 'custom' && prefs.customAudience) {
                elements.customAudience.classList.remove('hidden');
                elements.customAudience.value = prefs.customAudience;
            }
        }
    } catch (error) {
        console.error('Error loading preferences:', error);
    }
}

// ============================================
// Utilities
// ============================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make functions globally available for onclick handlers
window.removeKeyword = removeKeyword;
window.toggleDetails = toggleDetails;
window.copyTopic = copyTopic;
