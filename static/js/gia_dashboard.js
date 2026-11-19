/**
 * Tickr - GIA Dashboard Controller
 * Real-time clocking, live attendance tracking, monthly trend visualization, and schedule view.
 */

const clockBtn = document.getElementById("clockBtn");
const clockBtnLabel = document.getElementById("clockBtnLabel");
const statusBadge = document.getElementById("statusBadge");
const statusText = document.getElementById("statusText");
const currentTimeDisplay = document.getElementById("currentTime");
const currentDateDisplay = document.getElementById("currentDate");
const activeShiftNotice = document.getElementById("activeShiftNotice");
const shiftStartTimeEl = document.getElementById("shiftStartTime");
const activeShiftDurationEl = document.getElementById("activeShiftDuration");

const successModalEl = document.getElementById("clockSuccessModal");
const errorModalEl = document.getElementById("clockErrorModal");
const successModal = successModalEl ? new bootstrap.Modal(successModalEl) : null;
const errorModal = errorModalEl ? new bootstrap.Modal(errorModalEl) : null;

const monthFilter = document.getElementById("monthFilter");

let isClockedIn = false;
let isGrace = false;

// Variables for Live Progress Tracking
let baseTodayHours = 0;
let activeClockInTime = null;
let liveProgressInterval = null;

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Initialize clock and live calendar date display
    const updateClock = () => {
        const now = new Date();
        if (currentTimeDisplay) {
            currentTimeDisplay.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        }
        if (currentDateDisplay) {
            const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
            currentDateDisplay.textContent = now.toLocaleDateString(undefined, options);
        }
    };

    updateClock();
    setInterval(updateClock, 1000);

    // 2. Load attendance data & status
    await checkButton();
    await loadRecords();
    manageLiveProgress();

    // 3. Month Filter Change Listener
    if (monthFilter) {
        monthFilter.addEventListener("change", async () => {
            await loadRecords();
        });
    }

    // 4. Setup Schedule Modal Listener
    setupScheduleModal();
});

function showPage() {
    const main = document.querySelector('.main-container');
    if (main) {
        main.style.display = 'block';
        // Allow DOM paint before adding opacity class
        requestAnimationFrame(() => {
            main.classList.add('visible');
        });
    }
}

/**
 * Check user status from /api/status and adapt button styling
 */
async function checkButton() {
    if (!clockBtn) return;
    const userId = clockBtn.getAttribute('data-user-id');
    try {
        const res = await fetch(`/api/status?user_id=${encodeURIComponent(userId)}`);
        const data = await res.json();

        isClockedIn = Boolean(data.clocked_in && !data.clocked_out);
        isGrace = Boolean(data.is_grace);

        updateClockButtonUI();
    } catch (err) {
        console.error('Error checking button status:', err);
        if (statusText) statusText.textContent = "Status Check Failed";
        clockBtn.disabled = true;
    } finally {
        showPage();
    }
}

function updateClockButtonUI() {
    if (!clockBtn) return;

    if (isClockedIn && !isGrace) {
        // State: Clocked In -> Next action is Clock Out
        clockBtn.className = "clock-action-btn btn-clock-out";
        clockBtn.innerHTML = '<i class="bi bi-stop-fill"></i> <span id="clockBtnLabel">Clock Out</span>';
        
        if (statusBadge) {
            statusBadge.className = "status-badge-hero clocked-in";
        }
        if (statusText) {
            statusText.textContent = "Currently Clocked In";
        }
        if (activeShiftNotice) {
            activeShiftNotice.style.display = "block";
        }
    } else {
        // State: Clocked Out -> Next action is Clock In
        clockBtn.className = "clock-action-btn btn-clock-in";
        clockBtn.innerHTML = '<i class="bi bi-play-fill"></i> <span id="clockBtnLabel">Clock In</span>';
        
        if (statusBadge) {
            statusBadge.className = "status-badge-hero clocked-out";
        }
        if (statusText) {
            statusText.textContent = "Currently Clocked Out";
        }
        if (activeShiftNotice) {
            activeShiftNotice.style.display = "none";
        }
    }
}

function setDashboardLoading(isLoading) {
    const summaryTotalEl = document.getElementById('summaryTotalHours');
    const summaryRemainingEl = document.getElementById('summaryRemaining');
    const summaryTodayEl = document.getElementById('summaryToday');
    const summaryActiveDaysEl = document.getElementById('summaryActiveDays');
    const trendContainer = document.getElementById('trendBarsContainer');
    const tbody = document.getElementById('activityTableBody');
    const recordsCountBadge = document.getElementById('recordsCountBadge');

    const statElements = [summaryTotalEl, summaryRemainingEl, summaryTodayEl, summaryActiveDaysEl];

    if (isLoading) {
        statElements.forEach(el => {
            if (el) el.classList.add('skeleton-loading');
        });

        if (recordsCountBadge) {
            recordsCountBadge.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span> Loading...';
        }

        if (trendContainer) {
            trendContainer.innerHTML = `
                <div class="w-100 d-flex flex-column align-items-center justify-content-center py-4 text-muted">
                    <div class="spinner-border text-primary spinner-border-sm mb-2" role="status"></div>
                    <small>Loading monthly trends...</small>
                </div>
            `;
        }

        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted py-5">
                        <div class="spinner-border text-primary spinner-border-sm me-2" role="status"></div>
                        <span>Loading attendance records...</span>
                    </td>
                </tr>
            `;
        }
    } else {
        statElements.forEach(el => {
            if (el) el.classList.remove('skeleton-loading');
        });
    }
}

/**
 * Fetch and render attendance records, summaries, progress bars, and flags
 */
async function loadRecords() {
    if (!clockBtn) return;
    const userId = clockBtn.getAttribute('data-user-id');
    const month = monthFilter ? monthFilter.value : '';

    setDashboardLoading(true);

    try {
        const response = await fetch(
            `/api/gia-data?user_id=${encodeURIComponent(userId)}&month=${encodeURIComponent(month)}`
        );

        if (!response.ok) {
            throw new Error(`Failed to load records: ${response.status}`);
        }

        const data = await response.json();
        const records = data.records || [];
        const summary = data.summary || {};

        // Update Total Hours & Target
        const totalRendered = parseFloat(summary.total_hours || 0);
        const targetHours = parseFloat(summary.target_hours || 100);
        const remainingHours = Math.max(0, targetHours - totalRendered);
        const activeDays = parseInt(summary.active_days || 0, 10);
        baseTodayHours = parseFloat(summary.today_hours) || 0;

        const summaryTotalEl = document.getElementById('summaryTotalHours');
        const targetHoursLabel = document.getElementById('targetHoursLabel');
        const hoursProgressBar = document.getElementById('hoursProgressBar');
        const targetPercentageLabel = document.getElementById('targetPercentageLabel');
        const summaryRemainingEl = document.getElementById('summaryRemaining');
        const summaryActiveDaysEl = document.getElementById('summaryActiveDays');
        const recordsCountBadge = document.getElementById('recordsCountBadge');
        const trendMonthBadge = document.getElementById('trendMonthBadge');

        if (summaryTotalEl) summaryTotalEl.textContent = totalRendered.toFixed(2);
        if (targetHoursLabel) targetHoursLabel.textContent = targetHours.toFixed(0);
        if (summaryRemainingEl) summaryRemainingEl.textContent = remainingHours.toFixed(2);
        if (summaryActiveDaysEl) summaryActiveDaysEl.textContent = activeDays;

        if (recordsCountBadge) {
            recordsCountBadge.textContent = `${records.length} Record${records.length === 1 ? '' : 's'}`;
        }

        // Calculate progress percentage
        const progressPct = targetHours > 0 ? Math.min(100, (totalRendered / targetHours) * 100) : 0;
        if (hoursProgressBar) {
            hoursProgressBar.style.width = `${progressPct.toFixed(1)}%`;
            if (progressPct >= 100) {
                hoursProgressBar.style.backgroundColor = '#059669';
            } else {
                hoursProgressBar.style.backgroundColor = '';
            }
        }
        if (targetPercentageLabel) {
            targetPercentageLabel.textContent = `${progressPct.toFixed(1)}% of 100%`;
        }

        // Attendance Inconsistencies / Flags Summary
        const flagsSummaryText = document.getElementById('flagsSummaryText');
        if (flagsSummaryText) {
            const flags = summary.flags || {};
            const totalFlags = (flags.late || 0) + (flags.early_out || 0) + (flags.overtime || 0);
            if (totalFlags > 0) {
                let parts = [];
                if (flags.late) parts.push(`${flags.late} late`);
                if (flags.early_out) parts.push(`${flags.early_out} early`);
                if (flags.overtime) parts.push(`${flags.overtime} OT`);
                flagsSummaryText.innerHTML = `<span class="text-warning-emphasis fw-semibold"><i class="bi bi-exclamation-triangle-fill me-1"></i>${totalFlags} flag(s) (${parts.join(', ')})</span>`;
            } else {
                flagsSummaryText.innerHTML = `<span class="text-success"><i class="bi bi-check-circle me-1"></i>No flags recorded</span>`;
            }
        }

        // Update Trend Month Badge
        if (trendMonthBadge && month) {
            const [y, m] = month.split('-');
            const d = new Date(parseInt(y, 10), parseInt(m, 10) - 1, 1);
            trendMonthBadge.textContent = d.toLocaleDateString(undefined, { month: 'short', year: 'numeric' });
        }

        // Check for active running shift in records (must be today's date)
        activeClockInTime = null;
        if (records.length > 0) {
            const latest = records[0];
            const isToday = latest.is_today !== undefined
                ? latest.is_today
                : (latest.raw_date === new Date().toISOString().slice(0, 10));

            if (isToday && latest.clock_in && (!latest.clock_out || latest.clock_out === '-')) {
                activeClockInTime = latest.clock_in;
                if (shiftStartTimeEl) shiftStartTimeEl.textContent = latest.clock_in.toUpperCase();
            }
        }

        // Render Table & Trend Chart
        renderActivityTable(records);
        renderTrendChart(summary.daily_trend);

    } catch (err) {
        console.error('Error loading records:', err);
        const errorTitle = document.getElementById("errorTitle");
        const errorMessage = document.getElementById("errorMessage");
        if (errorTitle) errorTitle.textContent = "Error Loading Records";
        if (errorMessage) errorMessage.textContent = "Could not fetch data. Please try again.";
        if (errorModal) errorModal.show();
    } finally {
        setDashboardLoading(false);
    }
}

/**
 * Render Attendance Activity Table
 */
function renderActivityTable(records) {
    const tbody = document.getElementById('activityTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!records || records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4"><i class="bi bi-inbox me-2"></i>No attendance logs found for this month.</td></tr>`;
        return;
    }

    records.forEach(record => {
        const tr = document.createElement('tr');
        const statusText = record.status || (record.clock_in && record.clock_out ? 'Completed' : (record.clock_in ? 'On Duty' : 'Incomplete'));
        const badgeType = record.badge_type || 'secondary';
        const detailsTooltip = record.status_details ? `data-bs-toggle="tooltip" data-bs-placement="top" title="${escapeHtml(record.status_details)}"` : '';

        let badgeClass = 'incomplete';
        let badgeIcon = 'bi-dash-circle';

        if (badgeType === 'success') {
            badgeClass = 'completed';
            badgeIcon = 'bi-check-circle-fill';
        } else if (badgeType === 'warning') {
            badgeClass = 'late';
            badgeIcon = 'bi-exclamation-triangle-fill';
        } else if (badgeType === 'info') {
            badgeClass = 'active';
            badgeIcon = 'bi-broadcast';
        } else if (badgeType === 'secondary') {
            badgeClass = 'unscheduled';
            badgeIcon = 'bi-info-circle';
        }

        const statusBadge = `<span class="badge-status ${badgeClass}" ${detailsTooltip} style="cursor: ${record.status_details ? 'help' : 'default'};">
            <i class="bi ${badgeIcon}"></i> <span>${escapeHtml(statusText)}</span>
        </span>`;

        tr.innerHTML = `
            <td class="text-center font-mono fw-medium">${escapeHtml(record.date || '-')}</td>
            <td class="text-center font-mono">${escapeHtml(record.clock_in ? record.clock_in.toUpperCase() : '-')}</td>
            <td class="text-center font-mono">${escapeHtml(record.clock_out ? record.clock_out.toUpperCase() : '-')}</td>
            <td class="text-center">${statusBadge}</td>
            <td class="text-center font-mono fw-bold">${parseFloat(record.total_hours || 0).toFixed(2)} hrs</td>
        `;
        tbody.appendChild(tr);
    });

    // Initialize tooltips for status details
    const tooltipTriggerList = [].slice.call(tbody.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/**
 * Render Daily Duty Hours Trend Bar Chart
 */
function renderTrendChart(dailyTrend) {
    const container = document.getElementById('trendBarsContainer');
    const peakEl = document.getElementById('trendPeakHours');
    if (!container) return;
    container.innerHTML = '';

    if (!dailyTrend || dailyTrend.length === 0) {
        container.innerHTML = '<div class="w-100 text-center text-muted py-4">No daily duty activity recorded this month.</div>';
        if (peakEl) peakEl.textContent = '0.00';
        return;
    }

    const todayDate = new Date().getDate();
    const currentMonthStr = new Date().toISOString().slice(0, 7);
    const selectedMonth = monthFilter ? monthFilter.value : '';
    const isCurrentMonth = selectedMonth === currentMonthStr;

    const maxVal = Math.max(...dailyTrend.map(d => d.hours || 0), 4.0);
    const actualPeak = Math.max(...dailyTrend.map(d => d.hours || 0), 0);
    if (peakEl) peakEl.textContent = actualPeak.toFixed(2);

    dailyTrend.forEach(item => {
        const col = document.createElement('div');
        col.className = 'trend-bar-col';

        const hours = parseFloat(item.hours) || 0;
        const heightPercent = Math.min(100, Math.round((hours / maxVal) * 100));
        const isToday = isCurrentMonth && item.day === todayDate;

        let stemClass = 'trend-bar-stem';
        if (hours > 0) {
            stemClass += isToday ? ' is-today' : ' has-hours';
        } else {
            stemClass += ' empty';
        }

        col.innerHTML = `
            <div class="trend-bar-val">${hours > 0 ? hours.toFixed(1) : ''}</div>
            <div class="${stemClass}" 
                 style="height: ${Math.max(hours > 0 ? 12 : 4, heightPercent)}%;" 
                 title="Day ${item.day}: ${hours.toFixed(2)} hrs ${isToday ? '(Today)' : ''}"></div>
            <div class="trend-bar-label ${isToday ? 'fw-bold text-primary' : ''}">${item.day}</div>
        `;
        container.appendChild(col);
    });
}

/**
 * Live Progress Tracker: Updates "Today's Progress" and "Current Active Session" dynamically
 */
function manageLiveProgress() {
    if (liveProgressInterval) clearInterval(liveProgressInterval);

    const summaryTodayEl = document.getElementById('summaryToday');

    const parseTimeStr = (timeStr) => {
        if (!timeStr) return null;
        const match = String(timeStr).match(/(\d+):(\d+)(?::(\d+))?\s*(AM|PM)?/i);
        if (!match) return null;

        let hours = parseInt(match[1], 10);
        const minutes = parseInt(match[2], 10);
        const seconds = match[3] ? parseInt(match[3], 10) : 0;
        const ampm = match[4] ? match[4].toUpperCase() : null;

        if (ampm === 'PM' && hours < 12) hours += 12;
        if (ampm === 'AM' && hours === 12) hours = 0;

        const d = new Date();
        d.setHours(hours, minutes, seconds, 0);
        return d;
    };

    const updateProgress = () => {
        const safeBaseHours = parseFloat(baseTodayHours) || 0;

        if (isClockedIn && activeClockInTime && activeClockInTime !== '-') {
            const now = new Date();
            const clockInDate = parseTimeStr(activeClockInTime);

            if (clockInDate) {
                let diffMs = now - clockInDate;
                if (diffMs < 0) diffMs = 0;

                const liveSessionHours = diffMs / (1000 * 60 * 60);
                const totalLive = safeBaseHours + liveSessionHours;

                if (summaryTodayEl) summaryTodayEl.textContent = totalLive.toFixed(2);

                if (activeShiftDurationEl) {
                    const elapsedMins = Math.floor(diffMs / 60000);
                    const elapsedHours = Math.floor(elapsedMins / 60);
                    const remMins = elapsedMins % 60;
                    activeShiftDurationEl.textContent = elapsedHours > 0 ? `${elapsedHours}h ${remMins}m` : `${remMins}m`;
                }
                return;
            }
        }

        if (summaryTodayEl) summaryTodayEl.textContent = safeBaseHours.toFixed(2);
    };

    updateProgress();
    liveProgressInterval = setInterval(updateProgress, 10000); // refresh every 10 seconds
}

/**
 * Clock In / Clock Out Action Handler
 */
if (clockBtn) {
    clockBtn.addEventListener("click", async () => {
        clockBtn.disabled = true;

        const now = new Date();
        const timeFormatted = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const userId = clockBtn.getAttribute('data-user-id');

        const endpoint = isClockedIn && !isGrace ? '/api/clock-out' : '/api/clock-in';
        const actionText = isClockedIn && !isGrace ? 'Clock Out' : 'Clock In';

        try {
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userId)
            });

            const data = await res.json();

            if (data.success) {
                const successTitle = document.getElementById("successTitle");
                const successMessage = document.getElementById("successMessage");
                if (successTitle) successTitle.textContent = `${actionText} Successful!`;
                if (successMessage) {
                    const recordTime = data.data && data.data.time_record ? data.data.time_record : timeFormatted;
                    successMessage.innerHTML = `Your duty time has been recorded at <strong class="text-primary font-mono">${recordTime}</strong>.`;
                }
                if (successModal) successModal.show();

                await loadRecords();
                await checkButton();
                manageLiveProgress();
            } else {
                const errorTitle = document.getElementById("errorTitle");
                const errorMessage = document.getElementById("errorMessage");
                if (errorTitle) errorTitle.textContent = `${actionText} Failed`;
                if (errorMessage) errorMessage.textContent = data.error || `Unable to record ${actionText.toLowerCase()}. Please check with an administrator.`;
                if (errorModal) errorModal.show();
            }
        } catch (err) {
            console.error("Clock In/Out error:", err);
            const errorTitle = document.getElementById("errorTitle");
            const errorMessage = document.getElementById("errorMessage");
            if (errorTitle) errorTitle.textContent = "Network Error";
            if (errorMessage) errorMessage.textContent = "Unable to reach server. Please try again.";
            if (errorModal) errorModal.show();
        } finally {
            clockBtn.disabled = false;
        }
    });
}

/**
 * Schedule Modal Handler
 */
function setupScheduleModal() {
    const scheduleModal = document.getElementById('scheduleModal');
    if (!scheduleModal) return;

    scheduleModal.addEventListener('show.bs.modal', async (event) => {
        const button = event.relatedTarget;
        const userId = button ? button.getAttribute('data-user-id') : (clockBtn ? clockBtn.getAttribute('data-user-id') : '');
        const container = document.getElementById('scheduleListContainer');
        if (!container) return;

        container.innerHTML = `
            <div class="text-center text-muted py-3">
                <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                Loading schedule...
            </div>
        `;

        try {
            const response = await fetch(`/api/get-schedule/${encodeURIComponent(userId)}`);
            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error || 'Failed to fetch schedule');
            }

            if (!data.schedules || data.schedules.length === 0) {
                container.innerHTML = `
                    <div class="alert alert-light text-center border">
                        <i class="bi bi-info-circle me-1"></i> No regular shifts assigned yet.
                    </div>`;
                return;
            }

            const dayOrder = { "mw": 1, "tth": 2, "fri": 3, "sat": 4 };
            data.schedules.sort((a, b) => {
                return (dayOrder[a.day.toLowerCase()] || 99) - (dayOrder[b.day.toLowerCase()] || 99);
            });

            let listHtml = '';
            data.schedules.forEach(sched => {
                let timeBadge = '';
                const dayLabel = sched.day.toUpperCase();

                if (!sched.start_time || !sched.end_time) {
                    timeBadge = `<span class="badge bg-light text-muted border">No Shift Assigned</span>`;
                } else if (sched.is_split_shift) {
                    timeBadge = `
                        <div class="text-end">
                            <span class="badge bg-primary-subtle text-primary border border-primary-subtle d-block mb-1">
                                ${formatTime(sched.start_time)} &ndash; ${formatTime(sched.end_time)}
                            </span>
                            <span class="badge bg-primary-subtle text-primary border border-primary-subtle d-block">
                                ${formatTime(sched.split_start_time)} &ndash; ${formatTime(sched.split_end_time)}
                            </span>
                        </div>
                    `;
                } else {
                    timeBadge = `
                        <span class="badge bg-primary-subtle text-primary border border-primary-subtle">
                            ${formatTime(sched.start_time)} &ndash; ${formatTime(sched.end_time)}
                        </span>
                    `;
                }

                listHtml += `
                    <div class="shift-item">
                        <div>
                            <span class="fw-bold d-block text-dark">${dayLabel}</span>
                            <small class="text-muted">${sched.is_split_shift ? 'Split Shift' : (sched.start_time ? 'Regular Shift' : 'Unscheduled')}</small>
                        </div>
                        <div>${timeBadge}</div>
                    </div>
                `;
            });

            container.innerHTML = listHtml;
        } catch (error) {
            console.error("Error loading schedule:", error);
            container.innerHTML = `
                <div class="alert alert-danger text-center">
                    <i class="bi bi-exclamation-circle me-1"></i>
                    ${error.message || 'Error loading schedule'}
                </div>
            `;
        }
    });

    function formatTime(timeStr) {
        if (!timeStr) return '';
        const [hourString, minute] = timeStr.split(':');
        let hour = parseInt(hourString, 10);
        const ampm = hour >= 12 ? 'PM' : 'AM';
        hour = hour % 12 || 12;
        return `${hour}:${minute} ${ampm}`;
    }
}
