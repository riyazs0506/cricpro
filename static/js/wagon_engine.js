// static/js/wagon_engine.js
// 4-camera synchronized wagon engine (Smooth Physics Arc)
// Requires these elements in the page:
//  - canvases: cam_side, cam_top, cam_front, cam_bat
//  - wagonWheel (div), shot_list (div)
//  - btn_example, shot_type, runs_box
// Also expects global variables set by template: matchId, playerId, shots (array of dicts)

(function () {
  // -------------------
  // Utilities
  // -------------------
  function $(id) { return document.getElementById(id); }

  // safe clone
  function clone(obj) { return JSON.parse(JSON.stringify(obj || {})); }

  // linear / ease helpers
  function lerp(a, b, t) { return a + (b - a) * t; }
  function easeOutCubic(t) { return (--t) * t * t + 1; }

  // -------------------
  // Canvas setup
  // -------------------
  const canvases = {
    side: $('cam_side'),
    top: $('cam_top'),
    front: $('cam_front'),
    bat: $('cam_bat')
  };

  Object.values(canvases).forEach(c => {
    // set internal resolution for crispness
    const rect = c.getBoundingClientRect();
    c.width = Math.floor(rect.width * 1.0);
    c.height = Math.floor(rect.height * 1.0);
  });

  const ctx = {
    side: canvases.side.getContext('2d'),
    top: canvases.top.getContext('2d'),
    front: canvases.front.getContext('2d'),
    bat: canvases.bat.getContext('2d'),
  };

  // Stage metrics (logical coordinates)
  const STAGE = {
    // origin (0,0) at left-bottom for the "side" view simulation
    width: canvases.side.width,
    height: canvases.side.height,
    batsmanX: Math.floor(canvases.side.width * 0.15),
    batsmanY: Math.floor(canvases.side.height * 0.75)
  };

  // Wagon wheel element (top-view markers)
  const wagon = $('wagonWheel');
  const shotListEl = $('shot_list');

  // persisted shots (from template) -> ensure JS-friendly
  let savedShots = Array.isArray(window.shots) ? clone(window.shots) : [];

  // visual config mapping
  const runColor = r => r >= 6 ? '#d32f2f' : (r >= 4 ? '#1e6bff' : '#444');

  // -------------------
  // Drawing helpers
  // -------------------
  function clearAllCanvases() {
    Object.values(ctx).forEach(c => {
      c.clearRect(0, 0, c.canvas.width, c.canvas.height);
    });
  }

  // draws fixed reference: pitch and batsman marker for each canvas
  function drawReferences() {
    // SIDE view: grass gradient + pitch + batsman
    const c = ctx.side;
    const W = c.canvas.width, H = c.canvas.height;
    // background
    const g = c.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, '#0f5b1e');
    g.addColorStop(0.55, '#4aa33c');
    g.addColorStop(1, '#8bd88a');
    c.fillStyle = g;
    c.fillRect(0, 0, W, H);
    // pitch
    c.fillStyle = '#d9c39a';
    const pitchW = Math.floor(W * 0.14), pitchH = Math.floor(H * 0.03);
    c.fillRect(STAGE.batsmanX - 20, STAGE.batsmanY - pitchH / 2, pitchW, pitchH);
    // batsman marker
    c.fillStyle = '#ffffffcc';
    c.fillRect(STAGE.batsmanX + 14, STAGE.batsmanY - 46, 18, 46);

    // TOP view: simple turf background and center
    const ct = ctx.top;
    ct.fillStyle = '#e9f2e9';
    ct.fillRect(0, 0, ct.canvas.width, ct.canvas.height);
    ct.fillStyle = '#d0e8d0';
    const r = Math.min(ct.canvas.width, ct.canvas.height) / 2;
    ct.beginPath(); ct.arc(ct.canvas.width/2, ct.canvas.height/2, r, 0, Math.PI*2); ct.fill();

    // FRONT view: darker grass + pitch line center
    const cf = ctx.front;
    const Wf = cf.canvas.width, Hf = cf.canvas.height;
    const gf = cf.createLinearGradient(0, 0, 0, Hf);
    gf.addColorStop(0, '#083d14');
    gf.addColorStop(1, '#1b6a2b');
    cf.fillStyle = gf; cf.fillRect(0, 0, Wf, Hf);
    cf.fillStyle = '#d9c39a';
    cf.fillRect(Wf/2 - 30, Hf*0.58, 60, 6);

    // BATSMAN POV: subtle pitch & sightlines
    const cb = ctx.bat;
    cb.fillStyle = '#eaf7ea'; cb.fillRect(0,0,cb.canvas.width, cb.canvas.height);
    cb.strokeStyle = '#c0d7c0'; cb.beginPath(); cb.moveTo(0, cb.canvas.height*0.7); cb.lineTo(cb.canvas.width, cb.canvas.height*0.7); cb.stroke();
  }

  // wagon wheel plotting
  function drawWagonWheel() {
    wagon.innerHTML = '';
    const W = wagon.clientWidth, H = wagon.clientHeight;
    // rings
    const rings = [0.25, 0.5, 0.75, 1];
    rings.forEach(r => {
      const el = document.createElement('div');
      el.style.position = 'absolute';
      el.style.width = `${W*r}px`;
      el.style.height = `${H*r}px`;
      el.style.left = `${(W - W*r)/2}px`;
      el.style.top = `${(H - H*r)/2}px`;
      el.style.border = '1px dashed rgba(0,0,0,0.07)';
      el.style.borderRadius = '50%';
      wagon.appendChild(el);
    });

    // shots
    savedShots.forEach((s, idx) => {
      const pos = polarToWheel(s.angle || Math.random()*360, s.distance || 200);
      const dot = document.createElement('div');
      dot.className = 'wDot';
      dot.style.left = `${pos.x}px`;
      dot.style.top = `${pos.y}px`;
      dot.style.background = runColor(s.runs || 0);
      dot.title = `${s.runs || 0} runs — ${s.shot_type || ''}`;
      dot.style.transform = 'translate(-50%, -50%)';
      wagon.appendChild(dot);
    });
  }

  // map polar to wheel coords (used previously in template design)
  function polarToWheel(angleDeg, distance) {
    const W = wagon.clientWidth, H = wagon.clientHeight;
    const cx = W/2, cy = H/2;
    const maxDistance = 700;
    const r = Math.min(distance / maxDistance * (W/2 - 18), (W/2 - 18));
    const rad = angleDeg * Math.PI / 180;
    const x = cx + r * Math.cos(rad);
    const y = cy - r * Math.sin(rad);
    return { x, y };
  }

  // update saved shot list UI
  function populateShotList() {
    shotListEl.innerHTML = '';
    savedShots.forEach((s, i) => {
      const row = document.createElement('div');
      row.className = 'shot-item';
      row.style.display = 'flex';
      row.style.justifyContent = 'space-between';
      row.style.alignItems = 'center';
      row.style.background = '#fff';
      row.style.padding = '8px';
      row.style.marginBottom = '6px';
      row.style.borderRadius = '6px';
      row.innerHTML = `
        <div><strong>${s.shot_type || 'Shot'}</strong><br><small>${s.runs} runs • angle ${Math.round(s.angle||0)}°</small></div>
        <div>
          <button class="btn btn-sm btn-outline-primary replay" data-i="${i}">Replay</button>
        </div>`;
      shotListEl.appendChild(row);
    });

    // attach replays
    shotListEl.querySelectorAll('.replay').forEach(btn => {
      btn.addEventListener('click', e => {
        const idx = Number(e.currentTarget.dataset.i);
        const s = savedShots[idx];
        if (s) playShotSynced(s);
      });
    });
  }

  // -------------------
  // Shot physics & synchronized animation
  // -------------------
  // We'll compute a normalized path (0..1) then render each view's projection of that path.
  function generatePath(angle, distance, runs, shotType) {
    // Path sample points with simple physics-like param
    const points = [];
    const steps = 60; // smoothness
    // base start = batsman pos
    const sx = STAGE.batsmanX;
    const sy = STAGE.batsmanY;
    // map distance to pixel offset
    const pxDistance = Math.min(distance * 0.9, STAGE.width * 0.75);
    const rad = angle * Math.PI / 180;
    const ex = sx + Math.cos(rad) * pxDistance;
    const ey = sy - Math.sin(rad) * (pxDistance * 0.14) - (pxDistance * 0.03);
    // height curve influenced by shot type
    const Hmap = { Drive: 50, Pull: 140, Cut: 40, Flick: 80, Uppercut: 170, Lofted: 200 };
    const H = Hmap[shotType] || 80;

    for (let i = 0; i <= steps; i++) {
      const t = i / steps; // 0..1
      // quadratic / bezier blend
      const mx = lerp(sx, ex, t);
      const my = lerp(sy, ey, t);
      const arc = Math.sin(t * Math.PI) * H * (1 - (Math.abs(t - 0.5) * 0.4));
      points.push({ x: mx, y: my - arc, z: arc, t });
    }
    return points;
  }

  // Render a single frame: draw ball on each canvas using projection rules
  function renderFrame(points, frameIndex) {
    // clear only dynamic overlays (we keep references static)
    // We'll redraw dynamic layers each frame
    // Redraw static refs first
    drawReferences();

    // which point to draw at frameIndex
    const p = points[Math.min(frameIndex, points.length - 1)];

    // SIDE: draw small trail + ball (side is already in STAGE coordinates)
    const cs = ctx.side;
    // subtle trail
    cs.fillStyle = 'rgba(255,255,255,0.05)';
    cs.beginPath();
    cs.arc(p.x, p.y + 2, 6, 0, Math.PI*2);
    cs.fill();
    // ball
    cs.beginPath();
    cs.fillStyle = '#ff6b6b';
    cs.ellipse(p.x, p.y, 8, 8, 0, 0, Math.PI*2);
    cs.fill();
    cs.shadowColor = 'rgba(0,0,0,0.35)';
    cs.shadowBlur = 8;

    // TOP view: map path onto top-plane (x,z) with scaling
    const ct = ctx.top;
    // center in top canvas
    const cx = ct.canvas.width / 2;
    const cy = ct.canvas.height / 2;
    const maxR = Math.min(cx, cy) - 20;
    // convert pxDistance to radius mapping (approx)
    const relR = (Math.sqrt(Math.pow(p.x - STAGE.batsmanX,2) + Math.pow(STAGE.batsmanY - p.y,2)));
    const r = Math.min(maxR * (relR / (STAGE.width * 0.75)), maxR);
    const angleRad = Math.atan2(STAGE.batsmanY - p.y, p.x - STAGE.batsmanX);
    const tx = cx + r * Math.cos(angleRad);
    const ty = cy - r * Math.sin(angleRad);

    ct.fillStyle = runColor(0);
    // trail dot
    ct.beginPath(); ct.arc(tx, ty, 5, 0, Math.PI*2); ct.fill();
    // ball
    ct.fillStyle = '#ff6b6b';
    ct.beginPath(); ct.arc(tx, ty, 7, 0, Math.PI*2); ct.fill();

    // FRONT view: project using x => horizontal, z => vertical (fake)
    const cf = ctx.front;
    const fx = lerp(cf.canvas.width * 0.5, cf.canvas.width * 0.9, (p.x - STAGE.batsmanX) / (STAGE.width * 0.8));
    const fz = Math.max(6, p.z * 0.14);
    cf.beginPath(); cf.fillStyle = '#ff6b6b'; cf.ellipse(fx, cf.canvas.height * 0.55 - fz, 7, 7, 0, 0, Math.PI*2); cf.fill();

    // BATSMAN POV: small offsetting left-right based on angle
    const cb = ctx.bat;
    const vx = lerp(cb.canvas.width * 0.45, cb.canvas.width * 0.9, (p.x - STAGE.batsmanX) / (STAGE.width * 0.6));
    const vz = Math.max(4, p.z * 0.12);
    cb.beginPath(); cb.fillStyle = '#ff6b6b'; cb.ellipse(vx, cb.canvas.height * 0.62 - vz, 8, 8, 0, 0, Math.PI*2); cb.fill();

    // draw small shadows where ball lands (when frame close to end)
    if (p.t > 0.95) {
      // side shadow
      cs.beginPath(); cs.fillStyle = 'rgba(0,0,0,0.25)'; cs.ellipse(p.x, STAGE.batsmanY + 8, 20, 6, 0, 0, Math.PI*2); cs.fill();
    }
  }

  // play shot across all canvases synchronously
  function playShotSynced(shot) {
    const angle = Number(shot.angle || (Math.random()*360));
    const distance = Number(shot.distance || 300);
    const runs = Number(shot.runs || 0);
    const type = shot.shot_type || 'Drive';

    const path = generatePath(angle, distance, runs, type);
    let idx = 0;
    const fps = 60;
    const interval = Math.round(1000 / fps);

    // clear references and draw static immediately
    clearAllCanvases();
    drawReferences();

    // small fade effect
    const timer = setInterval(() => {
      // clear dynamic overlays by redrawing static layer first
      clearAllCanvases();
      drawReferences();
      renderFrame(path, idx);

      idx++;
      if (idx >= path.length) {
        clearInterval(timer);
        // after play, mark wheel dot persistently
        savedShots.push({ angle, distance, runs, shot_type: type });
        drawWagonWheel();
        populateShotList();
        // persist on server
        apiSaveShot(angle, distance, runs, type);
      }
    }, interval);
  }

  // -------------------
  // API save
  // -------------------
  async function apiSaveShot(angle, distance, runs, shot_type) {
    try {
      await fetch(`/api/wagon/${matchId}/${playerId}/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ angle, distance, runs, shot_type })
      });
    } catch (err) {
      console.error('Failed to save shot', err);
    }
  }

  // -------------------
  // Example shot helper
  // -------------------
  function sampleAngle() { return Math.floor(Math.random() * 140) + 10; }
  function sampleDistanceForRuns(runs) {
    if (runs >= 6) return 680;
    if (runs >= 4) return 480;
    if (runs === 3) return 320;
    if (runs === 2) return 240;
    if (runs === 1) return 160;
    return 120;
  }

  // -------------------
  // Initialization
  // -------------------
  function init() {
    drawReferences();
    drawWagonWheel();
    populateShotList();

    // bind example button
    const btn = $('btn_example');
    if (btn) {
      btn.addEventListener('click', () => {
        const type = $('shot_type').value;
        const runs = Number($('runs_box').value);
        const ang = sampleAngle();
        const dist = sampleDistanceForRuns(runs) * (1 + (Math.random() * 0.12 - 0.06));
        playShotSynced({ angle: ang, distance: dist, runs, shot_type: type });
      });
    }

    // if there are saved shots, draw wheel and list already
    drawWagonWheel();
    populateShotList();
  }

  // start
  init();

  // expose for debugging
  window._wagonEngine = {
    playShotSynced,
    savedShots,
    redraw: () => { drawReferences(); drawWagonWheel(); populateShotList(); }
  };

})();
