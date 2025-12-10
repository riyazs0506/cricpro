// ----------------------------------------------------
// GLOBAL JAVASCRIPT FOR CRICPRO
// ----------------------------------------------------

console.log("CricPro JS Loaded");

// ----------------------------------------------------
// Auto Back Button
// ----------------------------------------------------
function goBack() {
    if (document.referrer !== "") {
        window.history.back();
    } else {
        window.location.href = "/";
    }
}

// ----------------------------------------------------
// Highlight Active Navbar Item
// ----------------------------------------------------
document.addEventListener("DOMContentLoaded", function () {
    let navLinks = document.querySelectorAll(".nav-link");
    let currentURL = window.location.pathname;

    navLinks.forEach(link => {
        if (link.getAttribute("href") === currentURL) {
            link.classList.add("active");
        }
    });
});

// ----------------------------------------------------
// Future Feature Placeholder: Live Scoring System
// ----------------------------------------------------
function recordBall(run, wicket=false, extra=0) {
    console.log("Ball recorded:", {
        run: run,
        wicket: wicket,
        extra: extra
    });

    // Future AJAX support:
    // fetch("/live/update", { method: "POST", body: JSON.stringify({...}) })
}

// ----------------------------------------------------
// Form Enhancements (Optional)
// ----------------------------------------------------
document.addEventListener("DOMContentLoaded", function () {
    const selects = document.querySelectorAll("select");

    selects.forEach(sel => {
        sel.addEventListener("change", () => {
            sel.classList.add("changed");
        });
    });
});

// ----------------------------------------------------
// Scroll to Flash Messages
// ----------------------------------------------------
window.onload = function() {
    let alerts = document.querySelector(".alert");
    if (alerts) {
        alerts.scrollIntoView({ behavior: "smooth" });
    }
};
