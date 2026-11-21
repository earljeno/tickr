/**
 * Tickr Base UI Interactions
 * Handles sidebar toggling, responsive overlays, active link tracking, accessible alert notifications,
 * and global fetch interceptor with a top-of-page indeterminate progress bar.
 */

// -----------------------------------------------------------------------------
// Global API Loading Progress Bar (Active on All Fetch Calls)
// -----------------------------------------------------------------------------
(function setupGlobalFetchLoader() {
    let activeRequests = 0;
    let loadingBarEl = null;

    function getLoadingBar() {
        if (!loadingBarEl) {
            loadingBarEl = document.getElementById("tickrGlobalLoadingBar");
            if (!loadingBarEl && document.body) {
                loadingBarEl = document.createElement("div");
                loadingBarEl.id = "tickrGlobalLoadingBar";
                loadingBarEl.setAttribute("aria-hidden", "true");
                loadingBarEl.setAttribute("role", "progressbar");
                loadingBarEl.setAttribute("aria-label", "Loading content...");
                document.body.prepend(loadingBarEl);
            }
        }
        return loadingBarEl;
    }

    function startLoading() {
        activeRequests++;
        const bar = getLoadingBar();
        if (bar) {
            bar.classList.add("active");
        }
    }

    function stopLoading() {
        activeRequests = Math.max(0, activeRequests - 1);
        if (activeRequests === 0) {
            const bar = getLoadingBar();
            if (bar) {
                bar.classList.remove("active");
            }
        }
    }

    // Intercept native window.fetch
    if (typeof window.fetch === "function") {
        const originalFetch = window.fetch;
        window.fetch = async function (...args) {
            startLoading();
            try {
                return await originalFetch.apply(this, args);
            } finally {
                stopLoading();
            }
        };
    }

    // Expose programmatic hooks if needed
    window.tickrStartLoading = startLoading;
    window.tickrStopLoading = stopLoading;
})();

document.addEventListener("DOMContentLoaded", () => {
    const sidebarToggler = document.getElementById("sidebarToggler");
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("overlay");
    const body = document.body;
    const main = document.querySelector(".main");

    if (sidebarToggler && sidebar) {
        const isMobile = () => window.innerWidth <= 768;

        const closeMobileSidebar = () => {
            sidebar.classList.remove("m-open");
            overlay?.classList.remove("active");
            body.style.overflow = "";
        };

        sidebarToggler.addEventListener("click", () => {
            if (isMobile()) {
                const isOpen = sidebar.classList.toggle("m-open");
                overlay?.classList.toggle("active", isOpen);
                body.style.overflow = isOpen ? "hidden" : "";
            } else {
                sidebar.classList.toggle("collapsed");
                main?.classList.toggle("sidebar-collapsed");
            }
        });

        overlay?.addEventListener("click", closeMobileSidebar);

        window.addEventListener("resize", () => {
            if (!isMobile()) {
                closeMobileSidebar();
            }
        });
    }

    // Active link detection based on pathname
    const currentPath = window.location.pathname;

    document.querySelectorAll(".sidebar-menu-button").forEach(link => {
        const href = link.getAttribute("href");
        if (href && href !== "javascript:void(0);" && !href.startsWith("#")) {
            // Check direct pathname match or prefix match for subpaths
            if (currentPath === href || (href !== "/admin/dashboard" && href !== "/" && currentPath.startsWith(href))) {
                link.classList.add("active");
                const parentItem = link.closest(".sidebar-menu-item");
                if (parentItem) {
                    parentItem.classList.add("open");
                }
            }
        }
    });

    // Submenu accordion toggle
    document.querySelectorAll(".sidebar-menu-button.has-children").forEach(button => {
        button.addEventListener("click", (e) => {
            e.preventDefault();
            const parent = button.closest(".sidebar-menu-item");
            if (parent) {
                const isOpen = parent.classList.toggle("open");
                button.setAttribute("aria-expanded", isOpen ? "true" : "false");
            }
        });
    });
});

/**
 * Escapes HTML characters safely for innerHTML rendering.
 */
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/**
 * Dispatches a high-contrast, accessible toast notification at the top right of the viewport.
 * Supports types: 'success', 'error', 'danger', 'warning', 'info'
 */
function showAlert(type, message) {
    if (!message && message !== 0) return;

    // Normalize type string
    const normType = String(type || '').toLowerCase();

    // Check if toast container exists, if not create one
    let container = document.getElementById("tickrToastContainer");
    if (!container) {
        container = document.createElement("div");
        container.id = "tickrToastContainer";
        container.className = "toast-container position-fixed top-0 end-0 p-3";
        container.style.zIndex = "1090";
        document.body.appendChild(container);
    }

    let bgClass = "bg-primary text-white";
    let iconClass = "bi-info-circle-fill";
    let closeBtnClass = "btn-close-white";

    if (normType === "success") {
        bgClass = "bg-success text-white";
        iconClass = "bi-check-circle-fill";
    } else if (normType === "error" || normType === "danger") {
        bgClass = "bg-danger text-white";
        iconClass = "bi-exclamation-triangle-fill";
    } else if (normType === "warning") {
        bgClass = "bg-warning text-dark";
        iconClass = "bi-exclamation-circle-fill";
        closeBtnClass = "";
    } else if (normType === "info") {
        bgClass = "bg-info text-dark";
        iconClass = "bi-info-circle-fill";
        closeBtnClass = "";
    }

    const toastEl = document.createElement("div");
    toastEl.className = `toast align-items-center ${bgClass} border-0 shadow-lg`;
    toastEl.setAttribute("role", "alert");
    toastEl.setAttribute("aria-live", "assertive");
    toastEl.setAttribute("aria-atomic", "true");

    const safeMessage = typeof escapeHtml === "function" ? escapeHtml(String(message)) : String(message);

    toastEl.innerHTML = `
        <div class="d-flex p-2">
            <div class="toast-body d-flex align-items-center gap-2">
                <i class="bi ${iconClass} fs-5"></i>
                <span class="fw-medium">${safeMessage}</span>
            </div>
            <button type="button" class="btn-close ${closeBtnClass} me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    container.appendChild(toastEl);
    if (window.bootstrap && bootstrap.Toast) {
        const toast = new bootstrap.Toast(toastEl, { delay: 4500 });
        toast.show();
    } else {
        toastEl.classList.add("show");
        setTimeout(() => toastEl.remove(), 4500);
    }

    toastEl.addEventListener("hidden.bs.toast", () => {
        toastEl.remove();
    });
}
