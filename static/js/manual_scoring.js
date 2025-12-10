/* manual_scoring.js (copy/paste - replace existing file)
 *
 * Updated to:
 * - follow FIRST / SECOND innings show/hide rules
 * - only render rows when section is visible (so player inputs show)
 * - improved UI wiring and overview computation
 * - works with the template you provided (ids: addBatsmanBtn, addBowlerBtn, addFieldingBtn, clearWagonBtn, saveManualBtn)
 *
 * Assumes window.MS_PLAYERS = [{id, name}, ...] and window.MATCH exists (simple fields only).
 ***************************************************************************/

window.MS_PLAYERS = window.MS_PLAYERS || [];
window.WAGON_SHOTS = window.WAGON_SHOTS || [];

function $id(id) { return document.getElementById(id); }

function buildPlayerOptionsHTML(selectedId) {
  return window.MS_PLAYERS.map(function(p) {
    const sel = (selectedId != null && selectedId === p.id) ? "selected" : "";
    return `<option value="${p.id}" ${sel}>${escapeHtml(p.name)}</option>`;
  }).join("");
}

function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  return String(s).replace(/[&<>"'`=\/]/g, function (c) {
    return {
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',
      "'": '&#39;', '/': '&#x2F;', '`': '&#x60;', '=': '&#x3D;'
    }[c];
  });
}

function addBattingRow(existing) {
  const tbody = document.getElementById("batting-container");
  if (!tbody) return;

  const playerId = existing?.player_id || "";
  const runs = existing?.runs ?? "";
  const balls = existing?.balls ?? "";
  const fours = existing?.fours ?? "";
  const sixes = existing?.sixes ?? "";
  const is_out = existing?.is_out ? "1" : "0";
  const dismissal = existing?.dismissal_type || "";
  const wicket_over = existing?.wicket_over ?? "";
  const wicket_ball = existing?.wicket_ball ?? "";

  const tr = document.createElement("tr");
  tr.className = "batting-row";

  tr.innerHTML = `
    <td rowspan="2">
      <select class="form-select player-id">
        ${buildPlayerOptionsHTML(playerId)}
      </select>
    </td>

    <td><input type="number" class="form-control score-input runs" value="${runs}" placeholder="0"></td>
    <td><input type="number" class="form-control score-input balls" value="${balls}" placeholder="0"></td>
    <td><input type="number" class="form-control score-input fours" value="${fours}" placeholder="0"></td>
    <td><input type="number" class="form-control score-input sixes" value="${sixes}" placeholder="0"></td>

    <td>
      <select class="form-select is_out">
        <option value="0" ${is_out=="0"?"selected":""}>No</option>
        <option value="1" ${is_out=="1"?"selected":""}>Yes</option>
      </select>
    </td>

    <td rowspan="2">
      <button class="btn btn-danger remove-row">X</button>
    </td>
  `;

  const tr2 = document.createElement("tr");
  tr2.className = "batting-row-details";

  tr2.innerHTML = `
    <td colspan="2">
      <select class="form-select dismissal_type">
        <option value="">Dismissal Type</option>
        <option value="bowled">Bowled</option>
        <option value="caught">Caught</option>
        <option value="run_out">Run Out</option>
        <option value="lbw">LBW</option>
        <option value="stumped">Stumped</option>
        <option value="hit_wicket">Hit Wicket</option>
        <option value="retired_hurt">Retired Hurt</option>
      </select>
    </td>

    <td>
      <input type="number" class="form-control score-input wicket_over" placeholder="Over" value="${wicket_over}">
    </td>

    <td>
      <input type="number" class="form-control score-input wicket_ball" placeholder="Ball" value="${wicket_ball}">
    </td>

    <td></td>
  `;

  tbody.appendChild(tr);
  tbody.appendChild(tr2);

  // remove row
  tr.querySelector(".remove-row").onclick = () => {
    tr.remove();
    tr2.remove();
  };
}





/* ---------- BOWLING (table row) ---------- */
function addBowlingRow(existing) {
  const tbody = $id("bowling-container");
  if (!tbody) return;

  const row = document.createElement("tr");
  row.className = "bowling-row align-middle";

  const pid = existing?.player_id || "";
  const overs = existing?.overs ?? "";
  const runs = existing?.runs_conceded ?? "";
  const wkts = existing?.wickets ?? "";

  row.innerHTML = `
    <td style="min-width:160px;"><select class="form-select form-select-sm b-player-id">${buildPlayerOptionsHTML(pid)}</select></td>
    <td><input class="form-control form-control-sm overs" type="text" value="${overs}"></td>
    <td><input class="form-control form-control-sm bruns" type="number" value="${runs}"></td>
    <td><input class="form-control form-control-sm bwickets" type="number" value="${wkts}"></td>
    <td><button class="btn btn-danger btn-sm remove">X</button></td>
  `;
  row.querySelector(".remove").onclick = () => { row.remove(); };
  tbody.appendChild(row);
}

/* ---------- FIELDING (table row) ---------- */
function addFieldingRow(existing) {
  const tbody = $id("fielding-container");
  if (!tbody) return;

  const row = document.createElement("tr");
  row.className = "fielding-row align-middle";

  const pid = existing?.player_id || "";
  const catches = existing?.catches ?? "";
  const drops = existing?.drops ?? "";
  const saves = existing?.saves ?? "";

  row.innerHTML = `
    <td style="min-width:160px;"><select class="form-select form-select-sm f-player-id">${buildPlayerOptionsHTML(pid)}</select></td>
    <td><input class="form-control form-control-sm catches" type="number" value="${catches}"></td>
    <td><input class="form-control form-control-sm drops" type="number" value="${drops}"></td>
    <td><input class="form-control form-control-sm saves" type="number" value="${saves}"></td>
    <td>
      <button class="btn btn-warning btn-sm edit">Lock/Unlock</button>
      <button class="btn btn-danger btn-sm remove">X</button>
    </td>
  `;

  row.querySelector(".edit").onclick = () => {
    row.querySelectorAll("input, select").forEach(i => i.disabled = !i.disabled);
  };
  row.querySelector(".remove").onclick = () => row.remove();
  tbody.appendChild(row);
}

/* ---------- WAGON ---------- */
function clearWagonShots() {
  window.WAGON_SHOTS = [];
  renderWagonList();
  if (typeof window.resetWagon === "function") window.resetWagon();
}
function addWagonShot(playerId, shot) {
  let group = window.WAGON_SHOTS.find(g => g.player_id == playerId);
  if (!group) { group = { player_id: playerId, shots: [] }; window.WAGON_SHOTS.push(group); }
  group.shots.push(shot);
  renderWagonList();
}
function renderWagonList() {
  const ul = $id("shotsList"); if (!ul) return;
  ul.innerHTML = "";
  window.WAGON_SHOTS.forEach(function(g) {
    g.shots.forEach(function(s, idx) {
      const li = document.createElement("li");
      li.className = "list-group-item d-flex justify-content-between align-items-center";
      li.innerHTML = `<div>${playerNameById(g.player_id)} — ${s.runs} runs @ ${s.angle}° (${escapeHtml(s.shot_type||'')})</div><div><button class="btn btn-danger btn-sm remove">X</button></div>`;
      li.querySelector(".remove").onclick = function() {
        g.shots.splice(idx,1);
        if (g.shots.length === 0) window.WAGON_SHOTS = window.WAGON_SHOTS.filter(x => x !== g);
        renderWagonList();
      };
      ul.appendChild(li);
    });
  });
}
function playerNameById(id) {
  const p = window.MS_PLAYERS.find(x => x.id == id);
  return p ? p.name : ("Player " + id);
}

/* ---------- OPPONENT SIMPLE ---------- */
function getOpponentSimple() {
  return {
    runs: parseInt($id("oppRuns")?.value || 0),
    wickets: parseInt($id("oppWickets")?.value || 0),
    extras: parseInt($id("oppExtras")?.value || 0),
    overs: ($id("oppOvers")?.value || "0.0")
  };
}

/* ---------- OVERVIEW ---------- */
function computeOverview() {
  let totalRuns = 0, totalWkts = 0;
  document.querySelectorAll(".batting-row").forEach(r => {
    totalRuns += parseInt(r.querySelector(".runs")?.value || 0);
    if (r.querySelector(".is_out")?.value === "1") totalWkts++;
  });
  if ($id("ourTotalRuns")) $id("ourTotalRuns").textContent = totalRuns;
  if ($id("ourTotalWkts")) $id("ourTotalWkts").textContent = totalWkts;
  const opp = getOpponentSimple();
  if ($id("oppTotalRunsDisplay")) $id("oppTotalRunsDisplay").textContent = opp.runs;
  if ($id("oppTotalWktsDisplay")) $id("oppTotalWktsDisplay").textContent = opp.wickets;
}

/* ---------- PROMPT FOR TEAM/RESULT SUMMARY ---------- */
function promptMatchSummary() {
  const teamRunsDef = $id("ourTotalRuns")?.textContent || "0";
  const teamWktsDef = $id("ourTotalWkts")?.textContent || "0";
  const opp = getOpponentSimple();

  const teamRuns = window.prompt("Enter OUR team runs (integer)", teamRunsDef);
  if (teamRuns === null) return null;
  const teamWkts = window.prompt("Enter OUR team wickets (integer)", teamWktsDef);
  if (teamWkts === null) return null;
  const teamOvers = window.prompt("Enter OUR team overs (e.g. 20.0)", "");

  const oppRuns = window.prompt("Enter OPPONENT runs (integer)", opp.runs || "0");
  if (oppRuns === null) return null;
  const oppWkts = window.prompt("Enter OPPONENT wickets (integer)", opp.wickets || "0");
  if (oppWkts === null) return null;
  const oppOvers = window.prompt("Enter OPPONENT overs (e.g. 19.2)", opp.overs || "");

  const resultText = window.prompt("Enter match result (optional, e.g. 'Team A won by 5 runs')", "") || "";

  return {
    team_summary: {
      runs: parseInt(teamRuns || 0),
      wkts: parseInt(teamWkts || 0),
      overs: teamOvers || "0.0",
      result: resultText || null
    },
    opponent_simple: {
      runs: parseInt(oppRuns || 0),
      wickets: parseInt(oppWkts || 0),
      overs: oppOvers || "0.0",
      extras: parseInt($id("oppExtras")?.value || 0)
    }
  };
}

/* ---------- SAVE (collect & POST) ---------- */
async function saveManualScoring(matchId) {
  // collect batting
  const batting = [];
  document.querySelectorAll(".batting-row").forEach(function(r) {
    const pid = parseInt(r.querySelector(".player-id")?.value || 0);
    if (!pid) return;
    const outStatus = r.querySelector(".is_out")?.value === "1";
    batting.push({
      player_id: pid,
      runs: parseInt(r.querySelector(".runs")?.value || 0),
      balls: parseInt(r.querySelector(".balls")?.value || 0),
      fours: parseInt(r.querySelector(".fours")?.value || 0),
      sixes: parseInt(r.querySelector(".sixes")?.value || 0),
      is_out: outStatus ? 1 : 0,
      wicket_over: outStatus ? (parseInt(r.querySelector(".wicket_over")?.value || 0) || null) : null,
      wicket_ball: outStatus ? (parseInt(r.querySelector(".wicket_ball")?.value || 0) || null) : null,
      dismissal_type: outStatus ? (r.querySelector(".dismissal_type")?.value || null) : null,
      is_opponent: 0
    });
  });

  // bowling
  const bowling = [];
  document.querySelectorAll(".bowling-row").forEach(function(r) {
    const pid = parseInt(r.querySelector(".b-player-id")?.value || 0);
    if (!pid) return;
    bowling.push({
      player_id: pid,
      overs: parseFloat(r.querySelector(".overs")?.value || 0),
      runs_conceded: parseInt(r.querySelector(".bruns")?.value || 0),
      wickets: parseInt(r.querySelector(".bwickets")?.value || 0),
      is_opponent: 0
    });
  });

  // fielding
  const fielding = [];
  document.querySelectorAll(".fielding-row").forEach(function(r) {
    const pid = parseInt(r.querySelector(".f-player-id")?.value || 0);
    if (!pid) return;
    fielding.push({
      player_id: pid,
      catches: parseInt(r.querySelector(".catches")?.value || 0),
      drops: parseInt(r.querySelector(".drops")?.value || 0),
      saves: parseInt(r.querySelector(".saves")?.value || 0),
      is_opponent: 0
    });
  });

  // prompt for match summary
  const summary = promptMatchSummary();
  if (!summary) return alert("Save cancelled.");

  const payload = {
    batting: batting,
    bowling: bowling,
    fielding: fielding,
    wagon: window.WAGON_SHOTS || [],
    opponent_simple: summary.opponent_simple,
    team_summary: summary.team_summary
  };

  try {
    const resp = await fetch(`/api/match/${matchId}/manual_save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    if (!resp.ok) {
      alert("Save failed: " + (data.error || JSON.stringify(data)));
      return;
    }
    alert("Saved! Match marked pending approval for coach.");
    location.reload();
  } catch (err) {
    alert("Network error: " + err);
  }
}

/* ---------- WAGON HOOKS ---------- */
function wireWagonStart() {
  const btn = $id("startWagon");
  if (!btn) return;
  btn.onclick = function() {
    if (typeof window.initWagonClickHandler === "function") {
      alert("Click on the wagon canvas to set an angle. After that the shot is added automatically.");
      window.initWagonClickHandler(function(angle, distance) {
        const playerId = parseInt($id("wagonPlayer")?.value || 0);
        const runs = parseInt($id("wagonRun")?.value || 0);
        const shot_type = $id("wagonShotType")?.value || "";
        if (!playerId) return alert("Select a player first");
        addWagonShot(playerId, { angle: angle, distance: distance || 0, runs: runs, shot_type: shot_type });
      });
    } else {
      alert("Wagon wheel not initialised on this page.");
    }
  };
}

/* ---------- INNINGS UI (applies FIRST/SECOND rules) ---------- */
function applyInningsUI() {
  const inn = parseInt($id("inningsSelect")?.value || 1);
  const batSide = (window.MATCH && window.MATCH.batting_side) ? window.MATCH.batting_side : "team";

  // hide everything first
  ["ourBatSection","ourBowlSection","ourFieldSection","oppSimpleSection"].forEach(id => {
    const el = $id(id); if (el) el.style.display = "none";
  });

  // FIRST INNINGS RULES
  if (inn === 1) {
    if (batSide === "team") {
      // Our team batting first -> show only Batting table, NO opponent summary
      if ($id("ourBatSection")) $id("ourBatSection").style.display = "block";
      if ($id("ourBowlSection")) $id("ourBowlSection").style.display = "none";
      if ($id("ourFieldSection")) $id("ourFieldSection").style.display = "none";
      if ($id("oppSimpleSection")) $id("oppSimpleSection").style.display = "none";
    } else {
      // Opponent batting first -> show Bowling + Fielding and Opponent summary
      if ($id("ourBowlSection")) $id("ourBowlSection").style.display = "block";
      if ($id("ourFieldSection")) $id("ourFieldSection").style.display = "block";
      if ($id("oppSimpleSection")) $id("oppSimpleSection").style.display = "block";
    }
  }
  // SECOND INNINGS RULES
  else {
    // determine who bats in second innings (reverse of batting_side)
    const secondInningsBatting = (batSide === "team") ? "opponent" : "team";

    if (secondInningsBatting === "team") {
      // Team batting in 2nd innings -> show Batting table
      if ($id("ourBatSection")) $id("ourBatSection").style.display = "block";
      // When our team batting in 2nd innings, opponent summary NOT required according to rules
      if ($id("oppSimpleSection")) $id("oppSimpleSection").style.display = "none";
    } else {
      // Opponent batting in 2nd innings -> our team bowling: show bowling+fielding AND Opponent summary
      if ($id("ourBowlSection")) $id("ourBowlSection").style.display = "block";
      if ($id("ourFieldSection")) $id("ourFieldSection").style.display = "block";
      if ($id("oppSimpleSection")) $id("oppSimpleSection").style.display = "block";
    }
  }

  // ensure each visible section has at least one row rendered and player selects show up
  if ($id("ourBatSection") && $id("ourBatSection").style.display !== "none" && !$id("batting-container").querySelector(".batting-row")) {
    addBattingRow();
  }
  if ($id("ourBowlSection") && $id("ourBowlSection").style.display !== "none" && !$id("bowling-container").querySelector(".bowling-row")) {
    addBowlingRow();
  }
  if ($id("ourFieldSection") && $id("ourFieldSection").style.display !== "none" && !$id("fielding-container").querySelector(".fielding-row")) {
    addFieldingRow();
  }

  computeOverview();
}

/* ---------- INIT ---------- */
document.addEventListener("DOMContentLoaded", function() {
  // wire UI buttons (safe guards if elements missing)
  $id("addBatsmanBtn")?.addEventListener("click", function(e){ e.preventDefault(); addBattingRow(); });
  $id("addBowlerBtn")?.addEventListener("click", function(e){ e.preventDefault(); addBowlingRow(); });
  $id("addFieldingBtn")?.addEventListener("click", function(e){ e.preventDefault(); addFieldingRow(); });
  $id("clearWagonBtn")?.addEventListener("click", function(e){ e.preventDefault(); clearWagonShots(); });
  $id("saveManualBtn")?.addEventListener("click", function(e){ e.preventDefault(); saveManualScoring(window.MATCH?.id); });

  const inningsSelect = $id("inningsSelect");
  if (inningsSelect) inningsSelect.addEventListener("change", applyInningsUI);

  // wire wagon + render list
  wireWagonStart();
  renderWagonList();

  // compute overview on input changes
  document.body.addEventListener("input", computeOverview);

  // initial UI application (this will create rows for visible sections only)
  applyInningsUI();
  computeOverview();
});

/* expose for debugging if needed */
window.addBattingRow = addBattingRow;
window.addBowlingRow = addBowlingRow;
window.addFieldingRow = addFieldingRow;
window.saveManualScoring = saveManualScoring;
window.clearWagonShots = clearWagonShots;
window.renderWagonList = renderWagonList;
