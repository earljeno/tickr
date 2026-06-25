function initAuditLogs() {
    setupFilters();
    setupSearch();
    setupTableInteractions();
    addInteractiveEffects();
}

let currentPage = 1;
const perPage = 8;

function loadLogs(page = 1) {
    currentPage = page;
    const fromDate = document.getElementById("fromDate").value;
    const toDate = document.getElementById("toDate").value;

    fetch(`/api/get-logs?from=${fromDate}&to=${toDate}&page=${page}&per_page=${perPage}`)
        .then(res => {
            if (!res.ok) throw new Error(`Server responded with ${res.status}`);
            return res.json();
        })
        .then(data => {
            const tbody = document.getElementById('auditLogsTableBody');
            tbody.innerHTML = '';

            data.logs.forEach(log => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td>
                        <div class="timestamp">
                            <div class="fw-medium">${log.date}</div>
                            <small class="text-muted">${log.time}</small>
                        </div>
                    </td>
                    <td>
                        <div class="user-info">
                            <div class="fw-medium">${log.full_name}</div>
                            <small class="text-muted">${log.role}</small>
                        </div>
                    </td>
                    <td>
                        <span class="action-badge ${log.action.toLowerCase()}">${log.action}</span>
                    </td>
                    <td>
                        <div class="details-text">${log.details}</div>
                    </td>
                    <td>
                        <small class="text-muted">${log.ip}</small>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            renderPagination(data.page, data.pages, data.total);
        });
}

// Setup filter functionality
function setupFilters() {
    const fromDate = document.getElementById('fromDate');
    const toDate = document.getElementById('toDate');
    const userFilter = document.getElementById('userFilter');
    const actionFilter = document.getElementById('actionFilter');
    const resetButton = document.getElementById('resetFilters');
    
    // Auto-filter when any filter changes
    fromDate.addEventListener('change', applyFilters);
    toDate.addEventListener('change', applyFilters);
    userFilter.addEventListener('change', applyFilters);
    actionFilter.addEventListener('change', applyFilters);
    
    resetButton.addEventListener('click', function() {
        resetFilters();
        
        // Visual feedback
        this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Resetting...';
        this.disabled = true;
        
        setTimeout(() => {
            this.innerHTML = '<i class="fas fa-undo me-1"></i>Reset';
            this.disabled = false;
        }, 500);
    });
}

// Apply filters to the audit logs
function applyFilters() {
    const fromDate = document.getElementById('fromDate').value;
    const toDate = document.getElementById('toDate').value;
    const userFilter = document.getElementById('userFilter').value;
    const actionFilter = document.getElementById('actionFilter').value;
    const searchTerm = document.getElementById('searchLogs').value.toLowerCase();
    
    const rows = document.querySelectorAll('#auditLogsTableBody tr');
    let visibleCount = 0;
    
    rows.forEach(row => {
        const timestamp = row.querySelector('.timestamp .fw-medium').textContent;
        const user = row.querySelector('.user-info .fw-medium').textContent.toLowerCase();
        const userRole = row.querySelector('.user-info .text-muted').textContent.toLowerCase();
        const action = row.querySelector('.action-badge').textContent.toLowerCase();
        // const affectedData = row.querySelector('.affected-data .fw-medium').textContent.toLowerCase();
        const details = row.querySelector('.details-text').textContent.toLowerCase();
        
        // Date filtering (simplified for demo)
        let matchesDate = true;
        if (fromDate || toDate) {
            // In real implementation, would parse and compare dates
            matchesDate = true;
        }
        
        // User filtering
        const matchesUser = !userFilter || 
            user.includes(userFilter.toLowerCase()) || 
            userRole.includes(userFilter.toLowerCase());
        
        // Action filtering
        const matchesAction = !actionFilter || action === actionFilter;
        
        // Search filtering
        const matchesSearch = !searchTerm || 
            user.includes(searchTerm) ||
            userRole.includes(searchTerm) ||
            action.includes(searchTerm) ||
            // affectedData.includes(searchTerm) ||
            details.includes(searchTerm);
        
        if (matchesDate && matchesUser && matchesAction && matchesSearch) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    
    // Update showing info
    const showingInfo = document.querySelector('.showing-info');
    showingInfo.textContent = `Showing 1-${visibleCount} of 1,247 audit log entries`;
    
    console.log(`Applied filters - showing ${visibleCount} entries`);
}

// Reset all filters
function resetFilters() {
    document.getElementById('fromDate').value = '2025-01-01';
    document.getElementById('toDate').value = '2025-01-15';
    document.getElementById('userFilter').value = '';
    document.getElementById('actionFilter').value = '';
    document.getElementById('searchLogs').value = '';
    
    // Show all rows
    const rows = document.querySelectorAll('#auditLogsTableBody tr');
    rows.forEach(row => {
        row.style.display = '';
    });
    
    // Reset showing info
    const showingInfo = document.querySelector('.showing-info');
    showingInfo.textContent = 'Showing 1-8 of 1,247 audit log entries';
    
    console.log('Filters reset');
}

// Setup search functionality
function setupSearch() {
    const searchInput = document.getElementById('searchLogs');
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.trim().toLowerCase();
        
        // Apply filters automatically
        applyFilters();
        
        // Visual feedback
        if (searchTerm.length > 0) {
            this.style.borderColor = '#10b981';
            setTimeout(() => {
                this.style.borderColor = '#d1d5db';
            }, 1000);
        }
    });
    
    // Search on Enter key
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            applyFilters();
        }
    });
}

// Setup table interactions
function setupTableInteractions() {
    // Export logs button
    const exportBtn = document.querySelector('.btn-outline-primary');
    exportBtn.addEventListener('click', function() {
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
    refreshBtn.addEventListener('click', function() {
        this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Refreshing...';
        this.disabled = true;
        
        setTimeout(() => {
            loadLogs();
            this.innerHTML = '<i class="fas fa-sync me-1"></i>Refresh';
            this.disabled = false;
            console.log('Audit logs refreshed');
        }, 1500);
    });
    
    // Row click for details (optional)
    const tableRows = document.querySelectorAll('#auditLogsTableBody tr');
    tableRows.forEach(row => {
        row.addEventListener('click', function() {
            const user = this.querySelector('.user-info .fw-medium').textContent;
            const action = this.querySelector('.action-badge').textContent;
            // const affectedData = this.querySelector('.affected-data .fw-medium').textContent;
            
            // console.log(`Clicked log entry: ${user} ${action} ${affectedData}`);
            
            // Could open a modal with detailed information
            // showLogDetails(logData);
        });
    });
}

// Add interactive effects
function addInteractiveEffects() {
    // Table row hover effects
    const tableRows = document.querySelectorAll('#auditLogsTableBody tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f8f9fa';
            this.style.cursor = 'pointer';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
            this.style.cursor = '';
        });
    });
    
    // Action badge hover effects
    const actionBadges = document.querySelectorAll('.action-badge');
    actionBadges.forEach(badge => {
        badge.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.05)';
        });
        
        badge.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });
}

// Auto-refresh functionality (optional)
function setupAutoRefresh() {
    // Auto-refresh every 30 seconds
    setInterval(() => {
        loadLogs();
        console.log('Auto-refreshing audit logs...');
    }, 30000);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    loadLogs();
    initAuditLogs();
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + F to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault();
        document.getElementById('searchLogs').focus();
    }
    
    // Escape to clear search
    if (e.key === 'Escape') {
        const searchInput = document.getElementById('searchLogs');
        if (document.activeElement === searchInput) {
            searchInput.value = '';
            applyFilters();
            searchInput.blur();
        }
    }
    
    // Ctrl/Cmd + R to refresh (prevent default browser refresh)
    if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
        e.preventDefault();
        document.getElementById('refreshLogs').click();
    }
});

// Handle page visibility change for auto-refresh
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        console.log('Page hidden - pausing auto-refresh');
    } else {
        console.log('Page visible - resuming auto-refresh');
        // Could trigger immediate refresh when page becomes visible
    }
});

fromDate = document.getElementById("fromDate");
toDate = document.getElementById("toDate");

[fromDate, toDate].forEach(input => {
    if (input) {
        input.addEventListener("change", () => {
            loadLogs();
        });
    }
});

function renderPagination(current, totalPages, totalItems) {
    const container = document.querySelector(".pagination");
    const showingInfo = document.querySelector(".showing-info");

    showingInfo.textContent = `Showing ${((current-1)*perPage+1)}-${Math.min(current*perPage, totalItems)} of ${totalItems} audit log entries`;
    container.innerHTML = '';

    // Previous Button (Same as your code)
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${current === 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `<a class="page-link" href="#">Previous</a>`;
    prevLi.addEventListener('click', e => { e.preventDefault(); if (current > 1) loadLogs(current - 1); });
    container.appendChild(prevLi);

    // Dynamic Page Numbers (Logic to show max 5 buttons)
    const windowSize = 2; // Number of pages before/after current
    let start = Math.max(1, current - windowSize);
    let end = Math.min(totalPages, current + windowSize);

    for (let i = start; i <= end; i++) {
        const li = document.createElement('li');
        li.className = `page-item ${i === current ? 'active' : ''}`;
        li.innerHTML = `<a class="page-link" href="#">${i}</a>`;
        li.addEventListener('click', e => { e.preventDefault(); loadLogs(i); });
        container.appendChild(li);
    }

    // Next Button (Same as your code)
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${current === totalPages ? 'disabled' : ''}`;
    nextLi.innerHTML = `<a class="page-link" href="#">Next</a>`;
    nextLi.addEventListener('click', e => { e.preventDefault(); if (current < totalPages) loadLogs(current + 1); });
    container.appendChild(nextLi);
}
