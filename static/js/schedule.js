let currentPage = 1;
let searchTimeout = null;

function initScheduleManagement() {
    setupFilters();
    setupScheduleActions();
    setupModal();
    setupQuickShifts();
    loadSchedules();
}

function getFilterValues() {
    return {
        search: document.getElementById('scheduleSearch')?.value.trim() || '',
        status: document.getElementById('statusFilter')?.value ?? 'active',
        role: document.getElementById('roleFilter')?.value || '',
        perPage: parseInt(document.getElementById('pageSizeSelect')?.value, 10) || 25
    };
}

function buildQueryString() {
    const filters = getFilterValues();
    const params = new URLSearchParams();

    params.set('page', currentPage);
    params.set('per_page', filters.perPage);

    if (filters.search) params.set('search', filters.search);
    if (filters.status) params.set('status', filters.status);
    if (filters.role) params.set('role', filters.role);

    return params.toString();
}

function setupFilters() {
    const searchInput = document.getElementById('scheduleSearch');
    const statusSelect = document.getElementById('statusFilter');
    const roleSelect = document.getElementById('roleFilter');
    const pageSizeSelect = document.getElementById('pageSizeSelect');
    const clearBtn = document.getElementById('clearFilters');

    if (searchInput) {
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentPage = 1;
                loadSchedules();
            }, 300);
        });
    }

    if (statusSelect) {
        statusSelect.addEventListener('change', () => {
            currentPage = 1;
            loadSchedules();
        });
    }

    if (roleSelect) {
        roleSelect.addEventListener('change', () => {
            currentPage = 1;
            loadSchedules();
        });
    }

    if (pageSizeSelect) {
        pageSizeSelect.addEventListener('change', () => {
            currentPage = 1;
            loadSchedules();
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            if (statusSelect) statusSelect.value = 'active';
            if (roleSelect) roleSelect.value = '';
            if (pageSizeSelect) pageSizeSelect.value = '25';
            currentPage = 1;
            loadSchedules();
        });
    }
}

function updatePagination(total, page, perPage) {
    const pagination = document.getElementById('schedulePagination');
    const showingInfo = document.getElementById('scheduleShowingInfo');
    if (!pagination || !showingInfo) return;

    pagination.innerHTML = '';

    const totalPages = Math.max(1, Math.ceil(total / perPage));
    const startItem = total === 0 ? 0 : (page - 1) * perPage + 1;
    const endItem = Math.min(total, page * perPage);
    showingInfo.textContent = `Showing ${startItem}-${endItem} of ${total} student assistants`;

    const createPageButton = (label, targetPage, disabled = false, active = false) => {
        const li = document.createElement('li');
        li.className = `page-item${disabled ? ' disabled' : ''}${active ? ' active' : ''}`;
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'page-link';
        button.textContent = label;
        button.disabled = disabled;
        button.addEventListener('click', () => {
            if (!disabled && currentPage !== targetPage) {
                currentPage = targetPage;
                loadSchedules();
            }
        });
        li.appendChild(button);
        return li;
    };

    pagination.appendChild(createPageButton('Previous', Math.max(1, page - 1), page === 1));

    const windowSize = 5;
    let startPage = Math.max(1, page - Math.floor(windowSize / 2));
    let endPage = Math.min(totalPages, startPage + windowSize - 1);
    if (endPage - startPage < windowSize - 1) {
        startPage = Math.max(1, endPage - windowSize + 1);
    }

    for (let p = startPage; p <= endPage; p += 1) {
        pagination.appendChild(createPageButton(p, p, false, p === page));
    }

    pagination.appendChild(createPageButton('Next', Math.min(totalPages, page + 1), page === totalPages));
}

// -----------------------------------------------------------------------------
// Office Hours (7:30 AM - 8:30 PM) & Auto-complete Helpers
// -----------------------------------------------------------------------------
function calculateEndTimePlus4Hours(startTime) {
    if (!startTime) return '';
    const parts = startTime.split(':');
    if (parts.length < 2) return '';
    const h = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10);
    if (isNaN(h) || isNaN(m)) return '';

    // Add 4 hours (240 minutes)
    let totalMinutes = (h + 4) * 60 + m;

    // Cap at 8:30 PM (20:30 = 20 * 60 + 30 = 1230 minutes)
    const maxOfficeMinutes = 20 * 60 + 30;
    if (totalMinutes > maxOfficeMinutes) {
        totalMinutes = maxOfficeMinutes;
    }

    const endH = Math.floor(totalMinutes / 60);
    const endM = totalMinutes % 60;

    return `${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}`;
}

function calculateShiftHours(startStr, endStr) {
    if (!startStr || !endStr) return 0;
    const [sh, sm] = startStr.split(':').map(Number);
    const [eh, em] = endStr.split(':').map(Number);
    if (isNaN(sh) || isNaN(sm) || isNaN(eh) || isNaN(em)) return 0;
    let startMins = sh * 60 + sm;
    let endMins = eh * 60 + em;
    if (endMins < startMins) {
        endMins += 24 * 60; // Overnight shift if applicable
    }
    return Math.max(0, (endMins - startMins) / 60);
}

function updateModalWorkloadValidation() {
    const isDaily = document.getElementById('modeDaily')?.checked;
    const targetDaily = 4.0;
    const targetWeekly = 24.0;

    let weeklyTotal = 0;
    const dayDeviations = [];

    const updateBox = (dayId, boxId, hours, label) => {
        const textEl = document.getElementById(`val${dayId}Day`);
        const boxEl = document.getElementById(boxId);
        if (textEl) textEl.textContent = hours.toFixed(1);
        if (boxEl) {
            boxEl.className = 'p-2 rounded border';
            if (Math.abs(hours - targetDaily) < 0.05) {
                boxEl.classList.add('bg-success-subtle', 'border-success-subtle', 'text-success');
            } else if (hours > 0) {
                boxEl.classList.add('bg-warning-subtle', 'border-warning-subtle', 'text-warning');
            } else {
                boxEl.classList.add('bg-white', 'text-muted');
            }
        }
        if (Math.abs(hours - targetDaily) >= 0.05) {
            dayDeviations.push(`${label}: ${hours.toFixed(1)}h`);
        }
    };

    if (!isDaily) {
        // --- Block Mode ---
        const blocks = ['mw', 'tth', 'fri', 'sat'];
        const dayTotals = { mw: 0, tth: 0, fri: 0, sat: 0 };

        blocks.forEach(block => {
            const startVal = document.getElementById(`${block}In`)?.value;
            const endVal = document.getElementById(`${block}Out`)?.value;
            dayTotals[block] += calculateShiftHours(startVal, endVal);
        });

        document.querySelectorAll('#brokenScheduleContainer .broken-schedule-item').forEach(item => {
            const day = item.querySelector('.broken-day')?.value;
            const inputs = item.querySelectorAll('input[type="time"]');
            if (day && dayTotals[day] !== undefined && inputs[0]?.value && inputs[1]?.value) {
                dayTotals[day] += calculateShiftHours(inputs[0].value, inputs[1].value);
            }
        });

        weeklyTotal = (dayTotals.mw * 2) + (dayTotals.tth * 2) + (dayTotals.fri * 1) + (dayTotals.sat * 1);

        updateBox('Mw', 'valBoxMw', dayTotals.mw, 'MW');
        updateBox('Tth', 'valBoxTth', dayTotals.tth, 'TTh');
        updateBox('Fri', 'valBoxFri', dayTotals.fri, 'Fri');
        updateBox('Sat', 'valBoxSat', dayTotals.sat, 'Sat');
    } else {
        // --- Daily Mode (Mon-Sat) ---
        const days = ['mon', 'tue', 'wed', 'thu', 'dailyFri', 'dailySat'];
        const dayKeyMap = {
            mon: 'mon',
            tue: 'tue',
            wed: 'wed',
            thu: 'thu',
            dailyFri: 'fri',
            dailySat: 'sat'
        };
        const dayTotals = { mon: 0, tue: 0, wed: 0, thu: 0, fri: 0, sat: 0 };

        days.forEach(d => {
            const startVal = document.getElementById(`${d}In`)?.value;
            const endVal = document.getElementById(`${d}Out`)?.value;
            const targetKey = dayKeyMap[d];
            dayTotals[targetKey] += calculateShiftHours(startVal, endVal);
        });

        document.querySelectorAll('#brokenScheduleContainer .broken-schedule-item').forEach(item => {
            const day = item.querySelector('.broken-day')?.value;
            const inputs = item.querySelectorAll('input[type="time"]');
            if (day && dayTotals[day] !== undefined && inputs[0]?.value && inputs[1]?.value) {
                dayTotals[day] += calculateShiftHours(inputs[0].value, inputs[1].value);
            }
        });

        weeklyTotal = dayTotals.mon + dayTotals.tue + dayTotals.wed + dayTotals.thu + dayTotals.fri + dayTotals.sat;

        updateBox('Mon', 'valBoxMon', dayTotals.mon, 'Mon');
        updateBox('Tue', 'valBoxTue', dayTotals.tue, 'Tue');
        updateBox('Wed', 'valBoxWed', dayTotals.wed, 'Wed');
        updateBox('Thu', 'valBoxThu', dayTotals.thu, 'Thu');
        updateBox('DailyFri', 'valBoxDailyFri', dayTotals.fri, 'Fri');
        updateBox('DailySat', 'valBoxDailySat', dayTotals.sat, 'Sat');
    }

    // Weekly Total Badge
    const totalEl = document.getElementById('valWeeklyTotal');
    const badgeEl = document.getElementById('valWeeklyBadge');
    if (totalEl) totalEl.textContent = weeklyTotal.toFixed(1);

    const isCompliant = (Math.abs(weeklyTotal - targetWeekly) < 0.05 && dayDeviations.length === 0);

    if (badgeEl) {
        badgeEl.className = 'badge border font-mono';
        if (isCompliant) {
            badgeEl.classList.add('bg-success-subtle', 'text-success', 'border-success-subtle');
        } else if (weeklyTotal > 0) {
            badgeEl.classList.add('bg-warning-subtle', 'text-warning', 'border-warning-subtle');
        } else {
            badgeEl.classList.add('bg-white', 'text-dark');
        }
    }

    // Advisory Notice
    const noticeContainer = document.getElementById('valNoticeContainer');
    if (noticeContainer) {
        if (isCompliant) {
            noticeContainer.innerHTML = `
                <div class="alert alert-success d-flex align-items-center py-2 px-3 mb-0 small">
                    <i class="bi bi-check-circle-fill me-2 fs-6"></i>
                    <span><strong>Standard Compliant:</strong> Exactly 4.0 hrs everyday (24.0 hrs weekly total).</span>
                </div>
            `;
        } else if (weeklyTotal === 0) {
            noticeContainer.innerHTML = `
                <div class="text-muted small text-center py-1">
                    <i class="bi bi-info-circle me-1"></i> Standard GIA allocation is 4.0 hrs everyday (24.0 hrs total for the week).
                </div>
            `;
        } else {
            const diff = weeklyTotal - targetWeekly;
            const diffText = diff > 0 
                ? `+${diff.toFixed(1)} hrs over target` 
                : `${Math.abs(diff).toFixed(1)} hrs under target`;

            noticeContainer.innerHTML = `
                <div class="alert alert-warning d-flex align-items-start py-2 px-3 mb-0 small">
                    <i class="bi bi-exclamation-triangle-fill me-2 fs-6 flex-shrink-0 text-warning mt-1"></i>
                    <div>
                        <div><strong>Advisory (${diffText}):</strong> Standard is 4.0h everyday / 24.0h weekly. 
                        <span class="text-dark fw-medium">${dayDeviations.join(', ')}</span>.</div>
                        <div class="text-muted mt-1" style="font-size: 0.75rem;">You may still save this schedule; this validator is advisory.</div>
                    </div>
                </div>
            `;
        }
    }
}

// -----------------------------------------------------------------------------
// Load & Render Weekly Matrix
// -----------------------------------------------------------------------------
async function loadSchedules() {
    const tbody = document.getElementById('scheduleTableBody');
    const showingInfo = document.getElementById('scheduleShowingInfo');
    const tableContainer = tbody ? tbody.closest('.table-responsive') : null;
    const hasExistingRows = tbody && tbody.querySelectorAll('tr').length > 0 && !tbody.querySelector('.spinner-border');

    if (tableContainer) {
        tableContainer.classList.add('table-loading-container');
    }

    if (hasExistingRows) {
        // Keep existing rows visible to preserve table height while paginating
        if (tableContainer) {
            tableContainer.classList.add('is-loading-data');
            let overlay = tableContainer.querySelector('.table-loading-overlay');
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.className = 'table-loading-overlay';
                overlay.innerHTML = `
                    <div class="table-loading-badge">
                        <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
                        <span>Loading schedules...</span>
                    </div>
                `;
                tableContainer.appendChild(overlay);
            }
        }
    } else {
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-5 text-muted">
                        <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                        Loading schedule matrix...
                    </td>
                </tr>
            `;
        }
    }

    if (showingInfo && !hasExistingRows) {
        showingInfo.textContent = 'Loading schedules...';
    }

    try {
        const queryString = buildQueryString();
        const res = await fetch(`/api/get-schedules?${queryString}`);
        const data = await res.json();

        const users = data.users || [];
        const schedules = data.schedules || [];
        const total = typeof data.total === 'number' ? data.total : users.length;
        const page = data.page || currentPage;
        const perPage = data.per_page || 25;

        updatePagination(total, page, perPage);

        const scheduleMap = {};
        schedules.forEach(s => {
            if (!scheduleMap[s.user_id]) scheduleMap[s.user_id] = {};
            scheduleMap[s.user_id][s.day] = s;
        });

        const blocks = ['mw', 'tth', 'fri', 'sat'];
        if (!tbody) return;
        tbody.innerHTML = '';

        if (users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center py-5 text-muted">No student assistants found matching the filters.</td></tr>';
            return;
        }

        users.forEach(u => {
            const row = document.createElement('tr');
            
            // Format status badge if inactive
            const isInactive = u.status === 'inactive';
            const statusBadge = isInactive 
                ? '<span class="badge bg-light text-secondary border ms-2" style="font-size: 0.65rem;">Inactive</span>' 
                : '';
            
            const labText = u.laboratory 
                ? `<div class="text-muted small" style="font-size: 0.75rem;"><i class="bi bi-geo-alt me-1"></i>${u.laboratory}</div>` 
                : '';

            const userSchedMap = scheduleMap[u.user_id] || {};
            const isCustomDaily = Boolean(
                userSchedMap['mon'] || userSchedMap['tue'] || userSchedMap['wed'] || userSchedMap['thu']
            );
            const dailyScheduleBadge = isCustomDaily
                ? '<span class="badge bg-info-subtle text-info border border-info-subtle ms-2" style="font-size: 0.65rem;" title="Individual daily schedule assigned"><i class="bi bi-calendar3 me-1"></i>Daily</span>'
                : '';

            let rowHTML = `
                <td class="ps-4">
                    <div class="d-flex align-items-center">
                        <div class="user-avatar me-3">${(u.first_name[0] || '')}${(u.last_name[0] || '')}</div>
                        <div>
                            <div class="user-name d-flex align-items-center">
                                ${u.first_name} ${u.last_name}
                                ${statusBadge}
                                ${dailyScheduleBadge}
                            </div>
                            <div class="user-email text-muted small">${u.user_id}</div>
                            ${labText}
                        </div>
                    </div>
                </td>
            `;

            let userWeeklyHours = 0;

            if (!isCustomDaily) {
                // Standard block rendering: MW, TTh, Fri, Sat
                blocks.forEach(block => {
                    const s = userSchedMap[block];
                    const hasPrimary = Boolean(s && s.start_time && s.end_time);
                    const hasSplit = Boolean(s && (s.is_split_shift || (s.split_start_time && s.split_end_time)) && s.split_start_time && s.split_end_time);

                    const dailyHours = (s && typeof s.daily_hours === 'number') ? s.daily_hours : 0;
                    const multiplier = (block === 'mw' || block === 'tth') ? 2 : 1;
                    userWeeklyHours += dailyHours * multiplier;

                    let cellContent = '';
                    if (!hasPrimary && !hasSplit) {
                        cellContent = '<span class="text-muted small">-</span>';
                    } else {
                        if (hasPrimary) {
                            cellContent += `<div class="time-display fw-medium">${s.start_time} - ${s.end_time}</div>`;
                        }
                        if (hasSplit) {
                            cellContent += `
                                <div>
                                    <span class="split-display" title="Split Shift">
                                        <i class="bi bi-segmented-nav me-1"></i>${s.split_start_time} - ${s.split_end_time}
                                    </span>
                                </div>
                            `;
                        }
                        if (dailyHours > 0) {
                            cellContent += `<div class="text-muted small font-mono mt-1" style="font-size: 0.725rem;">${dailyHours.toFixed(1)}h/day</div>`;
                        }
                    }

                    rowHTML += `
                        <td>
                            <div class="schedule-time text-center">
                                ${cellContent}
                            </div>
                        </td>
                    `;
                });
            } else {
                // Custom daily rendering within the 4 columns
                // 1. Mon & Wed (MW column)
                const renderSubDay = (label, s) => {
                    if (!s || (!s.start_time && !s.split_start_time)) {
                        return `<div class="text-muted small">${label}: Off</div>`;
                    }
                    let txt = `<span class="fw-semibold text-dark">${label}:</span> ${s.start_time || ''}${s.end_time ? ' - ' + s.end_time : ''}`;
                    if (s.is_split_shift && s.split_start_time) {
                        txt += ` <span class="text-primary small" title="Split shift">(+split)</span>`;
                    }
                    return `<div class="small">${txt}</div>`;
                };

                const monS = userSchedMap['mon'];
                const wedS = userSchedMap['wed'];
                const tueS = userSchedMap['tue'];
                const thuS = userSchedMap['thu'];
                const friS = userSchedMap['fri'];
                const satS = userSchedMap['sat'];

                userWeeklyHours += (monS?.daily_hours || 0) + (tueS?.daily_hours || 0) + (wedS?.daily_hours || 0) +
                                   (thuS?.daily_hours || 0) + (friS?.daily_hours || 0) + (satS?.daily_hours || 0);

                rowHTML += `
                    <td>
                        <div class="schedule-time text-center">
                            ${renderSubDay('M', monS)}
                            ${renderSubDay('W', wedS)}
                        </div>
                    </td>
                    <td>
                        <div class="schedule-time text-center">
                            ${renderSubDay('T', tueS)}
                            ${renderSubDay('Th', thuS)}
                        </div>
                    </td>
                    <td>
                        <div class="schedule-time text-center">
                            ${renderSubDay('F', friS)}
                        </div>
                    </td>
                    <td>
                        <div class="schedule-time text-center">
                            ${renderSubDay('Sa', satS)}
                        </div>
                    </td>
                `;
            }

            // Weekly Total Column
            let weeklyBadge = '';
            if (Math.abs(userWeeklyHours - 24.0) < 0.05) {
                weeklyBadge = `<span class="badge bg-success-subtle text-success border border-success-subtle font-mono fw-semibold" title="Meets standard 24 hrs/week"><i class="bi bi-check-circle me-1"></i>24.0 hrs</span>`;
            } else if (userWeeklyHours > 0) {
                weeklyBadge = `<span class="badge bg-warning-subtle text-warning border border-warning-subtle font-mono fw-semibold" title="Standard is 24 hrs/week (4 hrs everyday)"><i class="bi bi-exclamation-circle me-1"></i>${userWeeklyHours.toFixed(1)} hrs</span>`;
            } else {
                weeklyBadge = `<span class="badge bg-light text-muted border font-mono">0.0 hrs</span>`;
            }

            rowHTML += `
                <td class="text-center">
                    ${weeklyBadge}
                </td>
            `;

            rowHTML += `
                <td class="text-center">
                    <button class="btn btn-sm btn-outline-primary edit-sched-btn" data-user-id="${u.user_id}" title="Edit Schedule">
                        <i class="bi bi-pencil-square"></i>
                    </button>
                </td>
            `;

            row.innerHTML = rowHTML;
            tbody.appendChild(row);
        });
    } catch (err) {
        console.error('Error loading schedules:', err);
        const tbody = document.getElementById('scheduleTableBody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center py-5 text-danger">Unable to load schedules. Please click Refresh.</td></tr>';
        }
    } finally {
        if (tableContainer) {
            tableContainer.classList.remove('is-loading-data');
        }
    }
}

// -----------------------------------------------------------------------------
// Quick Shifts & Day Clearing
// -----------------------------------------------------------------------------
function setupQuickShifts() {
    // Quick Shift Preset Buttons
    document.addEventListener('click', e => {
        const btn = e.target.closest('.quick-shift-btn');
        if (!btn) return;
        const block = btn.getAttribute('data-block');
        const start = btn.getAttribute('data-start');
        const end = btn.getAttribute('data-end');

        const inEl = document.getElementById(`${block}In`);
        const outEl = document.getElementById(`${block}Out`);

        if (inEl && outEl) {
            inEl.value = start;
            outEl.value = end;
            updateModalWorkloadValidation();
        }
    });

    // Clear Single Day Block Buttons
    document.addEventListener('click', e => {
        const btn = e.target.closest('.clear-block-btn');
        if (!btn) return;
        const block = btn.getAttribute('data-block');
        const inEl = document.getElementById(`${block}In`);
        const outEl = document.getElementById(`${block}Out`);

        if (inEl && outEl) {
            inEl.value = '';
            outEl.value = '';
            updateModalWorkloadValidation();
        }
    });
}

// -----------------------------------------------------------------------------
// Edit Modal Setup & Actions
// -----------------------------------------------------------------------------
function setupModal() {
    const saveBtn = document.getElementById('saveSchedBtn');
    const addBrokenBtn = document.getElementById('addBrokenSchedule');

    if (addBrokenBtn) {
        addBrokenBtn.addEventListener('click', () => {
            addBrokenScheduleRow();
            updateModalWorkloadValidation();
        });
    }

    // Auto-complete End Time with 4 hours when Start Time is input/changed,
    // while keeping End Time fully editable by the user.
    ['mw', 'tth', 'fri', 'sat', 'mon', 'tue', 'wed', 'thu', 'dailyFri', 'dailySat'].forEach(block => {
        const inEl = document.getElementById(`${block}In`);
        const outEl = document.getElementById(`${block}Out`);
        if (inEl && outEl) {
            const handleStartChange = function () {
                if (inEl.value) {
                    outEl.value = calculateEndTimePlus4Hours(inEl.value);
                }
                updateModalWorkloadValidation();
            };

            inEl.addEventListener('input', handleStartChange);
            inEl.addEventListener('change', handleStartChange);

            // User can still freely edit End Time directly
            outEl.addEventListener('input', updateModalWorkloadValidation);
            outEl.addEventListener('change', updateModalWorkloadValidation);
        }
    });

    // Schedule Mode Switch Listener (Block vs Custom Daily)
    const modeBlockRadio = document.getElementById('modeBlock');
    const modeDailyRadio = document.getElementById('modeDaily');
    const blockContainer = document.getElementById('blockModeContainer');
    const dailyContainer = document.getElementById('dailyModeContainer');
    const valBreakdownBlock = document.getElementById('valBreakdownBlock');
    const valBreakdownDaily = document.getElementById('valBreakdownDaily');

    const handleModeSwitch = () => {
        const isDaily = modeDailyRadio && modeDailyRadio.checked;
        if (isDaily) {
            blockContainer?.classList.add('d-none');
            dailyContainer?.classList.remove('d-none');
            valBreakdownBlock?.classList.add('d-none');
            valBreakdownDaily?.classList.remove('d-none');
        } else {
            dailyContainer?.classList.add('d-none');
            blockContainer?.classList.remove('d-none');
            valBreakdownDaily?.classList.add('d-none');
            valBreakdownBlock?.classList.remove('d-none');
        }
        updateModalWorkloadValidation();
    };

    if (modeBlockRadio) modeBlockRadio.addEventListener('change', handleModeSwitch);
    if (modeDailyRadio) modeDailyRadio.addEventListener('change', handleModeSwitch);

    // Save Action (Advisory: always allows save without constraining user)
    if (saveBtn) {
        saveBtn.addEventListener('click', async function () {
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Saving...';

            const userId = document.getElementById('userId').value;
            const isDaily = modeDailyRadio && modeDailyRadio.checked;
            const schedule_mode = isDaily ? 'daily' : 'block';

            // Collect Shifts based on active mode
            let schedules = [];
            if (!isDaily) {
                schedules = ['mw', 'tth', 'fri', 'sat'].map(block => ({
                    day: block,
                    start_time: document.getElementById(`${block}In`)?.value || null,
                    end_time: document.getElementById(`${block}Out`)?.value || null
                }));
            } else {
                const dailyInputs = [
                    { day: 'mon', id: 'mon' },
                    { day: 'tue', id: 'tue' },
                    { day: 'wed', id: 'wed' },
                    { day: 'thu', id: 'thu' },
                    { day: 'fri', id: 'dailyFri' },
                    { day: 'sat', id: 'dailySat' }
                ];
                schedules = dailyInputs.map(item => ({
                    day: item.day,
                    start_time: document.getElementById(`${item.id}In`)?.value || null,
                    end_time: document.getElementById(`${item.id}Out`)?.value || null
                }));
            }

            // Collect Broken Shifts
            const brokenSched = [];
            document.querySelectorAll('#brokenScheduleContainer .broken-schedule-item').forEach(item => {
                const day = item.querySelector('.broken-day').value;
                const inputs = item.querySelectorAll('input[type="time"]');
                if (inputs[0]?.value && inputs[1]?.value) {
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
                    body: JSON.stringify({ schedule_mode, schedules, brokenSched })
                });

                if (res.ok) {
                    bootstrap.Modal.getInstance(document.getElementById('scheduleEditModal')).hide();
                    loadSchedules();
                    showAlert('success', 'Schedule updated successfully.');
                } else {
                    const errData = await res.json();
                    showAlert('danger', errData.error || 'Failed to update schedule.');
                }
            } catch (err) {
                console.error(err);
                showAlert('danger', 'Failed to update schedule. Please try again.');
            } finally {
                this.disabled = false;
                this.innerHTML = '<i class="bi bi-check-lg"></i> Save Schedule';
            }
        });
    }
}

function addBrokenScheduleRow(day = 'mw', start = '', end = '') {
    const container = document.getElementById('brokenScheduleContainer');
    const template = document.getElementById('brokenScheduleTemplate');
    if (!container || !template) return;

    const clone = template.firstElementChild.cloneNode(true);
    clone.classList.remove('d-none');
    
    const daySelect = clone.querySelector('.broken-day');
    if (daySelect) daySelect.value = day;

    const timeInputs = clone.querySelectorAll('input[type="time"]');
    if (timeInputs.length >= 2) {
        timeInputs[0].value = start;
        timeInputs[1].value = end;

        // Auto-complete +4 hours on split start time input while allowing user to edit
        const handleSplitStartChange = function () {
            if (timeInputs[0].value) {
                timeInputs[1].value = calculateEndTimePlus4Hours(timeInputs[0].value);
            }
            updateModalWorkloadValidation();
        };

        timeInputs[0].addEventListener('input', handleSplitStartChange);
        timeInputs[0].addEventListener('change', handleSplitStartChange);

        timeInputs[1].addEventListener('input', updateModalWorkloadValidation);
        timeInputs[1].addEventListener('change', updateModalWorkloadValidation);
    }

    if (daySelect) {
        daySelect.addEventListener('change', updateModalWorkloadValidation);
    }

    const removeBtn = clone.querySelector('.remove-broken-schedule');
    if (removeBtn) {
        removeBtn.addEventListener('click', () => {
            clone.remove();
            updateModalWorkloadValidation();
        });
    }

    container.appendChild(clone);
}

// Global listener for Edit buttons on table rows
document.addEventListener('click', e => {
    const editBtn = e.target.closest('.edit-sched-btn');
    if (!editBtn) return;

    const userId = editBtn.getAttribute('data-user-id');
    if (!userId) return;

    const originalBtnHTML = editBtn.innerHTML;
    editBtn.disabled = true;
    editBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';

    fetch(`/api/get-schedule/${userId}`)
        .then(res => res.json())
        .then(data => {
            const user = data.user;
            const scheds = data.schedules || [];

            const editWho = document.getElementById('editWho');
            if (editWho) editWho.textContent = user.full_name;

            const userIdInput = document.getElementById('userId');
            if (userIdInput) userIdInput.value = user.user_id;

            // Detect whether user has custom daily schedules
            const hasDaily = scheds.some(s => ['mon', 'tue', 'wed', 'thu'].includes(s.day.toLowerCase()) && (s.start_time || s.split_start_time));
            const modeBlockRadio = document.getElementById('modeBlock');
            const modeDailyRadio = document.getElementById('modeDaily');
            const blockContainer = document.getElementById('blockModeContainer');
            const dailyContainer = document.getElementById('dailyModeContainer');
            const valBreakdownBlock = document.getElementById('valBreakdownBlock');
            const valBreakdownDaily = document.getElementById('valBreakdownDaily');

            if (hasDaily) {
                if (modeDailyRadio) modeDailyRadio.checked = true;
                blockContainer?.classList.add('d-none');
                dailyContainer?.classList.remove('d-none');
                valBreakdownBlock?.classList.add('d-none');
                valBreakdownDaily?.classList.remove('d-none');
            } else {
                if (modeBlockRadio) modeBlockRadio.checked = true;
                dailyContainer?.classList.add('d-none');
                blockContainer?.classList.remove('d-none');
                valBreakdownDaily?.classList.add('d-none');
                valBreakdownBlock?.classList.remove('d-none');
            }

            // Reset all inputs first without triggering change events
            ['mw', 'tth', 'fri', 'sat', 'mon', 'tue', 'wed', 'thu', 'dailyFri', 'dailySat'].forEach(id => {
                const inEl = document.getElementById(`${id}In`);
                const outEl = document.getElementById(`${id}Out`);
                if (inEl) inEl.value = '';
                if (outEl) outEl.value = '';
            });

            // Populate Main Inputs with existing values from database
            scheds.forEach(s => {
                const dayKey = s.day.toLowerCase();
                const inputIds = [dayKey];
                if (dayKey === 'fri') inputIds.push('dailyFri');
                if (dayKey === 'sat') inputIds.push('dailySat');

                inputIds.forEach(id => {
                    const inEl = document.getElementById(`${id}In`);
                    const outEl = document.getElementById(`${id}Out`);
                    if (inEl && outEl) {
                        inEl.value = s.start_time || '';
                        outEl.value = s.end_time || '';
                    }
                });
            });

            // Populate Broken Schedules
            const brokenContainer = document.getElementById('brokenScheduleContainer');
            if (brokenContainer) {
                brokenContainer.innerHTML = '';
                scheds.forEach(s => {
                    if (s.is_split_shift && s.split_start_time) {
                        addBrokenScheduleRow(s.day, s.split_start_time, s.split_end_time);
                    }
                });
            }

            // Update live workload validation
            updateModalWorkloadValidation();

            new bootstrap.Modal(document.getElementById('scheduleEditModal')).show();
        })
        .catch(err => {
            console.error('Error fetching schedule:', err);
            showAlert('danger', 'Unable to fetch user schedule.');
        })
        .finally(() => {
            editBtn.disabled = false;
            editBtn.innerHTML = originalBtnHTML;
        });
});

function setupScheduleActions() {
    // Clear All
    const confirmClearBtn = document.getElementById('confirmClear');
    if (confirmClearBtn) {
        confirmClearBtn.addEventListener('click', async function () {
            const originalHTML = confirmClearBtn.innerHTML;
            confirmClearBtn.disabled = true;
            confirmClearBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Clearing...';

            try {
                const res = await fetch('/api/purge-schedules', { method: 'POST' });
                if (res.ok) {
                    bootstrap.Modal.getInstance(document.getElementById('clearConfirmModal')).hide();
                    loadSchedules();
                    showAlert('success', 'All schedules have been cleared.');
                } else {
                    showAlert('danger', 'Failed to clear schedules.');
                }
            } catch (err) {
                console.error(err);
                showAlert('danger', 'Error connecting to server.');
            } finally {
                confirmClearBtn.disabled = false;
                confirmClearBtn.innerHTML = originalHTML;
            }
        });
    }

    // Refresh
    const refreshBtn = document.getElementById('refreshScheduleBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => loadSchedules());
    }
}

document.addEventListener('DOMContentLoaded', initScheduleManagement);
