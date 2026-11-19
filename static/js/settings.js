// DTR Settings JavaScript

// Initialize settings functionality
function initSettings() {
    setupToggleHandlers();
    setupSaveSettings();
    loadSettings();
}

// Setup toggle switch handlers
function setupToggleHandlers() {
    const strictModeToggle = document.getElementById('enableStrictMode');
    const earlyInToggle = document.getElementById('allowEarlyIn');
    
    // Strict Mode toggle
    if (strictModeToggle) {
        strictModeToggle.addEventListener('change', function() {
            const strictModeOptions = document.getElementById('strictModeOptions');    
            if (strictModeOptions) {
                strictModeOptions.style.display = strictModeToggle.checked ? 'none' : 'block';
            }
            updateSummary();
        });
    }

    // Early In toggle
    if (earlyInToggle) {
        earlyInToggle.addEventListener('change', function() {
            const earlyInOptions = document.getElementById('earlyInOptions');
            if (earlyInOptions) {
                earlyInOptions.style.display = this.checked ? 'block' : 'none';
            }
            updateSummary();
        });
    }

    ['allowEarlyOut', 'allowOvertime', 'unitHeadName', 'defaultStartTime', 'defaultEndTime', 'earlyInMinutes'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', updateSummary);
            el.addEventListener('change', updateSummary);
        }
    });
}

// Validate individual input
function validateInput(input) {
    const value = input.value.trim();
    
    // Remove existing validation classes
    input.classList.remove('is-valid', 'is-invalid');
    
    // Validate based on input type
    switch(input.type) {
        case 'number':
            const min = parseInt(input.min, 10) || 0;
            const max = parseInt(input.max, 10) || Infinity;
            const numValue = parseInt(value, 10);
            
            if (value === '' || isNaN(numValue) || numValue < min || numValue > max) {
                input.classList.add('is-invalid');
                return false;
            } else {
                input.classList.add('is-valid');
                return true;
            }
            
        case 'time':
            if (value === '') {
                input.classList.add('is-invalid');
                return false;
            } else {
                input.classList.add('is-valid');
                return true;
            }
            
        case 'text':
            if (input.hasAttribute('required') && value === '') {
                input.classList.add('is-invalid');
                return false;
            } else if (value !== '') {
                input.classList.add('is-valid');
                return true;
            }
            break;
    }
    
    return true;
}

function loadSettings() {
    fetch('/api/get-settings')
        .then(res => {
            if (!res.ok) throw new Error(`Server responded with ${res.status}`);
            return res.json();
        })
        .then(settings => {
            const setVal = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.value = val;
            };

            setVal('unitHeadName', settings.unit_head || '');
            setVal('defaultStartTime', settings.def_start || '08:00');
            setVal('defaultEndTime', settings.def_end || '17:00');
            
            const strictEl = document.getElementById('enableStrictMode');
            if (strictEl) strictEl.checked = !!settings.strict;

            setVal('strictModeEndDate', settings.strict_duration || '');
            setVal('earlyInMinutes', settings.early_allowance !== undefined ? settings.early_allowance : '15');

            const earlyOutEl = document.getElementById('allowEarlyOut');
            if (earlyOutEl) earlyOutEl.checked = !!settings.early;

            const overtimeEl = document.getElementById('allowOvertime');
            if (overtimeEl) overtimeEl.checked = !!settings.overtime;

            const strictModeOptions = document.getElementById('strictModeOptions');            
            if (strictModeOptions) {
                strictModeOptions.style.display = settings.strict ? 'none' : 'block';
            }
            updateSummary();
        })
        .catch(err => {
            console.error('Failed to load settings:', err);
            showAlert('danger', 'Unable to retrieve settings.');
        });
}

// Setup save settings functionality
function setupSaveSettings() {
    const saveButton = document.getElementById('saveSettings');
    if (!saveButton) return;
    
    saveButton.addEventListener('click', function() {
        if (validateForm()) {
            saveSettings();
        }
    });
}

// Validate entire form
function validateForm() {
    const form = document.getElementById('settingsForm');
    if (!form) return false;
    const inputs = form.querySelectorAll('input[type="number"], input[type="time"], input[type="text"]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!validateInput(input)) {
            isValid = false;
        }
    });
    
    // Additional validation for time range
    const startTime = document.getElementById('defaultStartTime').value;
    const endTime = document.getElementById('defaultEndTime').value;
    
    if (startTime && endTime && startTime >= endTime) {
        document.getElementById('defaultEndTime').classList.add('is-invalid');
        isValid = false;
        showAlert('danger', 'Default end time must be after start time.');
    }
    
    return isValid;
}

// Save settings without artificial delays
function saveSettings() {
    const saveButton = document.getElementById('saveSettings');
    const originalText = saveButton.innerHTML;
    
    saveButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
    saveButton.disabled = true;

    const settings = {
        unitHeadName: document.getElementById('unitHeadName')?.value || '',
        unitHeadTitle: document.getElementById('unitHeadTitle')?.value || 'Department Head',
        enableStrictMode: document.getElementById('enableStrictMode')?.checked || false,
        strictDuration: document.getElementById('strictModeEndDate')?.value || '',
        earlyInMinutes: document.getElementById('earlyInMinutes')?.value || 0,
        allowEarlyOut: document.getElementById('allowEarlyOut')?.checked || false,
        allowOvertime: document.getElementById('allowOvertime')?.checked || false,
        defaultStartTime: document.getElementById('defaultStartTime')?.value || '',
        defaultEndTime: document.getElementById('defaultEndTime')?.value || ''
    };

    fetch('/api/update-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
    })
    .then(async res => {
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.error || 'Failed to save settings.');
        }
        showAlert('success', 'System settings saved successfully!');
        updateSummary();
    })
    .catch(err => {
        console.error('Error saving settings:', err);
        showAlert('danger', err.message || 'Error saving settings.');
    })
    .finally(() => {
        saveButton.innerHTML = originalText;
        saveButton.disabled = false;
    });
}

// Update settings summary
function updateSummary() {
    const unitHeadName = document.getElementById('unitHeadName')?.value || 'Not Set';
    const startTime = document.getElementById('defaultStartTime')?.value;
    const endTime = document.getElementById('defaultEndTime')?.value;
    const strictMode = document.getElementById('enableStrictMode')?.checked;
    const earlyInMinutes = document.getElementById('earlyInMinutes')?.value || '0';
    const earlyOut = document.getElementById('allowEarlyOut')?.checked;
    const overtime = document.getElementById('allowOvertime')?.checked;
    
    const summaryUnitHead = document.getElementById('summaryUnitHead');
    if (summaryUnitHead) summaryUnitHead.textContent = unitHeadName;

    const summaryWorkingHours = document.getElementById('summaryWorkingHours');
    if (summaryWorkingHours) {
        summaryWorkingHours.textContent = (startTime && endTime) ? `${formatTime(startTime)} - ${formatTime(endTime)}` : 'Not Set';
    }

    const summaryStrictMode = document.getElementById('summaryStrictMode');
    if (summaryStrictMode) {
        summaryStrictMode.textContent = strictMode ? 'Strict Active' : 'Relaxed Mode';
        summaryStrictMode.className = `status-badge ${strictMode ? 'active' : 'neutral'}`;
    }

    const summaryEarlyIn = document.getElementById('summaryEarlyIn');
    if (summaryEarlyIn) {
        summaryEarlyIn.textContent = `${earlyInMinutes} minutes`;
    }

    const summaryEarlyOut = document.getElementById('summaryEarlyOut');
    if (summaryEarlyOut) {
        summaryEarlyOut.textContent = earlyOut ? 'Permitted' : 'Disabled';
        summaryEarlyOut.className = `status-badge ${earlyOut ? 'active' : 'neutral'}`;
    }

    const summaryOvertime = document.getElementById('summaryOvertime');
    if (summaryOvertime) {
        summaryOvertime.textContent = overtime ? 'Allowed' : 'Disabled';
        summaryOvertime.className = `status-badge ${overtime ? 'active' : 'neutral'}`;
    }
}

function formatTime(timeStr) {
    if (!timeStr) return '';
    const parts = timeStr.split(':');
    let hour = parseInt(parts[0], 10);
    const minute = parts[1];
    const ampm = hour >= 12 ? 'PM' : 'AM';
    hour = hour % 12 || 12;
    return `${hour}:${minute} ${ampm}`;
}

document.addEventListener('DOMContentLoaded', initSettings);
