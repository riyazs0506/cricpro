/* ---------------------------------------------------------
   SCOREBOARD AUTO REFRESH (Used in dashboards)
--------------------------------------------------------- */

async function refreshScoreboard(matchId, elementId) {
    try {
        const res = await fetch(`/api/live/${matchId}/events`);
        const events = await res.json();

        if (!events || events.length === 0) return;

        let total = 0;
        let wickets = 0;

        events.forEach(b => {
            total += parseInt(b.runs);
            if (b.extras === "wide" || b.extras === "no_ball") {
                total += 1;
            }
            if (b.wicket !== "none") wickets++;
        });

        const last = events[events.length - 1];
        const overs = `${last.over}.${last.ball}`;

        const box = document.getElementById(elementId);
        if (!box) return;

        box.innerHTML = `
            <div class="score-num">${total}/${wickets}</div>
            <div class="text-muted small">Overs: ${overs}</div>
        `;

    } catch (err) {
        console.error("Scoreboard update error:", err);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const boards = document.querySelectorAll("[data-scoreboard]");

    boards.forEach(box => {
        const matchId = box.getAttribute("data-scoreboard");
        const elementId = box.id;

        refreshScoreboard(matchId, elementId);

        setInterval(() => {
            refreshScoreboard(matchId, elementId);
        }, 5000);
    });
});
