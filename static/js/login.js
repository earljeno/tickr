/**
 * Tickr Login Logic
 * Prioritizes the Student Assistant (GIA) login flow while providing
 * a subtle, seamless transition to Administrator access when requested.
 */

document.addEventListener('DOMContentLoaded', () => {
    const giaViewSection = document.getElementById('giaViewSection');
    const adminViewSection = document.getElementById('adminViewSection');

    const employeeForm = document.getElementById('employeeForm');
    const adminForm = document.getElementById('adminForm');

    const giaInput = document.getElementById('giaId');
    const giaError = document.getElementById('giaError');

    const adminInput = document.getElementById('adminId');
    const adminPass = document.getElementById('adminPassword');
    const adminError = document.getElementById('adminError');

    const toAdminBtn = document.getElementById('toAdminBtn');
    const toGiaBtn = document.getElementById('toGiaBtn');
    const togglePasswordBtn = document.getElementById('toggleAdminPassword');

    // Legacy elements for backwards-compatibility
    const toggleLink = document.getElementById('toggleLink');
    const toggleText = document.getElementById('toggleText');
    const loginTitle = document.getElementById('loginTitle');
    const tabGia = document.getElementById('tabGia');
    const tabAdmin = document.getElementById('tabAdmin');

    function showGiaView() {
        if (adminViewSection) adminViewSection.classList.add('d-none');
        if (giaViewSection) giaViewSection.classList.remove('d-none');

        if (adminForm) adminForm.classList.add('d-none');
        if (employeeForm) employeeForm.classList.remove('d-none');

        if (adminError) adminError.textContent = '';
        if (adminInput) adminInput.classList.remove('is-invalid');
        if (adminPass) adminPass.classList.remove('is-invalid');

        if (tabGia) tabGia.classList.add('active');
        if (tabAdmin) tabAdmin.classList.remove('active');
        if (loginTitle) loginTitle.textContent = 'Computer Center DTR System';
        if (toggleLink) toggleLink.textContent = 'Login as Admin';
        if (toggleText) toggleText.textContent = 'Admin?';

        giaInput?.focus();
    }

    function showAdminView() {
        if (giaViewSection) giaViewSection.classList.add('d-none');
        if (adminViewSection) adminViewSection.classList.remove('d-none');

        if (employeeForm) employeeForm.classList.add('d-none');
        if (adminForm) adminForm.classList.remove('d-none');

        if (giaError) giaError.textContent = '';
        if (giaInput) giaInput.classList.remove('is-invalid');

        if (tabAdmin) tabAdmin.classList.add('active');
        if (tabGia) tabGia.classList.remove('active');
        if (loginTitle) loginTitle.textContent = 'Administrator Portal';
        if (toggleLink) toggleLink.textContent = 'Login as GIA';
        if (toggleText) toggleText.textContent = 'GIA?';

        adminInput?.focus();
    }

    // Toggle events
    toAdminBtn?.addEventListener('click', (e) => {
        e.preventDefault();
        showAdminView();
    });

    toGiaBtn?.addEventListener('click', (e) => {
        e.preventDefault();
        showGiaView();
    });

    // Backward-compatibility listeners
    tabGia?.addEventListener('click', showGiaView);
    tabAdmin?.addEventListener('click', showAdminView);
    toggleLink?.addEventListener('click', (e) => {
        e.preventDefault();
        if (giaViewSection?.classList.contains('d-none')) {
            showGiaView();
        } else {
            showAdminView();
        }
    });

    // Password visibility toggle
    togglePasswordBtn?.addEventListener('click', () => {
        if (!adminPass) return;
        const type = adminPass.getAttribute('type') === 'password' ? 'text' : 'password';
        adminPass.setAttribute('type', type);
        const icon = togglePasswordBtn.querySelector('i');
        if (icon) {
            icon.className = type === 'password' ? 'bi bi-eye text-muted' : 'bi bi-eye-slash text-primary';
        }
    });

    // Student Assistant (GIA) Form Submission
    employeeForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const giaId = giaInput?.value.trim();
        if (!giaId) return;

        const submitBtn = employeeForm.querySelector('button[type="submit"]');
        const originalBtnHTML = submitBtn ? submitBtn.innerHTML : '';
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Authenticating...';
        }

        try {
            const res = await fetch('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ giaId }),
            });

            const data = await res.json();

            if (!res.ok || !data.success) {
                giaInput?.classList.add('is-invalid');
                if (giaError) {
                    giaError.textContent = data.error || 'No active account found with that ID number.';
                }
                return;
            }

            window.location.href = data.redirect || '/dashboard';
        } catch (err) {
            console.error('Login error:', err);
            giaInput?.classList.add('is-invalid');
            if (giaError) {
                giaError.textContent = 'Unable to reach the server. Please check your network connection.';
            }
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnHTML;
            }
        }
    });

    giaInput?.addEventListener('input', () => {
        giaInput.classList.remove('is-invalid');
        if (giaError) giaError.textContent = '';
    });

    // Administrator Form Submission
    adminForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const adminId = adminInput?.value.trim();
        const password = adminPass?.value;
        if (!adminId || !password) return;

        const submitBtn = adminForm.querySelector('button[type="submit"]');
        const originalBtnHTML = submitBtn ? submitBtn.innerHTML : '';
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Verifying...';
        }

        try {
            const res = await fetch('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ adminId, password }),
            });

            const data = await res.json();

            if (!res.ok || !data.success) {
                adminInput?.classList.add('is-invalid');
                adminPass?.classList.add('is-invalid');
                if (adminError) {
                    adminError.textContent = data.error || 'Incorrect username or password.';
                }
                return;
            }

            window.location.href = data.redirect || '/admin/dashboard';
        } catch (err) {
            console.error('Login error:', err);
            if (adminError) {
                adminError.textContent = 'Unable to reach the server. Please check your network connection.';
            }
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnHTML;
            }
        }
    });

    adminInput?.addEventListener('input', () => {
        adminInput.classList.remove('is-invalid');
        if (adminError) adminError.textContent = '';
    });

    adminPass?.addEventListener('input', () => {
        adminPass.classList.remove('is-invalid');
        if (adminError) adminError.textContent = '';
    });
});
