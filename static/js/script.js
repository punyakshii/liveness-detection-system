// ==========================================================================
// CLIENT-SIDE BIOMETRICCONTROLLER
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
    // Stage transition controls
    const btnEnterPortal = document.getElementById("btn-enter-portal");
    const heroSec = document.getElementById("hero-sec");
    const portalSec = document.getElementById("portal-sec");
    const successSec = document.getElementById("success-sec");

    // Media & display elements
    const webcamStream = document.getElementById("webcam-stream");
    const systemStatusDot = document.getElementById("system-status-dot");
    const systemStatusText = document.getElementById("system-status-text");
    const scannerStatusBanner = document.getElementById("scanner-status-banner-id");
    const scanBannerText = document.getElementById("scan-banner-text");
    const laserElem = document.getElementById("scanner-laser-elem");

    // Form & Input elements
    const loginForm = document.getElementById("login-form");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const togglePassVisibility = document.getElementById("toggle-pass-visibility");
    const btnLoginSubmit = document.getElementById("btn-login-submit");
    const btnResetScans = document.getElementById("btn-reset-scans");
    const errorContainer = document.getElementById("error-container");
    const errorText = document.getElementById("error-text");

    // Diagnostics elements
    const chkBlink = document.getElementById("chk-blink");
    const chkLeft = document.getElementById("chk-left");
    const chkRight = document.getElementById("chk-right");
    const chkMouth = document.getElementById("chk-mouth");
    const livenessPercentage = document.getElementById("liveness-percentage");
    const livenessFill = document.getElementById("liveness-fill");
    const voiceTranscript = document.getElementById("voice-transcript");

    let statusInterval = null;
    let livenessUnlocked = false;

    // 1. Stage transition: landing → biometric scan panel (Phase 1 → Phase 2)
    btnEnterPortal.addEventListener("click", async () => {
        // Reset backend biometrics first
        try {
            await fetch('/reset_biometrics', { method: 'POST' });
        } catch (e) {
            console.error("Biometric reset failed on initialization", e);
        }

        // Visual transition: hero slides up, portal slides in
        heroSec.classList.add("hidden");
        portalSec.classList.add("active");

        // Activate webcam stream
        webcamStream.src = "/video";

        // Update top-bar status
        systemStatusDot.style.background = "#06b6d4";
        systemStatusDot.style.boxShadow = "0 0 8px rgba(6, 182, 212, 0.8)";
        systemStatusText.innerText = "Scanner Initiated";

        // Begin polling liveness metrics
        startBiometricPolling();
    });

    // 2. Toggle password visibility
    togglePassVisibility.addEventListener("click", () => {
        if (passwordInput.type === "password") {
            passwordInput.type = "text";
            togglePassVisibility.classList.remove("fa-eye-slash");
            togglePassVisibility.classList.add("fa-eye");
        } else {
            passwordInput.type = "password";
            togglePassVisibility.classList.remove("fa-eye");
            togglePassVisibility.classList.add("fa-eye-slash");
        }
    });

    // 3. Reset biometric scans
    btnResetScans.addEventListener("click", async () => {
        try {
            const res = await fetch('/reset_biometrics', { method: 'POST' });
            if (res.ok) {
                updateBadgeUI(chkBlink, false);
                updateBadgeUI(chkLeft, false);
                updateBadgeUI(chkRight, false);
                updateBadgeUI(chkMouth, false);

                livenessPercentage.innerText = "0%";
                livenessFill.style.width = "0%";
                voiceTranscript.innerText = "...";
                document.getElementById("val-emotion").innerText = "Neutral";
                document.getElementById("val-voice-state").innerText = "Listening";

                scanBannerText.innerText = "SCANNER RESET - READY";
                scannerStatusBanner.className = "scanner-status-banner";
                laserElem.style.animationPlayState = "running";

                checkLoginButtonUnlock();
            }
        } catch (e) {
            console.error("Failed to reset biometric state", e);
        }
    });

    // 4. Intercept form submit — fetch-based, triggers Phase 3 on success
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        // Show spinner while processing
        btnLoginSubmit.disabled = true;
        btnLoginSubmit.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Authenticating...`;

        const formData = new FormData(loginForm);

        try {
            const res = await fetch('/login', {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            const data = await res.json();

            if (data.success) {
                // Stop biometric polling
                if (statusInterval) clearInterval(statusInterval);

                // Populate Phase 3 operator name
                document.getElementById("phase3-username").innerText = usernameInput.value;

                // Update header to "Access Granted"
                systemStatusDot.style.background = "#10b981";
                systemStatusDot.style.boxShadow = "0 0 8px rgba(16, 185, 129, 0.8)";
                systemStatusText.innerText = "Access Granted";

                // Phase 2 → Phase 3: portal exits upward, success slides up
                portalSec.classList.add("exiting");
                portalSec.classList.remove("active");

                setTimeout(() => {
                    successSec.classList.add("active");
                }, 120);

                // Animate redirect progress bar, then navigate
                const redirectFill = document.getElementById("redirect-fill");
                const REDIRECT_DELAY = 3200;
                redirectFill.style.transition = `width ${REDIRECT_DELAY}ms linear`;
                setTimeout(() => { redirectFill.style.width = "100%"; }, 250);
                setTimeout(() => { window.location.href = data.redirect || "/"; }, REDIRECT_DELAY + 400);

            } else {
                // Show inline error, restore button
                errorText.innerText = data.error || "Authentication failed.";
                errorContainer.classList.add("active");
                checkLoginButtonUnlock();
            }

        } catch (err) {
            console.error("Login fetch error", err);
            errorText.innerText = "Network error. Please try again.";
            errorContainer.classList.add("active");
            checkLoginButtonUnlock();
        }
    });

    // 5. Biometric polling loop (Phase 2)
    function startBiometricPolling() {
        if (statusInterval) clearInterval(statusInterval);

        statusInterval = setInterval(async () => {
            try {
                const response = await fetch('/status');
                if (!response.ok) return;

                const data = await response.json();

                updateBadgeUI(chkBlink, data.blink);
                updateBadgeUI(chkLeft, data.left_turn);
                updateBadgeUI(chkRight, data.right_turn);
                updateBadgeUI(chkMouth, data.mouth_open);

                document.getElementById("val-emotion").innerText = data.emotion || "Neutral";
                document.getElementById("val-voice-state").innerText = data.voice_status || "Listening";

                const score = data.live_score || 0;
                livenessPercentage.innerText = `${score}%`;
                livenessFill.style.width = `${score}%`;

                if (data.voice_text && data.voice_text !== "...") {
                    voiceTranscript.innerText = data.voice_text;
                } else {
                    voiceTranscript.innerText = "Listening...";
                }

                if (score >= 50) {
                    livenessUnlocked = true;
                    scanBannerText.innerText = "SECURE - LIVE VERIFIED";
                    scannerStatusBanner.className = "scanner-status-banner verified";
                    laserElem.style.animationPlayState = "paused";

                    systemStatusDot.style.background = "#10b981";
                    systemStatusDot.style.boxShadow = "0 0 8px rgba(16, 185, 129, 0.8)";
                    systemStatusText.innerText = "Operator Verified";
                } else {
                    livenessUnlocked = false;
                    laserElem.style.animationPlayState = "running";

                    if (score > 0) {
                        scanBannerText.innerText = "EVALUATING GESTURES...";
                        scannerStatusBanner.className = "scanner-status-banner";
                        systemStatusDot.style.background = "#f59e0b";
                        systemStatusDot.style.boxShadow = "0 0 8px rgba(245, 158, 11, 0.8)";
                        systemStatusText.innerText = "Verification In Progress";
                    } else {
                        scanBannerText.innerText = "POSITION FACE IN RADAR";
                        scannerStatusBanner.className = "scanner-status-banner";
                        systemStatusDot.style.background = "#06b6d4";
                        systemStatusDot.style.boxShadow = "0 0 8px rgba(6, 182, 212, 0.8)";
                        systemStatusText.innerText = "Awaiting Subject";
                    }
                }

                checkLoginButtonUnlock();

            } catch (err) {
                console.error("Error polling biometric status", err);
            }
        }, 300);
    }

    // 6. Helper: update checklist badge UI
    function updateBadgeUI(badgeElem, isVerified) {
        const spanText = badgeElem.querySelector("span");
        const icon = badgeElem.querySelector("i");

        if (isVerified) {
            badgeElem.classList.remove("pending");
            badgeElem.classList.add("verified");
            spanText.innerText = "YES";
            icon.className = "fa-solid fa-circle-check";
        } else {
            badgeElem.classList.remove("verified");
            badgeElem.classList.add("pending");
            spanText.innerText = "NO";
            icon.className = "fa-regular fa-circle";
        }
    }

    // 7. Enable/disable login button based on form + liveness state
    function checkLoginButtonUnlock() {
        const usernameFilled = usernameInput.value.trim().length > 0;
        const passwordFilled = passwordInput.value.length > 0;

        if (usernameFilled && passwordFilled && livenessUnlocked) {
            btnLoginSubmit.disabled = false;
            btnLoginSubmit.classList.add("unlocked");
            btnLoginSubmit.innerHTML = `<i class="fa-solid fa-lock-open"></i> AUTHORIZE & ENTER`;
        } else {
            btnLoginSubmit.disabled = true;
            btnLoginSubmit.classList.remove("unlocked");
            btnLoginSubmit.innerHTML = `<i class="fa-solid fa-lock"></i> Biometric Locked`;
        }
    }

    // Input listeners
    usernameInput.addEventListener("input", checkLoginButtonUnlock);
    passwordInput.addEventListener("input", checkLoginButtonUnlock);
});