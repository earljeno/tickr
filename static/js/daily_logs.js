function initDailyLogs() {
    setupSearch();
    setupFilters();
    setupAutoRefresh();
    setupTableInteractions();
    addInteractiveEffects();
    updateLastUpdated();
}

function loadLogs() {
    dateFilter = document.getElementById("dateFilter").value

    fetch(`/api/get-daily-logs?today=${dateFilter}`)
        .then(res => {
            if (!res.ok) showAlert('error', res.status);
            return res.json();
        })
        .then(logs => {
            const tbody = document.getElementById('logsTableBody');
            tbody.innerHTML = '';

            logs.forEach(record => {
                const tr = document.createElement("tr");

                tr.innerHTML = `
                        <td class="ps-4">
                            <div class="d-flex align-items-center">
                                <div class="user-avatar me-3">${record.name_initial}</div>
                                <div>
                                    <div class="user-name">${record.full_name}</div>
                                    <div class="user-email">${record.user_id}</div>
                                </div>
                            </div>
                        </td>
                        <!-- <td>
                            <span class="department-badge engineering">Engineering</span>
                        </td> -->
                        <td>
                            <div class="time-log">
                                <div class="time-display text-center">${record.clock_in}</div>
                                <!-- <small class="text-muted">On time</small>-->
                            </div>
                        </td>
                        <td>
                            <div class="time-log">
                                <div class="time-display text-center">${record.clock_out}</div>
                                <!-- <small class="text-muted">Regular time</small>-->
                            </div>
                        </td>
                        <td>
                            <div class="total-hours">
                                <div class="hours-display text-center">${record.total_hours} hrs</div>
                                <!-- <small class="text-success">Complete</small> -->
                            </div>
                        </td>
                        <!-- <td>
                            <span class="status-badge completed">Completed</span>
                        </td> -->
                        <td>
                            <div class="action-buttons d-flex justify-content-center">
                                <button class="btn btn-sm btn-outline-primary" data-log-id="${record.log_id}" title="View Details" hidden>
                                    <i class="fas fa-eye"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-warning" data-log-id="${record.log_id}" title="Edit Log">
                                    <i class="fas fa-edit"></i>
                                </button>
                            </div>
                        </td>
                    `;

                tbody.appendChild(tr);
            })
        })
}

const tbody = document.getElementById('logsTableBody');
tbody.addEventListener('click', e => {
    const viewBtn = e.target.closest('.btn-outline-primary');
    const editBtn = e.target.closest('.btn-outline-warning');

    if (editBtn) {
        const logId = editBtn.getAttribute('data-log-id');
        console.log('Edit clicked:', logId);

        fetch(`/api/get-user-log/${logId}`)
            .then(res => {
                if (!res.ok) showAlert('error', res.status);
                return res.json();
            })
            .then(user => {
                document.getElementById('logId').value = user.log_id;
                document.getElementById('giaName').value = user.full_name;
                document.getElementById('editCheckIn').value = user.clock_in;
                document.getElementById('editCheckOut').value = user.clock_out || '';
                document.getElementById('editNotes').value = user.notes || '';

                new bootstrap.Modal(document.getElementById('editLogModal')).show();
            })
            .catch(err => {
                console.error("Failed to load user:", err.message);
                alert("User not found or something went wrong.");
            });
    }

    document.getElementById("saveLogChanges").addEventListener("click", function (e) {
        const form = document.getElementById('editLogForm');
        const logId = document.getElementById('logId').value;

        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';
        this.disabled = true;

        const editedData = {
            clockIn: document.getElementById('editCheckIn').value,
            clockOut: document.getElementById('editCheckOut').value,
            notes: document.getElementById('editNotes').value,
        }

        // Send to backend
        fetch(`/api/update-log/${logId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(editedData)
        })
            .then(res => res.json())
            .then(data => {
                this.innerHTML = 'Save Changes';
                this.disabled = false;

                if (data.success) {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('editLogModal'));
                    modal.hide();
                    showAlert('success', data.message);
                    loadLogs();
                    filterLogs();
                } else {
                    console.error('Error updating user:', data.error);
                }
            })
            .catch(err => {
                this.innerHTML = 'Save Changes';
                this.disabled = false;
                showAlert('error', err);
                console.error('Fetch error:', err);
            });

    })

    if (viewBtn) {
        new bootstrap.Modal(document.getElementById('logDetailsModal')).show();
    }

});

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
        filter.addEventListener('change', filterLogs);
    });

    // Clear filters
    document.getElementById('clearFilters').addEventListener('click', function () {
        filters.forEach(filterId => {
            if (filterId !== 'dateFilter') {
                document.getElementById(filterId).value = '';
            }
        });
        document.getElementById('logsSearch').value = '';
        filterLogs();

        // Visual feedback
        this.textContent = 'Cleared!';
        setTimeout(() => {
            this.innerHTML = '<i class="fas fa-times me-2"></i>Clear Filters';
        }, 1000);
    });
}

// Auto-refresh functionality
function setupAutoRefresh() {
    const autoRefreshToggle = document.getElementById('autoRefresh');
    const refreshBtn = document.getElementById('refreshLogs');
    let refreshInterval;

    function startAutoRefresh() {
        if (autoRefreshToggle.checked) {
            refreshInterval = setInterval(() => {
                refreshLogs();
                filterLogs();
            }, 30000); // Refresh every 30 seconds
        }
    }

    function stopAutoRefresh() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
        }
    }

    autoRefreshToggle.addEventListener('change', function () {
        if (this.checked) {
            startAutoRefresh();
            console.log('Auto-refresh enabled');
        } else {
            stopAutoRefresh();
            console.log('Auto-refresh disabled');
        }
    });

    refreshBtn.addEventListener('click', function () {
        refreshLogs();
    });

    // Start auto-refresh by default
    startAutoRefresh();
}

// Refresh logs function
function refreshLogs() {
    const refreshBtn = document.getElementById('refreshLogs');

    refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Refreshing...';
    refreshBtn.disabled = true;

    // Simulate API call
    setTimeout(() => {
        loadLogs();
        refreshBtn.innerHTML = '<i class="fas fa-sync me-2"></i>Refresh';
        refreshBtn.disabled = false;
        updateLastUpdated();
    }, 1500);
}

// Filter logs based on search and filter criteria
function filterLogs() {
    const searchTerm = document.getElementById('logsSearch').value.toLowerCase();
    const dateFilter = document.getElementById('dateFilter').value;
    // const departmentFilter = document.getElementById('departmentFilter').value;
    // const statusFilter = document.getElementById('statusFilter').value;

    const rows = document.querySelectorAll('#logsTableBody tr');
    let visibleCount = 0;

    rows.forEach(row => {
        const employeeName = row.querySelector('.user-name').textContent.toLowerCase();
        const employeeEmail = row.querySelector('.user-email').textContent.toLowerCase();
        // const department = row.querySelector('.department-badge').textContent.toLowerCase();
        // const status = row.querySelector('.status-badge').textContent.toLowerCase();

        const matchesSearch = employeeName.includes(searchTerm) || employeeEmail.includes(searchTerm);
        // const matchesDepartment = !departmentFilter || department === departmentFilter;
        // const matchesStatus = !statusFilter || status.includes(statusFilter);

        // if (matchesSearch && matchesDepartment && matchesStatus) {
        //     row.style.display = '';
        //     visibleCount++;
        // } else {
        //     row.style.display = 'none';
        // }
    });

    // Update showing info
    const showingInfo = document.querySelector('.showing-info');
    const selectedDate = document.getElementById('dateFilter').value;
    const dateStr = selectedDate ? new Date(selectedDate).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    }) : 'today';
    // showingInfo.textContent = `Showing 1-${visibleCount} of 248 employees for ${dateStr}`;
}

// Table interactions
function setupTableInteractions() {
    // View details buttons
    const viewButtons = document.querySelectorAll('.action-buttons .btn-outline-primary');
    viewButtons.forEach(button => {
        button.addEventListener('click', function () {
            const row = this.closest('tr');
            const employeeName = row.querySelector('.user-name').textContent;

            // Populate modal with employee data
            populateLogDetailsModal(row);

            const modal = new bootstrap.Modal(document.getElementById('logDetailsModal'));
            modal.show();

            console.log(`Viewing details for: ${employeeName}`);
        });
    });

    // Edit log buttons
    const editButtons = document.querySelectorAll('.action-buttons .btn-outline-warning');
    editButtons.forEach(button => {
        button.addEventListener('click', function () {
            const row = this.closest('tr');
            const employeeName = row.querySelector('.user-name').textContent;

            // Populate edit modal with current data
            populateEditLogModal(row);

            const modal = new bootstrap.Modal(document.getElementById('editLogModal'));
            modal.show();

            console.log(`Editing log for: ${employeeName}`);
        });
    });

    // Export button
    const exportBtn = document.querySelector('.btn-outline-primary');
    if (exportBtn && exportBtn.textContent.includes('Export')) {
        exportBtn.addEventListener('click', function () {
            this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Exporting...';
            this.disabled = true;

            setTimeout(() => {
                this.innerHTML = '<i class="fas fa-download me-1"></i>Export';
                this.disabled = false;
                showAlert('success', 'Logs exported successfuly');
                console.log('Logs exported');
            }, 2000);
        });
    }
}

// Populate log details modal
function populateLogDetailsModal(row) {
    const employeeName = row.querySelector('.user-name').textContent;
    // const department = row.querySelector('.department-badge').textContent;
    const checkIn = row.querySelector('.time-log .time-display').textContent;
    const totalHours = row.querySelector('.total-hours .hours-display').textContent;
    // const status = row.querySelector('.status-badge').textContent;

    // Update modal content (simplified for demo)
    const modal = document.getElementById('logDetailsModal');
    modal.querySelector('.fw-medium').textContent = employeeName;
    modal.querySelector('.text-muted').textContent = `${department} - Manager`;
}

// Populate edit log modal
function populateEditLogModal(row) {
    const employeeName = row.querySelector('.user-name').textContent;

    // Update modal content (simplified for demo)
    const modal = document.getElementById('editLogModal');
    modal.querySelector('input[readonly]').value = employeeName;
}

// Update last updated timestamp
function updateLastUpdated() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });

    document.getElementById('lastUpdated').textContent = timeString;
}

// Add interactive effects
function addInteractiveEffects() {
    // Table row hover effects
    const tableRows = document.querySelectorAll('#logsTableBody tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function () {
            this.style.backgroundColor = '#f8f9fa';
        });

        row.addEventListener('mouseleave', function () {
            this.style.backgroundColor = '';
        });
    });

    // Status badge hover effects
    // const statusBadges = document.querySelectorAll('.status-badge');
    // statusBadges.forEach(badge => {
    //     badge.addEventListener('mouseenter', function () {
    //         this.style.transform = 'scale(1.05)';
    //     });

    //     badge.addEventListener('mouseleave', function () {
    //         this.style.transform = '';
    //     });
    // });
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

    if (document.hidden) {
        console.log('Page hidden - pausing auto-refresh');
    } else {
        console.log('Page visible - resuming auto-refresh');
        if (autoRefreshToggle.checked) {
            refreshLogs();
        }
    }
});

document.getElementById("dateFilter").addEventListener("change", () => {
    loadLogs();
})

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

                    this.innerHTML = 'Add Manual Log';
                    this.disabled = false;
                    const modal = bootstrap.Modal.getInstance(document.getElementById('addManualLogModal'));
                    modal.hide();
                    form.reset();
                    console.log('New manual log added successfully');
                    
                } else {
                    console.error('Error updating user:', data.error);
                }
            })
            .catch(err => {
                this.innerHTML = 'Save Changes';
                this.disabled = false;
                console.error('Fetch error:', err);
            });
    } else {
        form.reportValidity();
    }
});