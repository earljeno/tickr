document.addEventListener('DOMContentLoaded', () => {
    const giaSelector = document.getElementById('giaSelector');
    const monthFilter = document.getElementById('monthFilter');
    const refreshBtn = document.getElementById('refreshBtn');
    const exportCsvBtn = document.getElementById('exportCsvBtn');
    const exportPdfBtn = document.getElementById('exportPdfBtn');
    const btnCurrentMonth = document.getElementById('btnCurrentMonth');
    const btnPrevMonth = document.getElementById('btnPrevMonth');

    function updateExportLinks() {
        const userId = giaSelector ? giaSelector.value : '';
        const month = monthFilter ? monthFilter.value : '';
        if (exportPdfBtn) {
            exportPdfBtn.href = `/admin/export?user_id=${encodeURIComponent(userId)}&month=${encodeURIComponent(month)}`;
        }
    }

    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', () => {
            const userId = giaSelector ? giaSelector.value : '';
            const month = monthFilter ? monthFilter.value : '';
            if (!userId) {
                if (typeof showAlert === 'function') showAlert('warning', 'Please select a GIA assistant first.');
                return;
            }
            window.location.href = `/api/export-gia-logs?user_id=${encodeURIComponent(userId)}&month=${encodeURIComponent(month)}`;
        });
    }

    if (btnCurrentMonth && monthFilter) {
        btnCurrentMonth.addEventListener('click', () => {
            const now = new Date();
            const y = now.getFullYear();
            const m = String(now.getMonth() + 1).padStart(2, '0');
            monthFilter.value = `${y}-${m}`;
            updateExportLinks();
            loadGiaLogs();
        });
    }

    if (btnPrevMonth && monthFilter) {
        btnPrevMonth.addEventListener('click', () => {
            const [curY, curM] = (monthFilter.value || '').split('-').map(Number);
            const d = new Date(curY || new Date().getFullYear(), (curM || 1) - 2, 1);
            const y = d.getFullYear();
            const m = String(d.getMonth() + 1).padStart(2, '0');
            monthFilter.value = `${y}-${m}`;
            updateExportLinks();
            loadGiaLogs();
        });
    }

    if (giaSelector) {
        giaSelector.addEventListener('change', () => {
            updateExportLinks();
            updateAssistantHeader();
            loadGiaLogs();
        });
    }

    if (monthFilter) {
        monthFilter.addEventListener('change', () => {
            updateExportLinks();
            loadGiaLogs();
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadGiaLogs();
        });
    }

    updateExportLinks();
    loadGiaLogs();
});

function updateAssistantHeader() {
    const giaSelector = document.getElementById('giaSelector');
    if (!giaSelector) return;
    const selectedOption = giaSelector.options[giaSelector.selectedIndex];
    if (selectedOption) {
        const userId = selectedOption.value;
        const name = selectedOption.dataset.name || selectedOption.textContent.trim();
        const lab = selectedOption.dataset.laboratory;
        const status = (selectedOption.dataset.status || 'inactive').toLowerCase();

        const assistantFullName = document.getElementById('assistantFullName');
        const assistantUserId = document.getElementById('assistantUserId');
        const assistantLab = document.getElementById('assistantLab');
        const assistantStatusBadge = document.getElementById('assistantStatusBadge');

        if (assistantFullName) assistantFullName.textContent = name;
        if (assistantUserId) assistantUserId.textContent = userId;
        if (assistantLab) assistantLab.textContent = lab ? `Room ${lab}` : 'Not Assigned';
        if (assistantStatusBadge) {
            assistantStatusBadge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            if (status === 'active') {
                assistantStatusBadge.className = 'badge bg-success-subtle text-success border border-success-subtle';
            } else {
                assistantStatusBadge.className = 'badge bg-secondary-subtle text-secondary border';
            }
        }
    }
}

async function loadGiaLogs() {
    const giaSelector = document.getElementById('giaSelector');
    const monthFilter = document.getElementById('monthFilter');
    const tbody = document.getElementById('giaLogsTableBody');

    if (!giaSelector || !giaSelector.value) {
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">No student assistant selected.</td></tr>`;
        }
        return;
    }

    const userId = giaSelector.value;
    const month = monthFilter ? monthFilter.value : '';

    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-5 text-muted">
                    <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                    Loading attendance records and analytics...
                </td>
            </tr>
        `;
    }

    try {
        const res = await fetch(`/api/gia-data?user_id=${encodeURIComponent(userId)}&month=${encodeURIComponent(month)}`);
        if (!res.ok) {
            throw new Error(`Failed to load data (${res.status})`);
        }

        const data = await res.json();
        const summary = data.summary || {};
        const records = data.records || [];

        renderKPIs(summary);
        renderTrendChart(summary.daily_trend || [], month);
        renderFlags(summary.inconsistencies || []);
        renderLogsTable(records);

    } catch (err) {
        console.error('Error fetching GIA analytics:', err);
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger py-4"><i class="bi bi-exclamation-circle me-1"></i> Error loading attendance data. Please try again.</td></tr>`;
        }
        if (typeof showAlert === 'function') {
            showAlert('danger', 'Failed to fetch logs and analytics.');
        }
    }
}

function renderKPIs(summary) {
    const totalHours = Number(summary.total_hours || 0);
    const targetHours = Number(summary.target_hours || 100);
    const remaining = Math.max(0, targetHours - totalHours);
    const progressPercent = Math.min(100, Math.round((totalHours / targetHours) * 100));

    const kpiRendered = document.getElementById('kpiRenderedHours');
    const kpiRemaining = document.getElementById('kpiRemainingHours');
    const kpiActive = document.getElementById('kpiActiveDays');
    const kpiProgressBar = document.getElementById('kpiProgressBar');
    const kpiProgressPercent = document.getElementById('kpiProgressPercent');
    const tableTotalHours = document.getElementById('tableTotalHours');

    if (kpiRendered) kpiRendered.textContent = totalHours.toFixed(2);
    if (kpiRemaining) kpiRemaining.textContent = remaining.toFixed(2);
    if (kpiActive) kpiActive.textContent = summary.active_days || 0;
    if (tableTotalHours) tableTotalHours.textContent = totalHours.toFixed(2);

    if (kpiProgressBar) {
        kpiProgressBar.style.width = `${progressPercent}%`;
        kpiProgressBar.setAttribute('aria-valuenow', progressPercent);
        if (progressPercent >= 100) {
            kpiProgressBar.className = 'progress-bar bg-success';
        } else {
            kpiProgressBar.className = 'progress-bar bg-primary';
        }
    }
    if (kpiProgressPercent) kpiProgressPercent.textContent = `${progressPercent}%`;

    const flags = summary.flags || {};
    const totalFlags = Number(flags.total_inconsistencies || 0);
    const kpiFlagsCount = document.getElementById('kpiFlagsCount');
    const kpiFlagsBreakdown = document.getElementById('kpiFlagsBreakdown');

    if (kpiFlagsCount) kpiFlagsCount.textContent = totalFlags;
    if (kpiFlagsBreakdown) {
        kpiFlagsBreakdown.innerHTML = `
            <span>Late: <strong class="text-dark">${flags.late || 0}</strong></span> • 
            <span>Early Out: <strong class="text-dark">${flags.early_out || 0}</strong></span> • 
            <span>OT: <strong class="text-dark">${flags.overtime || 0}</strong></span>
        `;
    }
}

function renderTrendChart(dailyTrend, monthStr) {
    const container = document.getElementById('chartBars');
    const trendMonthBadge = document.getElementById('trendMonthBadge');
    const trendMaxHours = document.getElementById('trendMaxHours');

    if (!container) return;
    container.innerHTML = '';

    if (trendMonthBadge && monthStr) {
        trendMonthBadge.textContent = monthStr;
    }

    if (!dailyTrend || dailyTrend.length === 0) {
        container.innerHTML = `<div class="w-100 text-center text-muted py-5">No daily trend activity for this month.</div>`;
        if (trendMaxHours) trendMaxHours.textContent = '0.00';
        return;
    }

    const maxVal = Math.max(...dailyTrend.map(d => d.hours), 4.0); // Minimum 4h baseline
    if (trendMaxHours) {
        const actualMax = Math.max(...dailyTrend.map(d => d.hours), 0.0);
        trendMaxHours.textContent = actualMax.toFixed(2);
    }

    dailyTrend.forEach(item => {
        const barWrap = document.createElement('div');
        barWrap.className = 'd-flex flex-column align-items-center flex-fill';
        barWrap.style.minWidth = '22px';
        barWrap.style.height = '100%';
        barWrap.style.justifyContent = 'flex-end';

        const heightPercent = Math.min(100, Math.round((item.hours / maxVal) * 100));
        const barColor = item.hours > 0 ? (item.hours >= 4.0 ? 'bg-primary' : 'bg-info') : 'bg-light';
        const borderClass = item.hours > 0 ? '' : 'border';

        barWrap.innerHTML = `
            <div class="small font-mono text-muted" style="font-size: 0.65rem; margin-bottom: 2px;">
                ${item.hours > 0 ? item.hours.toFixed(1) : ''}
            </div>
            <div class="${barColor} ${borderClass} rounded-top w-100 transition" 
                 style="height: ${Math.max(item.hours > 0 ? 8 : 2, heightPercent)}%;" 
                 title="Day ${item.day}: ${item.hours.toFixed(2)} hrs">
            </div>
            <div class="text-muted mt-1 font-mono" style="font-size: 0.7rem;">
                ${item.day}
            </div>
        `;
        container.appendChild(barWrap);
    });
}

function renderFlags(inconsistencies) {
    const flagsCard = document.getElementById('flagsCard');
    const flagsTableBody = document.getElementById('flagsTableBody');
    const flagsBadgeCount = document.getElementById('flagsBadgeCount');

    if (!flagsCard || !flagsTableBody) return;

    if (!inconsistencies || inconsistencies.length === 0) {
        flagsCard.style.display = 'none';
        flagsTableBody.innerHTML = '';
        return;
    }

    flagsCard.style.display = 'block';
    if (flagsBadgeCount) flagsBadgeCount.textContent = `${inconsistencies.length} Flag${inconsistencies.length === 1 ? '' : 's'}`;

    flagsTableBody.innerHTML = '';
    inconsistencies.forEach(flag => {
        const tr = document.createElement('tr');
        let badgeClass = 'bg-danger-subtle text-danger border border-danger-subtle';
        if (flag.issue_type === 'Late') badgeClass = 'bg-warning-subtle text-warning-emphasis border border-warning-subtle';
        if (flag.issue_type === 'Early Out') badgeClass = 'bg-danger-subtle text-danger border border-danger-subtle';
        if (flag.issue_type === 'Overtime') badgeClass = 'bg-info-subtle text-info-emphasis border border-info-subtle';

        tr.innerHTML = `
            <td class="ps-4 fw-medium text-dark font-mono">${escapeHtml(flag.date)}</td>
            <td class="text-center">
                <span class="badge ${badgeClass} fw-semibold">${escapeHtml(flag.issue_type)}</span>
            </td>
            <td class="text-muted small">${escapeHtml(flag.details)}</td>
        `;
        flagsTableBody.appendChild(tr);
    });
}

function renderLogsTable(records) {
    const tbody = document.getElementById('giaLogsTableBody');
    const logsCountBadge = document.getElementById('logsCountBadge');
    if (!tbody) return;

    if (logsCountBadge) {
        logsCountBadge.textContent = `${records.length} Record${records.length === 1 ? '' : 's'}`;
    }

    if (!records || records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted py-5">No attendance records found for this billing period.</td></tr>`;
        return;
    }

    tbody.innerHTML = '';
    records.forEach(record => {
        const tr = document.createElement('tr');
        const hoursNum = parseFloat(record.total_hours) || 0.0;

        tr.innerHTML = `
            <td class="ps-4 fw-medium font-mono text-dark">${escapeHtml(record.date || '-')}</td>
            <td class="text-center font-mono">${escapeHtml(record.clock_in ? record.clock_in.toUpperCase() : '-')}</td>
            <td class="text-center font-mono">${escapeHtml(record.clock_out ? record.clock_out.toUpperCase() : '-')}</td>
            <td class="text-center pe-4 font-mono fw-bold ${hoursNum > 0 ? 'text-primary' : 'text-muted'}">${hoursNum.toFixed(2)} hrs</td>
        `;
        tbody.appendChild(tr);
    });
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
