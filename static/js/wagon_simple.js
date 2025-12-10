(function () {

const canvas = document.getElementById("wagonCanvas");

let clickX = 0, clickY = 0;

function addLabels() {
    const labels = [
        ["Cover", 80, 140],
        ["Extra Cover", 130, 100],
        ["Mid-off", 260, 60],
        ["Long-off", 260, 40],
        ["Straight", 260, 260],
        ["Long-on", 260, 480],
        ["Mid-on", 260, 440],
        ["Square Leg", 430, 330],
        ["Fine Leg", 480, 260],
        ["Third Man", 80, 260],
        ["Point", 120, 200]
    ];

    labels.forEach(l => {
        const el = document.createElement("div");
        el.className = "label";
        el.style.left = l[1] + "px";
        el.style.top = l[2] + "px";
        el.innerText = l[0];
        canvas.appendChild(el);
    });
}

function drawDot(angle, distance, runs) {
    const cx = canvas.clientWidth / 2;
    const cy = canvas.clientHeight / 2;

    const rad = angle * Math.PI / 180;

    // normalize distance
    const maxDist = 500;
    const useDist = Math.min(distance / maxDist * (cx - 20), cx - 20);

    const x = cx + Math.cos(rad) * useDist;
    const y = cy - Math.sin(rad) * useDist;

    const dot = document.createElement("div");
    dot.className = "dot";
    dot.style.left = x + "px";
    dot.style.top = y + "px";

    if (runs == 4) dot.style.background = "blue";
    else if (runs == 6) dot.style.background = "red";
    else dot.style.background = "black";

    canvas.appendChild(dot);
}

// Convert click to polar angle/distance
function convertToPolar(x, y) {
    const cx = canvas.clientWidth / 2;
    const cy = canvas.clientHeight / 2;

    const dx = x - cx;
    const dy = cy - y;

    const angle = (Math.atan2(dy, dx) * 180 / Math.PI + 360) % 360;
    const dist = Math.sqrt(dx*dx + dy*dy) * 2.5;

    return {angle, dist};
}

// Register click
canvas.addEventListener("click", (e) => {
    const rect = canvas.getBoundingClientRect();
    clickX = e.clientX - rect.left;
    clickY = e.clientY - rect.top;

    new bootstrap.Modal(document.getElementById("shotModal")).show();
});

// Save shot
document.getElementById("saveShotBtn").addEventListener("click", async () => {
    const type = document.getElementById("shot_type").value;
    const runs = Number(document.getElementById("runs").value);

    const polar = convertToPolar(clickX, clickY);

    // save on UI
    drawDot(polar.angle, polar.dist, runs);

    // send API
    await fetch(`/api/wagon/${matchId}/${playerId}/add`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            angle: polar.angle,
            distance: polar.dist,
            runs: runs,
            shot_type: type
        })
    });

    bootstrap.Modal.getInstance(document.getElementById("shotModal")).hide();
});

// Load existing shots
savedShots.forEach(s => {
    drawDot(s.angle, s.distance, s.runs);
});

addLabels();

})();
