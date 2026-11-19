/**
 * Tickr Base UI Interactions
 * Handles sidebar toggling, responsive overlays, active link tracking, and accessible alert notifications.
 */

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
 */
function showAlert(type, message) {
    // Check if toast container exists, if not create one
    let container = document.getElementById("tickrToastContainer");
    if (!container) {
        container = document.createElement("div");
        container.id = "tickrToastContainer";
        container.className = "toast-container position-fixed top-0 end-0 p-3";
        container.style.zIndex = "1090";
        document.body.appendChild(container);
    }

    const isSuccess = type === "success";
    const bgClass = isSuccess ? "bg-success text-white" : "bg-danger text-white";
    const iconClass = isSuccess ? "bi-check-circle-fill" : "bi-exclamation-triangle-fill";

    const toastEl = document.createElement("div");
    toastEl.className = `toast align-items-center ${bgClass} border-0 shadow-lg`;
    toastEl.setAttribute("role", "alert");
    toastEl.setAttribute("aria-live", "assertive");
    toastEl.setAttribute("aria-atomic", "true");

    toastEl.innerHTML = `
        <div class="d-flex p-2">
            <div class="toast-body d-flex align-items-center gap-2">
                <i class="bi ${iconClass} fs-5"></i>
                <span class="fw-medium">${escapeHtml(message)}</span>
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    container.appendChild(toastEl);
    const toast = new bootstrap.Toast(toastEl, { delay: 4500 });
    toast.show();

    toastEl.addEventListener("hidden.bs.toast", () => {
        toastEl.remove();
    });
}
