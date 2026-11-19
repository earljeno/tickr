/**
 * Tickr Client-Side Inactivity Auto-Logout Tracker
 *
 * Monitors real user interactions (mouse movement, clicks, keystrokes, touches, scrolls)
 * and logs out inactive sessions to protect shared kiosks and administrative consoles.
 * Shows an accessible warning countdown modal prior to terminating the session.
 */

(function () {
    'use strict';

    // Only run if user is authenticated (indicated by config or body attribute)
    const configEl = document.getElementById('tickrInactivityConfig');
    const logoutUrl = configEl?.dataset?.logoutUrl || '/auth/logout';
    
    // Default timeouts:
    // timeoutSec: Total idle seconds before auto-logout (e.g. 300s = 5m, or 120s for GIA kiosk)
    // warningSec: Warning prompt duration in seconds prior to logout (e.g. 30s)
    const timeoutSec = parseInt(configEl?.dataset?.timeoutSec || '300', 10);
    const warningSec = parseInt(configEl?.dataset?.warningSec || '30', 10);

    if (isNaN(timeoutSec) || timeoutSec <= 0) return;

    let lastActivityTimestamp = Date.now();
    let warningModal = null;
    let warningCountdownInterval = null;
    let checkInterval = null;
    let isWarningShown = false;
    let throttleTimeout = null;

    /**
     * Create and inject the accessible Inactivity Warning Modal if not already in DOM.
     */
    function createWarningModal() {
        let modalEl = document.getElementById('inactivityWarningModal');
        if (!modalEl) {
            modalEl = document.createElement('div');
            modalEl.id = 'inactivityWarningModal';
            modalEl.className = 'modal fade';
            modalEl.tabIndex = -1;
            modalEl.setAttribute('aria-labelledby', 'inactivityModalLabel');
            modalEl.setAttribute('aria-describedby', 'inactivityModalDesc');
            modalEl.setAttribute('aria-hidden', 'true');
            modalEl.setAttribute('data-bs-backdrop', 'static');
            modalEl.setAttribute('data-bs-keyboard', 'false');

            modalEl.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content border-0 shadow-lg" style="border-radius: 1rem; overflow: hidden;">
                        <div class="modal-body p-4 text-center">
                            <div class="mb-3 d-inline-flex align-items-center justify-content-center rounded-circle bg-warning-subtle text-warning" style="width: 64px; height: 64px;">
                                <i class="bi bi-clock-history fs-1" aria-hidden="true"></i>
                            </div>
                            <h5 class="fw-bold text-dark mb-2" id="inactivityModalLabel">Session Inactivity Warning</h5>
                            <p class="text-muted mb-4 small" id="inactivityModalDesc">
                                You have been inactive for a while. For security reasons, you will be automatically logged out in 
                                <span id="inactivityCountdownTimer" class="fw-bold text-danger font-mono fs-6" aria-live="polite">30</span> seconds.
                            </p>
                            <div class="d-flex flex-column flex-sm-row gap-2 justify-content-center">
                                <button type="button" class="btn btn-primary px-4 py-2 fw-semibold" id="stayLoggedInBtn">
                                    <i class="bi bi-person-check me-1" aria-hidden="true"></i> Stay Logged In
                                </button>
                                <a href="${logoutUrl}" class="btn btn-outline-secondary px-4 py-2 fw-medium" id="logoutNowBtn">
                                    <i class="bi bi-box-arrow-right me-1" aria-hidden="true"></i> Log Out Now
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modalEl);

            const stayBtn = modalEl.querySelector('#stayLoggedInBtn');
            if (stayBtn) {
                stayBtn.addEventListener('click', () => {
                    dismissWarningAndReset();
                });
            }
        }

        if (window.bootstrap && window.bootstrap.Modal) {
            warningModal = new window.bootstrap.Modal(modalEl, {
                backdrop: 'static',
                keyboard: false
            });
        }
        return modalEl;
    }

    /**
     * Resets activity timestamp (throttled to avoid performance overhead on rapid mouse movements).
     */
    function recordActivity() {
        const now = Date.now();
        // If warning is not active, throttle updating timestamp
        if (!isWarningShown) {
            if (!throttleTimeout) {
                lastActivityTimestamp = now;
                throttleTimeout = setTimeout(() => {
                    throttleTimeout = null;
                }, 500);
            }
        }
    }

    /**
     * User explicitly pressed "Stay Logged In" or interacted while warning was up.
     */
    function dismissWarningAndReset() {
        lastActivityTimestamp = Date.now();
        if (isWarningShown) {
            isWarningShown = false;
            clearInterval(warningCountdownInterval);
            if (warningModal) {
                warningModal.hide();
            }
        }
    }

    /**
     * Performs automatic logout redirection.
     */
    function executeAutoLogout() {
        clearInterval(checkInterval);
        clearInterval(warningCountdownInterval);
        // Redirect to logout endpoint
        window.location.href = logoutUrl;
    }

    /**
     * Shows the inactivity warning dialog with live countdown.
     */
    function triggerWarning() {
        isWarningShown = true;
        const modalEl = createWarningModal();
        const countdownEl = document.getElementById('inactivityCountdownTimer');
        
        let remainingSeconds = warningSec;
        if (countdownEl) countdownEl.textContent = String(remainingSeconds);

        if (warningModal) {
            warningModal.show();
        }

        clearInterval(warningCountdownInterval);
        warningCountdownInterval = setInterval(() => {
            remainingSeconds--;
            if (countdownEl) {
                countdownEl.textContent = String(Math.max(0, remainingSeconds));
            }
            if (remainingSeconds <= 0) {
                clearInterval(warningCountdownInterval);
                executeAutoLogout();
            }
        }, 1000);
    }

    /**
     * Periodically checks elapsed idle time.
     */
    function checkInactivity() {
        if (isWarningShown) return;

        const idleMs = Date.now() - lastActivityTimestamp;
        const idleSec = Math.floor(idleMs / 1000);

        const warningThresholdSec = timeoutSec - warningSec;

        if (idleSec >= timeoutSec) {
            executeAutoLogout();
        } else if (idleSec >= warningThresholdSec) {
            triggerWarning();
        }
    }

    /**
     * Initialize listeners for relevant user activity:
     * - mousemove, mousedown: mouse movements and clicks
     * - keydown: keyboard input
     * - scroll, wheel: scrolling actions
     * - touchstart, touchmove: mobile/touch screen actions
     */
    function initListeners() {
        const activityEvents = [
            'mousemove',
            'mousedown',
            'keydown',
            'scroll',
            'touchstart',
            'touchmove',
            'wheel'
        ];

        activityEvents.forEach(eventType => {
            window.addEventListener(eventType, recordActivity, { passive: true });
        });

        // Initialize checking interval (every 1 second)
        checkInterval = setInterval(checkInactivity, 1000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            createWarningModal();
            initListeners();
        });
    } else {
        createWarningModal();
        initListeners();
    }
})();
