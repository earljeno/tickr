function initAuditLogs() {
    setupFilters();
    setupSearch();
    setupTableInteractions();
    addInteractiveEffects();
    loadLogs(1);
}

let currentPage = 1;
const perPage = 8;

const defaultFilterValues = {
    fromDate: document.getElementById('fromDate')?.value || '',
    toDate: document.getElementById('toDate')?.value || ''
};

function loadLogs(page = 1) {
    currentPage = page;
    const fromDate = document.getElementById('fromDate').value;
    const toDate = document.getElementById('toDate').value;
    const userFilter = document.getElementById('userFilter').value.trim();
    const actionFilter = document.getElementById('actionFilter').value.trim();
    const searchTerm = document.getElementById('searchLogs').value.trim();

    const params = new URLSearchParams({
        from: fromDate,
        to: toDate,
        page,
        per_page: perPage
    });

    if (userFilter) params.set('user', userFilter);
    if (actionFilter) params.set('action', actionFilter);
    if (searchTerm) params.set('search', searchTerm);

    const tbody = document.getElementById('auditLogsTableBody');
    const showingInfo = document.querySelector('.showing-info');
    const tableContainer = tbody ? tbody.closest('.table-responsive') : null;
    const hasExistingRows = tbody && tbody.querySelectorAll('tr').length > 0 && !tbody.querySelector('.spinner-border');

    if (tableContainer) {
        tableContainer.classList.add('table-loading-container');
    }

    if (hasExistingRows) {
        // Keep existing rows visible so the table height does not shrink while fetching
        if (tableContainer) {
            tableContainer.classList.add('is-loading-data');
            let overlay = tableContainer.querySelector('.table-loading-overlay');
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.className = 'table-loading-overlay';
                overlay.innerHTML = `
                    <div class="table-loading-badge">
                        <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
                        <span>Loading audit logs...</span>
                    </div>
                `;
                tableContainer.appendChild(overlay);
            }
        }
    } else {
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-5 text-muted">
                        <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                        Loading audit logs...
                    </td>
                </tr>
            `;
        }
    }
    if (showingInfo && !hasExistingRows) showingInfo.textContent = 'Loading audit logs...';

    fetch(`/api/get-logs?${params.toString()}`)
        .then(res => {
            if (!res.ok) throw new Error(`Server responded with ${res.status}`);
            return res.json();
        })
        .then(data => {
            tbody.innerHTML = '';

            if (!data.logs || data.logs.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="5" class="text-center py-4 text-muted">
                            No audit logs match the current filters.
                        </td>
                    </tr>
                `;
            } else {
                data.logs.forEach(log => {
                    const tr = document.createElement('tr');
                    const safeDate = typeof escapeHtml === 'function' ? escapeHtml(log.date) : log.date;
                    const safeTime = typeof escapeHtml === 'function' ? escapeHtml(log.time) : log.time;
                    const safeName = typeof escapeHtml === 'function' ? escapeHtml(log.full_name) : log.full_name;
                    const safeRole = typeof escapeHtml === 'function' ? escapeHtml(log.role) : log.role;
                    const safeAction = typeof escapeHtml === 'function' ? escapeHtml(log.action) : log.action;
                    const safeDetails = typeof escapeHtml === 'function' ? escapeHtml(log.details || '') : (log.details || '');
                    const safeIp = typeof escapeHtml === 'function' ? escapeHtml(log.ip || '') : (log.ip || '');
                    const actionClass = (log.action || '').toLowerCase().replace(/[^a-z0-9_-]/g, '');

                    tr.innerHTML = `
                        <td>
                            <div class="timestamp">
                                <div class="fw-medium">${safeDate}</div>
                                <small class="text-muted">${safeTime}</small>
                            </div>
                        </td>
                        <td>
                            <div class="user-info">
                                <div class="fw-medium">${safeName}</div>
                                <small class="text-muted">${safeRole}</small>
                            </div>
                        </td>
                        <td>
                            <span class="action-badge ${actionClass}">${safeAction}</span>
                        </td>
                        <td>
                            <div class="details-text">${safeDetails}</div>
                        </td>
                        <td>
                            <small class="text-muted">${safeIp}</small>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            }

            renderPagination(data.page, data.pages, data.total);
        })
        .catch(error => {
            console.error('Failed to load audit logs:', error);
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-4 text-danger">
                        Unable to load audit logs. Please refresh or try again later.
                    </td>
                </tr>
            `;
            showingInfo.textContent = 'Unable to load audit logs.';
        })
        .finally(() => {
            if (tableContainer) {
                tableContainer.classList.remove('is-loading-data');
            }
        });
}

// Setup filter functionality
function setupFilters() {
    const fromDate = document.getElementById('fromDate');
    const toDate = document.getElementById('toDate');
    const userFilter = document.getElementById('userFilter');
    const actionFilter = document.getElementById('actionFilter');
    const resetButton = document.getElementById('resetFilters');

    [fromDate, toDate, userFilter, actionFilter].forEach(control => {
        control?.addEventListener('change', () => loadLogs(1));
    });

    resetButton?.addEventListener('click', function(event) {
        event.preventDefault();
        resetFilters();
        loadLogs(1);

        this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Resetting...';
        this.disabled = true;

        setTimeout(() => {
            this.innerHTML = '<i class="fas fa-undo me-1"></i>Clear';
            this.disabled = false;
        }, 500);
    });
}

function applyFilters() {
    loadLogs(1);
}

// Reset all filters
function resetFilters() {
    const fromDateInput = document.getElementById('fromDate');
    const toDateInput = document.getElementById('toDate');

    if (fromDateInput) fromDateInput.value = defaultFilterValues.fromDate;
    if (toDateInput) toDateInput.value = defaultFilterValues.toDate;
    document.getElementById('userFilter').value = '';
    document.getElementById('actionFilter').value = '';
    document.getElementById('searchLogs').value = '';

    const showingInfo = document.querySelector('.showing-info');
    showingInfo.textContent = 'Loading audit logs...';

    console.log('Filters reset');
}

// Setup search functionality
function setupSearch() {
    const searchInput = document.getElementById('searchLogs');
    let debounceTimer;

    searchInput?.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => loadLogs(1), 300);
    });

    searchInput?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            loadLogs(1);
        }
    });
}

// Setup table interactions
function setupTableInteractions() {
    // Export logs button
    const exportBtn = document.querySelector('.btn-outline-primary');
    exportBtn?.addEventListener('click', function() {
        this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Exporting...';
        this.disabled = true;
        
        setTimeout(() => {
            this.innerHTML = '<i class="fas fa-download me-2"></i>Export Logs';
            this.disabled = false;
            console.log('Audit logs exported');
        }, 2000);
    });
    
    // Refresh logs button
    const refreshBtn = document.getElementById('refreshLogs');
    refreshBtn?.addEventListener('click', function() {
        this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Refreshing...';
        this.disabled = true;
        
        setTimeout(() => {
            loadLogs(1);
            this.innerHTML = '<i class="fas fa-sync me-1"></i>Refresh';
            this.disabled = false;
            console.log('Audit logs refreshed');
        }, 1500);
    });

    // Row click for details (optional)
    const tbody = document.getElementById('auditLogsTableBody');
    tbody.addEventListener('click', function(event) {
        const row = event.target.closest('tr');
        if (!row) return;

        const user = row.querySelector('.user-info .fw-medium')?.textContent || 'Unknown';
        const action = row.querySelector('.action-badge')?.textContent || 'Unknown';
        console.log(`Clicked log entry: ${user} ${action}`);
    });
}

// Add interactive effects
function addInteractiveEffects() {
    const tbody = document.getElementById('auditLogsTableBody');
    tbody?.addEventListener('mouseover', function(event) {
        const row = event.target.closest('tr');
        if (row) {
            row.style.backgroundColor = '#f8f9fa';
            row.style.cursor = 'pointer';
        }
    });

    tbody?.addEventListener('mouseout', function(event) {
        const row = event.target.closest('tr');
        if (row) {
            row.style.backgroundColor = '';
            row.style.cursor = '';
        }
    });

    const card = document.querySelector('.content-card');
    card?.addEventListener('mouseover', function(event) {
        const badge = event.target.closest('.action-badge');
        if (badge) badge.style.transform = 'scale(1.05)';
    });

    card?.addEventListener('mouseout', function(event) {
        const badge = event.target.closest('.action-badge');
        if (badge) badge.style.transform = '';
    });
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault();
        document.getElementById('searchLogs')?.focus();
    }

    if (e.key === 'Escape') {
        const searchInput = document.getElementById('searchLogs');
        if (document.activeElement === searchInput) {
            searchInput.value = '';
            applyFilters();
            searchInput.blur();
        }
    }

    if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
        e.preventDefault();
        document.getElementById('refreshLogs')?.click();
    }
});

// Handle page visibility change for auto-refresh
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        console.log('Page hidden - pausing auto-refresh');
    } else {
        console.log('Page visible - resuming auto-refresh');
    }
});

function renderPagination(current, totalPages, totalItems) {
    const container = document.querySelector('.pagination');
    const showingInfo = document.querySelector('.showing-info');

    if (totalItems === 0) {
        showingInfo.textContent = 'Showing 0-0 of 0 audit log entries';
    } else {
        const pageStart = (current - 1) * perPage + 1;
        const pageEnd = Math.min(current * perPage, totalItems);
        showingInfo.textContent = `Showing ${pageStart}-${pageEnd} of ${totalItems} audit log entries`;
    }

    container.innerHTML = '';

    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${current === 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `<a class="page-link" href="#">Previous</a>`;
    prevLi.addEventListener('click', e => { e.preventDefault(); if (current > 1) loadLogs(current - 1); });
    container.appendChild(prevLi);

    const windowSize = 2;
    let start = Math.max(1, current - windowSize);
    let end = Math.min(totalPages, current + windowSize);

    for (let i = start; i <= end; i++) {
        const li = document.createElement('li');
        li.className = `page-item ${i === current ? 'active' : ''}`;
        li.innerHTML = `<a class="page-link" href="#">${i}</a>`;
        li.addEventListener('click', e => { e.preventDefault(); loadLogs(i); });
        container.appendChild(li);
    }

    const nextLi = document.createElement('li');
    const disableNext = totalPages <= 1 || current >= totalPages;
    nextLi.className = `page-item ${disableNext ? 'disabled' : ''}`;
    nextLi.innerHTML = `<a class="page-link" href="#">Next</a>`;
    nextLi.addEventListener('click', e => { e.preventDefault(); if (!disableNext) loadLogs(current + 1); });
    container.appendChild(nextLi);
}

document.addEventListener('DOMContentLoaded', initAuditLogs);
