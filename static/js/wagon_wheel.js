// wagon_wheel.js
// Simple interactive wagon wheel with color mapping:
// 4 -> yellow, 6 -> red, other shots -> blue

(function(){
  const canvas = document.getElementById("wagonCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const size = Math.min(canvas.width, canvas.height);
  const cx = canvas.width/2, cy = canvas.height/2, radius = (size/2) - 10;

  function drawBase() {
    ctx.clearRect(0,0,canvas.width,canvas.height);
    // circle
    ctx.beginPath();
    ctx.arc(cx,cy,radius,0,Math.PI*2);
    ctx.fillStyle = "#ffffff";
    ctx.fill();
    ctx.strokeStyle = "#e6e9ef";
    ctx.stroke();
    // radial lines for reference
    for (let a=0; a<360; a+=30) {
      const rad = a * Math.PI/180;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(rad)*radius, cy + Math.sin(rad)*radius);
      ctx.strokeStyle = "#f3f4f6";
      ctx.stroke();
    }
  }

  function colorForRuns(r) {
    if (parseInt(r) === 4) return getComputedStyle(document.documentElement).getPropertyValue('--four-color') || '#f6c84c';
    if (parseInt(r) === 6) return getComputedStyle(document.documentElement).getPropertyValue('--six-color') || '#ef4444';
    return getComputedStyle(document.documentElement).getPropertyValue('--shot-color') || '#60a5fa';
  }

  // draw shots from global WAGON_SHOTS
  function drawShots() {
    drawBase();
    const shots = window.WAGON_SHOTS || [];
    shots.forEach(group => {
      group.shots.forEach(s => {
        const angle = (s.angle || 0) * Math.PI/180;
        const dist = (s.distance || (radius*0.8));
        const x = cx + Math.cos(angle) * dist;
        const y = cy + Math.sin(angle) * dist;

        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(x, y);
        ctx.strokeStyle = colorForRuns(s.runs);
        ctx.lineWidth = 3;
        ctx.stroke();

        // small circle at the end
        ctx.beginPath();
        ctx.arc(x, y, 6, 0, Math.PI*2);
        ctx.fillStyle = colorForRuns(s.runs);
        ctx.fill();

        // label (runs)
        ctx.font = "10px Inter, sans-serif";
        ctx.fillStyle = "#0f172a";
        ctx.fillText((s.runs || 0), x+8, y+4);
      });
    });
  }

  // click to select angle when 'startWagon' clicked
  let picking = false;
  document.getElementById("startWagon").addEventListener("click", function(){
    picking = !picking;
    this.textContent = picking ? "Click on wheel to record" : "Start Select Angle";
  });

  canvas.addEventListener("click", function(e){
    if (!picking) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const dx = mx - cx, dy = my - cy;
    let angle = Math.atan2(dy, dx) * 180 / Math.PI;
    if (angle < 0) angle += 360;
    const dist = Math.sqrt(dx*dx + dy*dy);

    // get selected player and run type
    const pid = parseInt(document.getElementById("wagonPlayer").value || 0);
    const runs = parseInt(document.getElementById("wagonRun").value || 0);
    const shot_type = document.getElementById("wagonShotType").value || "other";

    // store item
    addWagonShot(pid, { angle: Math.round(angle), distance: Math.round(dist), runs: runs, shot_type: shot_type });
    drawShots();
  });

  // expose draw function
  window.resetWagon = drawShots;
  // initial draw
  drawBase();
})();
