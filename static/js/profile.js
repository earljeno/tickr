// Profile Page JavaScript - Read Only Info + Password Change

function initProfile() {
    // Only initializing password related stuff
    setupPasswordToggle();
    setupPasswordStrength();
    setupChangePassword();
}

function loadInfo() {
    const userId = document.getElementById('userId').value;

    fetch(`/api/get-user/${userId}`)
        .then(res => {
            if (!res.ok) throw new Error(`Server responded with ${res.status}`);
            return res.json();
        })
        .then(user => {
            document.getElementById('firstName').value = user.first_name;
            document.getElementById('lastName').value = user.last_name;
            document.getElementById('middleName').value = user.middle_name || '';
            document.getElementById('username').value = user.username; // Added username mapping
            
            // Handle visuals
            const fullName = `${user.first_name} ${user.last_name}`;
            const initials = `${user.first_name[0]}${user.last_name[0]}`;
            
            const nameDisplay = document.getElementById('fullName');
            if(nameDisplay) nameDisplay.innerText = fullName;
            
            const initDisplay = document.getElementById('initials');
            if(initDisplay) initDisplay.innerText = initials;
        })
        .catch(err => console.error("Failed to load user:", err));
}

// Setup password toggle functionality
function setupPasswordToggle() {
    const toggleButtons = [
        { button: 'toggleCurrentPassword', input: 'currentPassword' },
        { button: 'toggleNewPassword', input: 'newPassword' },
        { button: 'toggleConfirmPassword', input: 'confirmPassword' }
    ];
    
    toggleButtons.forEach(({ button, input }) => {
        const toggleBtn = document.getElementById(button);
        const inputField = document.getElementById(input);
        
        if (toggleBtn && inputField) {
            toggleBtn.addEventListener('click', function() {
                const type = inputField.getAttribute('type') === 'password' ? 'text' : 'password';
                inputField.setAttribute('type', type);
                
                const icon = this.querySelector('i');
                icon.className = type === 'password' ? 'fas fa-eye' : 'fas fa-eye-slash';
            });
        }
    });
}

// Setup password strength indicator
function setupPasswordStrength() {
    const newPasswordInput = document.getElementById('newPassword');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const strengthIndicator = document.getElementById('passwordStrength');
    const strengthBar = document.getElementById('strengthBar');
    const strengthText = document.getElementById('strengthText');
    
    if(!newPasswordInput) return;

    newPasswordInput.addEventListener('input', function() {
        const password = this.value;
        
        if (password.length > 0) {
            strengthIndicator.style.display = 'block';
            const strength = calculatePasswordStrength(password);
            updateStrengthIndicator(strength, strengthBar, strengthText);
        } else {
            strengthIndicator.style.display = 'none';
        }
        
        if (confirmPasswordInput.value) {
            validatePasswordMatch();
        }
    });
    
    confirmPasswordInput.addEventListener('input', validatePasswordMatch);
}

function calculatePasswordStrength(password) {
    let score = 0;
    if (password.length >= 8) score += 1;
    if (password.length >= 12) score += 1;
    if (/[a-z]/.test(password)) score += 1;
    if (/[A-Z]/.test(password)) score += 1;
    if (/[0-9]/.test(password)) score += 1;
    if (/[^A-Za-z0-9]/.test(password)) score += 1;
    return Math.min(score, 4);
}

function updateStrengthIndicator(strength, bar, text) {
    const colors = ['#dc3545', '#fd7e14', '#ffc107', '#28a745'];
    const labels = ['Very Weak', 'Weak', 'Fair', 'Strong'];
    const widths = [25, 50, 75, 100];
    
    const index = Math.min(strength - 1, 3);
    if(index < 0) return; // handle empty/very weak

    const color = colors[index];
    bar.style.backgroundColor = color;
    bar.style.width = widths[index] + '%';
    text.textContent = labels[index];
    text.style.color = color;
}

function validatePasswordMatch() {
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const confirmInput = document.getElementById('confirmPassword');
    
    confirmInput.classList.remove('is-valid', 'is-invalid');
    
    if (confirmPassword === '') return;
    
    if (newPassword === confirmPassword) {
        confirmInput.classList.add('is-valid');
        return true;
    } else {
        confirmInput.classList.add('is-invalid');
        return false;
    }
}

// Setup change password functionality
function setupChangePassword() {
    const changePasswordBtn = document.getElementById('changePassword');
    if(!changePasswordBtn) return;
    
    changePasswordBtn.addEventListener('click', function() {
        if (validatePasswordForm()) {
            changePassword();
        }
    });
}

function validatePasswordForm() {
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    
    if (!currentPassword || !newPassword) {
        showAlert('error', 'Please fill in all fields.');
        return false;
    }
    
    if (newPassword.length < 8) {
        showAlert('error', 'New password must be at least 8 characters long.');
        return false;
    }
    
    if (!validatePasswordMatch()) {
        showAlert('error', 'New passwords do not match.');
        return false;
    }
    
    return true;
}

function changePassword() {
    const btn = document.getElementById('changePassword');
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Changing...';
    btn.disabled = true;

    // Use a hardcoded ID or the one from the hidden input
    const userId = document.getElementById('userId').value || "123";

    fetch('/api/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            userId,
            currentPassword,
            newPassword,
            confirmPassword
        })
    })
    .then(res => res.json())
    .then(data => {
        btn.innerHTML = '<i class="fas fa-key me-2"></i>Update Password';
        btn.disabled = false;

        if (!data.success) {
            showAlert('danger', data.error || "Something went wrong");
            return;
        }

        // Clear fields on success
        document.getElementById('currentPassword').value = '';
        document.getElementById('newPassword').value = '';
        document.getElementById('confirmPassword').value = '';
        document.getElementById('passwordStrength').style.display = 'none';
        
        const inputs = document.querySelectorAll('#passwordForm input');
        inputs.forEach(i => i.classList.remove('is-valid', 'is-invalid'));

        showAlert('success', 'Password changed successfully!');
    })
    .catch(err => {
        btn.innerHTML = '<i class="fas fa-key me-2"></i>Update Password';
        btn.disabled = false;
        showAlert('danger', 'Network error.');
        console.error(err);
    });
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    initProfile();
    loadInfo();
});