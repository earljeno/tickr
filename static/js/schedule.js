function initScheduleManagement() {
    loadSchedules();
    setupSearch();
    setupScheduleActions();
    setupModal();
    addInteractiveEffects();
}

// Search functionality
function setupSearch() {
    const searchInput = document.getElementById('scheduleSearch');
    if (!searchInput) return;

    searchInput.addEventListener('input', function () {
        const searchTerm = this.value.trim().toLowerCase();
        
        // Basic filtering logic
        const rows = document.querySelectorAll('#scheduleTableBody tr');
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(searchTerm) ? '' : 'none';
        });

        if (searchTerm.length > 0) {
            this.style.borderColor = '#10b981';
            setTimeout(() => { this.style.borderColor = '#d1d5db'; }, 1000);
        }
    });
}

async function loadSchedules() {
    try {
        const res = await fetch(`/api/get-schedules`);
        const data = await res.json();

        const users = data.users;
        const schedules = data.schedules;

        const scheduleMap = {};
        schedules.forEach(s => {
            if (!scheduleMap[s.user_id]) scheduleMap[s.user_id] = {};
            // Store the time range for the specific block
            scheduleMap[s.user_id][s.day] = s.start_time ? `${s.start_time} - ${s.end_time}` : '-';
        });

        // New block identifiers
        const blocks = ['mw', 'tth', 'fri', 'sat'];
        const tbody = document.getElementById('scheduleTableBody');
        tbody.innerHTML = '';

        users.forEach(u => {
            const row = document.createElement('tr');
            let rowHTML = `
                <td class="ps-4">
                    <div class="d-flex align-items-center">
                        <div class="user-avatar me-3">${u.first_name[0]}${u.last_name[0]}</div>
                        <div>
                            <div class="user-name">${u.first_name} ${u.last_name}</div>
                            <div class="user-email text-muted small">${u.user_id}</div>
                        </div>
                    </div>
                </td>
            `;

            blocks.forEach(block => {
                const timeStr = scheduleMap[u.user_id]?.[block] || '-';
                rowHTML += `
                    <td>
                        <div class="schedule-time text-center">
                            <div class="time-display fw-medium">${timeStr}</div>
                        </div>
                    </td>
                `;
            });

            rowHTML += `
                <td class="text-center">
                    <button class="btn btn-sm btn-outline-primary edit-sched-btn" data-user-id="${u.user_id}">
                        <i class="fas fa-edit"></i>
                    </button>
                </td>
            `;

            row.innerHTML = rowHTML;
            tbody.appendChild(row);
        });
    } catch (err) {
        console.error('Error loading schedules:', err);
    }
}

// Global listener for Edit buttons
document.getElementById('scheduleTableBody').addEventListener('click', e => {
    const editBtn = e.target.closest('.edit-sched-btn');
    if (!editBtn) return;

    const userId = editBtn.getAttribute('data-user-id');
    
    fetch(`/api/get-schedule/${userId}`)
        .then(res => res.json())
        .then(data => {
            const user = data.user;
            const scheds = data.schedules || [];

            document.getElementById('editWho').textContent = user.full_name;
            document.getElementById('userId').value = user.user_id;

            // Reset all inputs first
            ['mw', 'tth', 'fri', 'sat'].forEach(block => {
                document.getElementById(`${block}In`).value = '';
                document.getElementById(`${block}Out`).value = '';
            });

            // Populate Main Inputs
            scheds.forEach(s => {
                const block = s.day; // 'mw', 'tth', 'fri', 'sat'
                if (document.getElementById(`${block}In`)) {
                    document.getElementById(`${block}In`).value = s.start_time || '';
                    document.getElementById(`${block}Out`).value = s.end_time || '';
                }
            });

            // Populate Broken Schedules
            const brokenContainer = document.getElementById('brokenScheduleContainer');
            brokenContainer.innerHTML = '';
            
            scheds.forEach(s => {
                if (s.is_split_shift && s.split_start_time) {
                    addBrokenScheduleRow(s.day, s.split_start_time, s.split_end_time);
                }
            });

            new bootstrap.Modal(document.getElementById('scheduleEditModal')).show();
        });
});

function addBrokenScheduleRow(day = 'mw', start = '', end = '') {
    const container = document.getElementById('brokenScheduleContainer');
    const template = document.getElementById('brokenScheduleTemplate');
    const clone = template.firstElementChild.cloneNode(true);
    
    clone.classList.remove('d-none');
    clone.querySelector('.broken-day').value = day;
    
    const timeInputs = clone.querySelectorAll('input[type="time"]');
    timeInputs[0].value = start;
    timeInputs[1].value = end;

    clone.querySelector('.remove-broken-schedule').addEventListener('click', () => clone.remove());
    container.appendChild(clone);
}

function setupScheduleActions() {
    // Clear All
    document.getElementById('confirmClear').addEventListener('click', async function() {
        const res = await fetch('/api/purge-schedules', { method: 'POST' });
        if (res.ok) {
            bootstrap.Modal.getInstance(document.getElementById('clearConfirmModal')).hide();
            loadSchedules();
            showAlert('success', 'All schedules have been cleared.');
        }
    });

    // Refresh
    const refreshBtn = document.querySelector('.btn-outline-secondary');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => loadSchedules());
    }
}

function setupModal() {
    const saveBtn = document.getElementById('saveSchedBtn');
    const addBrokenBtn = document.getElementById('addBrokenSchedule');

    addBrokenBtn.addEventListener('click', () => addBrokenScheduleRow());

    saveBtn.addEventListener('click', async function() {
        this.disabled = true;
        this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';

        const userId = document.getElementById('userId').value;
        
        // Collect Main Blocks
        const schedules = ['mw', 'tth', 'fri', 'sat'].map(block => ({
            day: block,
            start_time: document.getElementById(`${block}In`).value || null,
            end_time: document.getElementById(`${block}Out`).value || null
        }));

        // Collect Broken Shifts
        const brokenSched = [];
        document.querySelectorAll('#brokenScheduleContainer .broken-schedule-item').forEach(item => {
            const day = item.querySelector('.broken-day').value;
            const inputs = item.querySelectorAll('input[type="time"]');
            if (inputs[0].value && inputs[1].value) {
                brokenSched.push({
                    day: day,
                    split_start_time: inputs[0].value,
                    split_end_time: inputs[1].value
                });
            }
        });

        try {
            const res = await fetch(`/api/update-schedule/${userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ schedules, brokenSched })
            });

            if (res.ok) {
                bootstrap.Modal.getInstance(document.getElementById('scheduleEditModal')).hide();
                loadSchedules();
                showAlert('success', 'Schedule updated successfully.');
            }
        } catch (err) {
            console.error(err);
            showAlert('danger', 'Failed to update schedule. Please try again.');
        } finally {
            this.disabled = false;
            this.innerHTML = 'Save Changes';
        }
    });
}

function addInteractiveEffects() {
    // Table row hover effects
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function () {
            this.style.backgroundColor = '#f8f9fa';
        });

        row.addEventListener('mouseleave', function () {
            this.style.backgroundColor = '';
        });
    });
}

document.addEventListener('DOMContentLoaded', initScheduleManagement);