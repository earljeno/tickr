function initDailyLogs() {
    setupSearch();
    setupFilters();
    setupAutoRefresh();
    setupModalsAndActions();
    updateLastUpdated();
}

function loadLogs(isBackground = false) {
    const dateInput = document.getElementById("dateFilter");
    const dateFilter = dateInput ? dateInput.value : '';

    const queryDisplay = document.getElementById("queryDateDisplay");
    if (queryDisplay && dateFilter) {
        queryDisplay.textContent = dateFilter;
    }

    const tbody = document.getElementById('logsTableBody');
    const tableContainer = tbody ? tbody.closest('.table-responsive') : null;
    const hasExistingRows = tbody && tbody.querySelectorAll('tr').length > 0 && !tbody.querySelector('.spinner-border');

    if (tableContainer) {
        tableContainer.classList.add('table-loading-container');
    }

    if (isBackground && hasExistingRows) {
        // Subtle non-intrusive refresh without wiping current rows
        if (tableContainer) {
            tableContainer.classList.add('is-loading-data');
            let overlay = tableContainer.querySelector('.table-loading-overlay');
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.className = 'table-loading-overlay';
                overlay.innerHTML = `
                    <div class="table-loading-badge">
                        <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
                        <span>Updating daily logs...</span>
                    </div>
                `;
                tableContainer.appendChild(overlay);
            }
        }
    } else {
        // Initial / explicit full load: show spinner inside tbody
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-5 text-muted">
                        <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                        Loading daily attendance records...
                    </td>
                </tr>
            `;
        }
    }

    fetch(`/api/get-daily-logs?today=${encodeURIComponent(dateFilter)}`)
        .then(res => {
            if (!res.ok) throw new Error(`HTTP error ${res.status}`);
            return res.json();
        })
        .then(logs => {
            if (!tbody) return;
            tbody.innerHTML = '';

            if (!logs || logs.length === 0) {
                tbody.innerHTML = `
                    <tr class="empty-state-row">
                        <td colspan="5" class="text-center py-5">
                            <div class="d-flex flex-column align-items-center justify-content-center text-muted">
                                <div class="stat-icon total-icon mb-3" style="width: 48px; height: 48px; font-size: 1.25rem;">
                                    <i class="bi bi-calendar-x"></i>
                                </div>
                                <h6 class="fw-semibold text-dark mb-1">No attendance records found</h6>
                                <p class="small mb-0 text-secondary">No student assistants have clocked in for ${escapeHtml(dateFilter || 'selected date')}.</p>
                            </div>
                        </td>
                    </tr>
                `;
            } else {
                logs.forEach(record => {
                    const tr = document.createElement("tr");
                    const safeInitial = typeof escapeHtml === 'function' ? escapeHtml(record.name_initial) : record.name_initial;
                    const safeName = typeof escapeHtml === 'function' ? escapeHtml(record.full_name) : record.full_name;
                    const safeUserId = typeof escapeHtml === 'function' ? escapeHtml(record.user_id) : record.user_id;
                    const safeClockIn = typeof escapeHtml === 'function' ? escapeHtml(record.clock_in) : record.clock_in;
                    const safeClockOut = typeof escapeHtml === 'function' ? escapeHtml(record.clock_out) : record.clock_out;
                    const safeHours = typeof escapeHtml === 'function' ? escapeHtml(record.total_hours) : record.total_hours;
                    const safeLogId = typeof escapeHtml === 'function' ? escapeHtml(record.log_id) : record.log_id;

                    tr.innerHTML = `
                            <td class="ps-4">
                                <div class="d-flex align-items-center">
                                    <div class="user-avatar me-3">${safeInitial}</div>
                                    <div>
                                        <div class="user-name">${safeName}</div>
                                        <div class="user-email">${safeUserId}</div>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <div class="time-log">
                                    <div class="time-display text-center">${safeClockIn || '<span class="text-muted">-</span>'}</div>
                                </div>
                            </td>
                            <td>
                                <div class="time-log">
                                    <div class="time-display text-center">${safeClockOut || '<span class="badge bg-light text-primary border fw-normal">In Progress</span>'}</div>
                                </div>
                            </td>
                            <td>
                                <div class="total-hours">
                                    <div class="hours-display text-center">${safeHours} hrs</div>
                                </div>
                            </td>
                            <td>
                                <div class="action-buttons d-flex justify-content-center">
                                    <button class="btn btn-sm btn-outline-primary" data-log-id="${safeLogId}" title="View Details" hidden>
                                        <i class="fas fa-eye"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-warning" data-log-id="${safeLogId}" title="Edit Log">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                </div>
                            </td>
                        `;

                    tbody.appendChild(tr);
                });
            }

            filterLogs();
            updateLastUpdated();
        })
        .catch(err => {
            console.error('Failed to load daily logs:', err);
            if (!hasExistingRows && tbody) {
                tbody.innerHTML = `
                    <tr class="empty-state-row">
                        <td colspan="5" class="text-center py-4 text-danger">
                            <i class="bi bi-exclamation-triangle-fill me-2"></i>Unable to load daily logs. Please check your network and refresh.
                        </td>
                    </tr>
                `;
            }
        })
        .finally(() => {
            if (tableContainer) {
                tableContainer.classList.remove('is-loading-data');
            }
        });
}

function setupModalsAndActions() {
    const tbody = document.getElementById('logsTableBody');
    if (tbody) {
        tbody.addEventListener('click', e => {
            const editBtn = e.target.closest('.btn-outline-warning');
            if (editBtn) {
                const logId = editBtn.getAttribute('data-log-id');
                const originalBtnHTML = editBtn.innerHTML;
                editBtn.disabled = true;
                editBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';

                fetch(`/api/get-user-log/${logId}`)
                    .then(res => {
                        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
                        return res.json();
                    })
                    .then(user => {
                        document.getElementById('logId').value = user.log_id || '';
                        document.getElementById('giaName').value = user.full_name || '';
                        document.getElementById('editCheckIn').value = user.clock_in || '';
                        document.getElementById('editCheckOut').value = user.clock_out || '';
                        document.getElementById('editNotes').value = user.notes || '';

                        new bootstrap.Modal(document.getElementById('editLogModal')).show();
                    })
                    .catch(err => {
                        console.error("Failed to load user log:", err);
                        showAlert('danger', "User log not found or error loading record.");
                    })
                    .finally(() => {
                        editBtn.disabled = false;
                        editBtn.innerHTML = originalBtnHTML;
                    });
            }
        });
    }

    const saveChangesBtn = document.getElementById("saveLogChanges");
    if (saveChangesBtn) {
        saveChangesBtn.addEventListener("click", function () {
            const form = document.getElementById('editLogForm');
            const logId = document.getElementById('logId').value;

            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }

            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Saving...';
            this.disabled = true;

            const editedData = {
                clockIn: document.getElementById('editCheckIn').value,
                clockOut: document.getElementById('editCheckOut').value,
                notes: document.getElementById('editNotes').value,
            };

            fetch(`/api/update-log/${logId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(editedData)
            })
                .then(res => res.json())
                .then(data => {
                    this.innerHTML = '<i class="bi bi-save"></i> Save Changes';
                    this.disabled = false;

                    if (data.success) {
                        const modal = bootstrap.Modal.getInstance(document.getElementById('editLogModal'));
                        if (modal) modal.hide();
                        showAlert('success', data.message || 'Log updated successfully!');
                        loadLogs(true);
                    } else {
                        showAlert('error', data.error || 'Failed to update attendance record');
                    }
                })
                .catch(err => {
                    this.innerHTML = '<i class="bi bi-save"></i> Save Changes';
                    this.disabled = false;
                    showAlert('error', err.message || err);
                });
        });
    }
}

// Search functionality
function setupSearch() {
    const searchInput = document.getElementById('logsSearch');

    searchInput.addEventListener('input', function () {
        const searchTerm = this.value.trim().toLowerCase();
        filterLogs();

        // Visual feedback
        if (searchTerm.length > 0) {
            this.style.borderColor = '#10b981';
            setTimeout(() => {
                this.style.borderColor = '#d1d5db';
            }, 1000);
        }
    });
}

// Filter functionality
function setupFilters() {
    const filters = ['dateFilter'];

    filters.forEach(filterId => {
        const filter = document.getElementById(filterId);
        filter?.addEventListener('change', () => loadLogs(false));
    });

    // Reset filters
    const clearBtn = document.getElementById('clearFilters');
    if (clearBtn) {
        clearBtn.addEventListener('click', function () {
            const today = new Date().toISOString().split('T')[0];
            const dateInput = document.getElementById('dateFilter');
            if (dateInput) {
                dateInput.value = today;
            }
            const searchInput = document.getElementById('logsSearch');
            if (searchInput) {
                searchInput.value = '';
            }
            loadLogs(false);
        });
    }
}

// Auto-refresh functionality
function setupAutoRefresh() {
    const autoRefreshToggle = document.getElementById('autoRefresh');
    const refreshBtn = document.getElementById('refreshLogs');
    let refreshInterval = null;

    function startAutoRefresh() {
        stopAutoRefresh();
        if (autoRefreshToggle && autoRefreshToggle.checked) {
            refreshInterval = setInterval(() => {
                loadLogs(true); // background silent update without clearing rows
            }, 30000); // Refresh every 30 seconds
        }
    }

    function stopAutoRefresh() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
    }

    if (autoRefreshToggle) {
        autoRefreshToggle.addEventListener('change', function () {
            if (this.checked) {
                startAutoRefresh();
            } else {
                stopAutoRefresh();
            }
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', function () {
            refreshLogs();
        });
    }

    // Start auto-refresh by default
    startAutoRefresh();
}

// Refresh logs function (manual button click)
function refreshLogs() {
    const refreshBtn = document.getElementById('refreshLogs');
    const originalHTML = refreshBtn ? refreshBtn.innerHTML : '';

    if (refreshBtn) {
        refreshBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Refreshing...';
        refreshBtn.disabled = true;
    }

    loadLogs(true);

    setTimeout(() => {
        if (refreshBtn) {
            refreshBtn.innerHTML = originalHTML || '<i class="bi bi-arrow-repeat"></i> <span>Refresh</span>';
            refreshBtn.disabled = false;
        }
    }, 600);
}

// Filter logs based on search and filter criteria
function filterLogs() {
    const searchInput = document.getElementById('logsSearch');
    const searchTerm = searchInput ? searchInput.value.trim().toLowerCase() : '';

    const tbody = document.getElementById('logsTableBody');
    if (!tbody) return;

    const rows = tbody.querySelectorAll('tr:not(.empty-state-row)');
    if (rows.length === 0) return;

    let visibleCount = 0;

    rows.forEach(row => {
        const nameEl = row.querySelector('.user-name');
        const emailEl = row.querySelector('.user-email');
        const employeeName = nameEl ? nameEl.textContent.toLowerCase() : '';
        const employeeEmail = emailEl ? emailEl.textContent.toLowerCase() : '';

        const matchesSearch = !searchTerm || employeeName.includes(searchTerm) || employeeEmail.includes(searchTerm);

        if (matchesSearch) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });

    // Handle no matching search results
    let searchEmptyRow = tbody.querySelector('.search-empty-row');
    if (visibleCount === 0 && searchTerm) {
        if (!searchEmptyRow) {
            searchEmptyRow = document.createElement('tr');
            searchEmptyRow.className = 'search-empty-row';
            searchEmptyRow.innerHTML = `
                <td colspan="5" class="text-center py-5 text-muted">
                    <i class="bi bi-search fs-4 d-block mb-2 text-secondary"></i>
                    <span class="fw-medium">No results match "${escapeHtml(searchTerm)}"</span>
                </td>
            `;
            tbody.appendChild(searchEmptyRow);
        }
    } else if (searchEmptyRow) {
        searchEmptyRow.remove();
    }
}

// Update last updated timestamp
function updateLastUpdated() {
    const el = document.getElementById('lastUpdated');
    if (!el) return;

    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });

    el.textContent = timeString;
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    loadLogs();
    initDailyLogs();
});

// Keyboard shortcuts
document.addEventListener('keydown', function (e) {
    // Ctrl/Cmd + K to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('logsSearch').focus();
    }

    // Escape to clear search
    if (e.key === 'Escape') {
        const searchInput = document.getElementById('logsSearch');
        if (document.activeElement === searchInput) {
            searchInput.value = '';
            filterLogs();
            searchInput.blur();
        }
    }
});

// Handle page visibility change for auto-refresh
document.addEventListener('visibilitychange', function () {
    const autoRefreshToggle = document.getElementById('autoRefresh');

    if (!document.hidden && autoRefreshToggle && autoRefreshToggle.checked) {
        loadLogs(true);
    }
});

// Add Manual Log button
const addManualLogBtn = document.querySelector('.add-manual-log-btn');
addManualLogBtn.addEventListener('click', function () {
    dateFilter = document.getElementById("dateFilter").value
    document.getElementById("addLogDate").value = dateFilter;

    const modal = new bootstrap.Modal(document.getElementById('addManualLogModal'));
    modal.show();
});

// Save new manual log
const saveManualLogBtn = document.getElementById('saveManualLog');
saveManualLogBtn.addEventListener('click', function () {
    const form = document.getElementById('addManualLogForm');
    if (form.checkValidity()) {

        const newLog = {
            userId: document.getElementById('addEmployee').value,
            date: document.getElementById('addLogDate').value,
            clockIn: document.getElementById('addTimeIn').value,
            clockOut: document.getElementById('addTimeOut').value
        }

        this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Adding...';
        this.disabled = true;

        fetch('/api/add-log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newLog)
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    loadLogs();

                    this.innerHTML = '<i class="bi bi-check-lg"></i> Record Entry';
                    this.disabled = false;
                    const modal = bootstrap.Modal.getInstance(document.getElementById('addManualLogModal'));
                    modal.hide();
                    form.reset();
                    showAlert('success', data.message || 'New manual log added successfully');
                    console.log('New manual log added successfully');
                    
                } else {
                    this.innerHTML = '<i class="bi bi-check-lg"></i> Record Entry';
                    this.disabled = false;
                    showAlert('error', data.error || 'Failed to add manual log');
                    console.error('Error adding manual log:', data.error);
                }
            })
            .catch(err => {
                this.innerHTML = '<i class="bi bi-check-lg"></i> Record Entry';
                this.disabled = false;
                showAlert('error', err.message || err);
                console.error('Fetch error:', err);
            });
    } else {
        form.reportValidity();
    }
});