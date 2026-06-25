let currentPage = 1;
let perPage = 10;
let currentEditingUserId = null;

function getFilterValues() {
    return {
        search: document.getElementById('userSearch').value.trim(),
        status: document.getElementById('statusFilter').value,
        role: document.getElementById('roleFilter').value,
        perPage: parseInt(document.getElementById('pageSizeSelect').value, 10) || 10
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

function updatePagination(total, page, perPage) {
    const pagination = document.getElementById('usersPagination');
    const showingInfo = document.getElementById('usersShowingInfo');

    pagination.innerHTML = '';

    const totalPages = Math.max(1, Math.ceil(total / perPage));
    const startItem = total === 0 ? 0 : (page - 1) * perPage + 1;
    const endItem = Math.min(total, page * perPage);
    showingInfo.textContent = `Showing ${startItem}-${endItem} of ${total} users`;

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
                loadUsers();
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

function normalizePhilippinePhone(phone) {
    if (!phone) return '';
    let digits = phone.toString().replace(/\D+/g, '');
    digits = digits.replace(/^00/, '');

    if (digits === '63') {
        return '';
    }

    if (digits.startsWith('63')) {
        // already country formatted
    } else if (digits.startsWith('0')) {
        digits = '63' + digits.slice(1);
    } else {
        digits = '63' + digits;
    }

    if (digits === '63') {
        return '';
    }

    return digits;
}

function formatPhilippinePhone(phone) {
    const digits = normalizePhilippinePhone(phone);
    if (!digits) return '-';
    if (!digits.startsWith('63')) return '+' + digits;

    const rest = digits.slice(2);
    if (!rest.length) return '-';
    if (rest.length === 10) {
        return `+63 ${rest.slice(0, 3)} ${rest.slice(3, 6)} ${rest.slice(6)}`;
    }
    if (rest.length === 9) {
        return `+63 ${rest.slice(0, 1)} ${rest.slice(1, 5)} ${rest.slice(5)}`;
    }
    if (rest.length === 7) {
        return `+63 ${rest.slice(0, 3)} ${rest.slice(3)}`;
    }
    if (rest.length === 8) {
        return `+63 ${rest.slice(0, 3)} ${rest.slice(3)}`;
    }
    return `+${digits}`;
}

function formatPhone(phone) {
    return phone ? formatPhilippinePhone(phone) : '-';
}

function formatLaboratory(lab) {
    return lab ? `Room ${lab}` : '-';
}

function renderUsers(users) {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = '';

    users.forEach(user => {
        const tr = document.createElement('tr');
        const initials = `${(user.first_name || '').charAt(0)}${(user.last_name || '').charAt(0)}`.toUpperCase();
        const roleLabel = user.role === 'gia' ? 'GIA' : user.role || '-';

        tr.innerHTML = `
            <td class="ps-4">
                <div class="d-flex align-items-center">
                    <div class="user-avatar me-3">
                        <div class="default-avatar rounded-circle d-flex align-items-center justify-content-center"
                            style="width: 40px; height: 40px">
                            <span class="initials">${initials}</span>
                        </div>
                    </div>
                    <div>
                        <div class="user-name">${user.first_name || '-'} ${user.last_name || ''}</div>
                        <div class="user-email">${user.user_id || '-'}</div>
                    </div>
                </div>
            </td>
            <td class="text-center">${formatPhone(user.phone_number)}</td>
            <td class="text-center">${formatLaboratory(user.laboratory)}</td>
            <td class="text-center">
                <span class="role-badge ${user.role ? user.role.toLowerCase() : 'unknown'}">${roleLabel}</span>
            </td>
            <td class="text-center">
                <span class="status-badge ${user.status ? user.status.toLowerCase() : 'unknown'}">${user.status || '-'}</span>
            </td>
            <td class="text-center">
                <div class="d-inline-flex gap-2 justify-content-center">
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-outline-primary" data-user-id="${user.user_id}" title="Edit">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" data-user-id="${user.user_id}" title="Delete" hidden>
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </td>
        `;

        tbody.appendChild(tr);
    });
}

function loadUsers() {
    const filters = getFilterValues();
    perPage = filters.perPage;

    fetch(`/api/users-data?${buildQueryString()}`)
        .then(res => {
            if (!res.ok) throw new Error(`Server responded with ${res.status}`);
            return res.json();
        })
        .then(data => {
            if (!data.success) {
                throw new Error(data.error || 'Failed to fetch users');
            }

            renderUsers(data.users || []);
            updatePagination(data.total || 0, data.page || currentPage, data.per_page || perPage);
        })
        .catch(err => {
            console.error('Failed to load users:', err);
            document.getElementById('usersTableBody').innerHTML = '<tr><td colspan="6" class="text-center py-4">Unable to load users.</td></tr>';
            document.getElementById('usersShowingInfo').textContent = 'Unable to load users.';
            document.getElementById('usersPagination').innerHTML = '';
        });
}

function applyFilters() {
    currentPage = 1;
    loadUsers();
}

function clearFilters() {
    document.getElementById('userSearch').value = '';
    document.getElementById('statusFilter').value = '';
    document.getElementById('roleFilter').value = '';
    document.getElementById('pageSizeSelect').value = '10';
    currentPage = 1;
    loadUsers();
}

function showLoadingState(button, label) {
    button.dataset.originalLabel = button.innerHTML;
    button.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i> ${label}`;
    button.disabled = true;
}

function resetButtonState(button) {
    if (button.dataset.originalLabel) {
        button.innerHTML = button.dataset.originalLabel;
        delete button.dataset.originalLabel;
    }
    button.disabled = false;
}

function setupListeners() {
    document.getElementById('userSearch').addEventListener('input', () => {
        currentPage = 1;
        loadUsers();
    });

    document.getElementById('statusFilter').addEventListener('change', applyFilters);
    document.getElementById('roleFilter').addEventListener('change', applyFilters);
    document.getElementById('pageSizeSelect').addEventListener('change', () => {
        currentPage = 1;
        applyFilters();
    });
    document.getElementById('clearFilters').addEventListener('click', clearFilters);

    const refreshBtn = document.getElementById('refreshBtn');
    const exportBtn = document.getElementById('exportBtn');

    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            showLoadingState(refreshBtn, 'Refreshing...');
            loadUsers();
            setTimeout(() => resetButtonState(refreshBtn), 1000);
        });
    }

    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            showLoadingState(exportBtn, 'Exporting...');
            const link = document.createElement('a');
            link.href = '/api/export-users';
            link.download = '';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            setTimeout(() => resetButtonState(exportBtn), 500);
        });
    }

    document.getElementById('usersTableBody').addEventListener('click', e => {
        const editBtn = e.target.closest('.btn-outline-primary');
        const deleteBtn = e.target.closest('.btn-outline-danger');

        if (editBtn) {
            currentEditingUserId = editBtn.dataset.userId;
            fetch(`/api/get-user/${currentEditingUserId}`)
                .then(res => {
                    if (!res.ok) throw new Error(`Server responded with ${res.status}`);
                    return res.json();
                })
                .then(user => {
                    document.getElementById('editUserId').value = user.user_id;
                    document.getElementById('editFirstName').value = user.first_name;
                    document.getElementById('editLastName').value = user.last_name;
                    document.getElementById('editMiddleInitial').value = user.middle_name || '';
                    document.getElementById('editRole').value = user.role;
                    document.getElementById('editPhone').value = user.phone_number || '';
                    document.getElementById('editLaboratory').value = user.laboratory || '';
                    document.getElementById('editStatus').value = user.status;

                    new bootstrap.Modal(document.getElementById('editUserModal')).show();
                })
                .catch(err => {
                    console.error('Failed to load user:', err);
                    showAlert('danger', 'Unable to load user details.');
                });
        }

        if (deleteBtn) {
            const userId = deleteBtn.dataset.userId;
            fetch(`/api/get-user/${userId}`)
                .then(res => {
                    if (!res.ok) throw new Error(`Server responded with ${res.status}`);
                    return res.json();
                })
                .then(user => {
                    document.getElementById('deleteUserName').textContent = `${user.first_name} ${user.last_name}`;
                    const modalElement = document.getElementById('deleteUserModal');
                    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
                    modal.show();

                    const newConfirmBtn = document.getElementById('confirmDeleteUser');
                    newConfirmBtn.replaceWith(newConfirmBtn.cloneNode(true));
                    const clonedConfirmBtn = document.getElementById('confirmDeleteUser');

                    clonedConfirmBtn.addEventListener('click', function () {
                        showLoadingState(clonedConfirmBtn, 'Deleting...');
                        fetch(`/api/delete-user/${userId}`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ userId })
                        })
                            .then(async res => {
                                const data = await res.json();
                                if (!res.ok || !data.success) {
                                    throw new Error(data.error || `Server responded with ${res.status}`);
                                }
                                const modal = bootstrap.Modal.getInstance(document.getElementById('deleteUserModal'));
                                if (modal) modal.hide();
                                loadUsers();
                            })
                            .catch(err => {
                                console.error('Failed to delete user:', err);
                                showAlert('danger', 'Unable to delete user.');
                            })
                            .finally(() => resetButtonState(clonedConfirmBtn));
                    });
                })
                .catch(err => {
                    console.error('Failed to load user:', err);
                    showAlert('danger', 'Unable to load user details.');
                });
        }
    });

    document.getElementById('saveUserChanges').addEventListener('click', function () {
        const form = document.getElementById('editUserForm');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const editPhoneValue = document.getElementById('editPhone').value.trim();
        const userData = {
            userId: document.getElementById('editUserId').value,
            firstName: document.getElementById('editFirstName').value,
            lastName: document.getElementById('editLastName').value,
            middleInitial: document.getElementById('editMiddleInitial').value || '',
            phoneNumber: editPhoneValue ? normalizePhilippinePhone(editPhoneValue) : '',
            laboratory: document.getElementById('editLaboratory').value || '',
            role: document.getElementById('editRole').value,
            status: document.getElementById('editStatus').value
        };

        const button = this;
        showLoadingState(button, 'Saving...');

        fetch(`/api/update-user/${currentEditingUserId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        })
            .then(async res => {
                const data = await res.json();
                if (!res.ok || !data.success) {
                    throw new Error(data.error || 'Unable to update user.');
                }
                const modal = bootstrap.Modal.getInstance(document.getElementById('editUserModal'));
                if (modal) modal.hide();
                loadUsers();
                showAlert('success', 'User updated successfully!');
            })
            .catch(err => {
                console.error('Error updating user:', err);
                showAlert('danger', 'Failed to update user.');
            })
            .finally(() => resetButtonState(button));
    });

    document.getElementById('saveNewUser').addEventListener('click', function () {
        const addUserForm = document.getElementById('addUserForm');
        if (!addUserForm.checkValidity()) {
            addUserForm.reportValidity();
            return;
        }

        const addPhoneValue = document.getElementById('addPhone').value.trim();
        const userData = {
            userId: document.getElementById('addUserId').value,
            firstName: document.getElementById('addFirstName').value,
            lastName: document.getElementById('addLastName').value,
            middleInitial: document.getElementById('addMiddleInitial').value || '',
            phoneNumber: addPhoneValue ? normalizePhilippinePhone(addPhoneValue) : '',
            laboratory: document.getElementById('addLaboratory').value || '',
            role: document.getElementById('addRole').value
        };

        const button = this;
        showLoadingState(button, 'Adding...');

        fetch('/api/add-user', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        })
            .then(async res => {
                const data = await res.json();
                if (!res.ok || !data.success) {
                    throw new Error(data.error || 'Unable to add user.');
                }
                const modalEl = document.getElementById('addUserModal');
                const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
                modal.hide();
                document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
                document.body.classList.remove('modal-open');
                document.body.style.overflow = '';
                document.getElementById('addUserForm').reset();
                loadUsers();
                showAlert('success', 'User added successfully!');
            })
            .catch(err => {
                console.error('Error adding user:', err);
                showAlert('danger', 'Failed to add user.');
            })
            .finally(() => resetButtonState(button));
    });
}

document.addEventListener('DOMContentLoaded', function () {
    setupListeners();
    loadUsers();
});

document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        document.getElementById('userSearch').focus();
    }
});
