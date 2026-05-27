// GitHub Monitor Dashboard JavaScript

// Global variables
let timelineChart = null;
let autoRefreshInterval = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    console.log('GitHub Monitor Dashboard loaded');
    
    // Load initial data
    loadStats();
    loadRepositories();
    loadUpdates();
    loadTimeline();
    
    // Setup modal
    setupModal();
    
    // Auto-refresh every 30 seconds
    autoRefreshInterval = setInterval(() => {
        loadStats();
        loadRepositories();
        loadUpdates();
        loadTimeline();
    }, 30000);
});

// Load statistics
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        document.getElementById('total-repos').textContent = data.total_repos;
        document.getElementById('total-updates').textContent = data.total_updates;
        document.getElementById('updates-today').textContent = data.updates_today;
        
        if (data.most_active) {
            document.getElementById('most-active').textContent = 
                data.most_active.repo_name.split('/')[1] || data.most_active.repo_name;
        } else {
            document.getElementById('most-active').textContent = 'N/A';
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load repositories
async function loadRepositories() {
    try {
        const response = await fetch('/api/repositories');
        const repos = await response.json();
        
        const tbody = document.getElementById('repos-tbody');
        
        if (repos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="loading">No repositories found</td></tr>';
            return;
        }
        
        tbody.innerHTML = repos.map(repo => `
            <tr>
                <td>
                    <a href="https://github.com/${escapeHtml(repo.repo_name)}"
                       target="_blank"
                       rel="noopener noreferrer"
                       style="color: var(--primary-color); text-decoration: none; font-weight: bold;">
                        ${escapeHtml(repo.repo_name)}
                        <span style="font-size: 0.8em; opacity: 0.7;">🔗</span>
                    </a>
                </td>
                <td>${escapeHtml(repo.first_checked_at)}</td>
                <td>${escapeHtml(repo.last_checked_at)}</td>
                <td>
                    <span style="color: var(--primary-color); font-weight: bold;">
                        ${repo.update_count}
                    </span>
                </td>
                <td>
                    <button class="btn btn-primary" onclick="showRepoDetails(${repo.id})">
                        View Details
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading repositories:', error);
        document.getElementById('repos-tbody').innerHTML = 
            '<tr><td colspan="5" class="loading">Error loading repositories</td></tr>';
    }
}

// Load recent updates
async function loadUpdates() {
    try {
        const response = await fetch('/api/updates');
        const updates = await response.json();
        
        const container = document.getElementById('updates-list');
        
        if (updates.length === 0) {
            container.innerHTML = '<div class="loading">No updates found</div>';
            return;
        }
        
        container.innerHTML = updates.map(update => `
            <div class="update-item ${update.is_first_run ? 'first-run' : ''}">
                <div class="update-header">
                    <div class="update-repo">
                        <a href="https://github.com/${escapeHtml(update.repo_name)}"
                           target="_blank"
                           rel="noopener noreferrer"
                           style="color: var(--primary-color); text-decoration: none;">
                            ${escapeHtml(update.repo_name)}
                            <span style="font-size: 0.8em; opacity: 0.7;">🔗</span>
                        </a>
                    </div>
                    <span class="update-badge ${update.is_first_run ? 'badge-first' : 'badge-update'}">
                        ${update.is_first_run ? 'FIRST RUN' : 'UPDATE'}
                    </span>
                </div>
                <div class="update-time">
                    <strong>Updated:</strong> ${escapeHtml(update.update_timestamp)}<br>
                    <strong>Checked:</strong> ${escapeHtml(update.check_timestamp)}
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading updates:', error);
        document.getElementById('updates-list').innerHTML = 
            '<div class="loading">Error loading updates</div>';
    }
}

// Load timeline chart
async function loadTimeline() {
    try {
        const response = await fetch('/api/timeline');
        const timeline = await response.json();
        
        if (timeline.length === 0) {
            return;
        }
        
        // Reverse to show oldest to newest
        timeline.reverse();
        
        const ctx = document.getElementById('timeline-chart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (timelineChart) {
            timelineChart.destroy();
        }
        
        timelineChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timeline.map(item => item.date),
                datasets: [{
                    label: 'Updates',
                    data: timeline.map(item => item.count),
                    borderColor: '#2196F3',
                    backgroundColor: 'rgba(33, 150, 243, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#2196F3',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#2196F3',
                        borderWidth: 1
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#b0b0b0',
                            stepSize: 1
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#b0b0b0',
                            maxRotation: 45,
                            minRotation: 45
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading timeline:', error);
    }
}

// Show repository details in modal
async function showRepoDetails(repoId) {
    const modal = document.getElementById('modal');
    const modalBody = document.getElementById('modal-body');
    
    modal.style.display = 'block';
    modalBody.innerHTML = '<div class="loading">Loading...</div>';
    
    try {
        const response = await fetch(`/api/repository/${repoId}`);
        const data = await response.json();
        
        if (data.error) {
            modalBody.innerHTML = `<div class="loading">${escapeHtml(data.error)}</div>`;
            return;
        }
        
        const repo = data.repository;
        const updates = data.updates;
        
        document.getElementById('modal-title').innerHTML = `
            <a href="https://github.com/${escapeHtml(repo.repo_name)}"
               target="_blank"
               rel="noopener noreferrer"
               style="color: var(--text-primary); text-decoration: none;">
                ${escapeHtml(repo.repo_name)}
                <span style="font-size: 0.7em; opacity: 0.7;">🔗</span>
            </a>
        `;
        
        modalBody.innerHTML = `
            <div class="repo-detail">
                <div class="repo-detail-label">Repository URL</div>
                <div class="repo-detail-value">
                    <a href="https://github.com/${escapeHtml(repo.repo_name)}"
                       target="_blank"
                       rel="noopener noreferrer"
                       style="color: var(--primary-color); text-decoration: none;">
                        https://github.com/${escapeHtml(repo.repo_name)} 🔗
                    </a>
                </div>
            </div>
            <div class="repo-detail">
                <div class="repo-detail-label">Repository ID</div>
                <div class="repo-detail-value">${repo.id}</div>
            </div>
            <div class="repo-detail">
                <div class="repo-detail-label">First Checked</div>
                <div class="repo-detail-value">${escapeHtml(repo.first_checked_at)}</div>
            </div>
            <div class="repo-detail">
                <div class="repo-detail-label">Last Update</div>
                <div class="repo-detail-value">${escapeHtml(repo.last_checked_at)}</div>
            </div>
            <div class="repo-detail">
                <div class="repo-detail-label">Total Updates</div>
                <div class="repo-detail-value">${updates.length}</div>
            </div>
            
            <h3 style="margin-top: 30px; margin-bottom: 15px;">Update History</h3>
            <div class="updates-container">
                ${updates.map(update => `
                    <div class="update-item ${update.is_first_run ? 'first-run' : ''}">
                        <div class="update-header">
                            <span class="update-badge ${update.is_first_run ? 'badge-first' : 'badge-update'}">
                                ${update.is_first_run ? 'FIRST RUN' : 'UPDATE'}
                            </span>
                        </div>
                        <div class="update-time">
                            <strong>Updated:</strong> ${escapeHtml(update.update_timestamp)}<br>
                            <strong>Checked:</strong> ${escapeHtml(update.check_timestamp)}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        console.error('Error loading repository details:', error);
        modalBody.innerHTML = '<div class="loading">Error loading repository details</div>';
    }
}

// Setup modal
function setupModal() {
    const modal = document.getElementById('modal');
    const closeBtn = document.querySelector('.close');
    
    closeBtn.onclick = function() {
        modal.style.display = 'none';
    };
    
    window.onclick = function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    };
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    if (timelineChart) {
        timelineChart.destroy();
    }
});

// Made with Bob
