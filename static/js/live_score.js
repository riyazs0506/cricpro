// live_score.js — final (works with /api/live/<id>/add and /api/live/<id>/events)

async function postBall(matchId, payload){
  try{
    const res = await fetch(`/api/live/${matchId}/add`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    return await res.json();
  }catch(e){
    console.error("postBall error", e); return {error:"network"};
  }
}

async function fetchEvents(matchId){
  try{
    const res = await fetch(`/api/live/${matchId}/events`);
    if(!res.ok) return [];
    return await res.json();
  }catch(e){ console.error("fetchEvents", e); return []; }
}

function buildSummary(events){
  const summary = { totalRuns:0, wickets:0, balls:0, batsmen:{}, bowlers:{} };
  events.forEach(ev=>{
    const runs = Number(ev.runs||0);
    summary.totalRuns += runs;
    if(ev.wicket && ev.wicket !== "none") summary.wickets += 1;
    const extras = (ev.extras||"none").toLowerCase();
    const legal = !(extras==="wide" || extras==="no_ball");
    if(legal) summary.balls += 1;

    if(ev.striker){
      const s = ev.striker;
      if(!summary.batsmen[s]) summary.batsmen[s] = {runs:0,balls:0,fours:0,sixes:0,out:false};
      summary.batsmen[s].runs += runs;
      if(legal) summary.batsmen[s].balls += 1;
      if(runs===4) summary.batsmen[s].fours += 1;
      if(runs===6) summary.batsmen[s].sixes += 1;
      if(ev.wicket && ev.wicket!=="none") summary.batsmen[s].out = true;
    }
    if(ev.bowler){
      const b = ev.bowler;
      if(!summary.bowlers[b]) summary.bowlers[b] = {runs:0,balls:0,wickets:0};
      summary.bowlers[b].runs += runs;
      if(legal) summary.bowlers[b].balls += 1;
      if(ev.wicket && ev.wicket!=="none") summary.bowlers[b].wickets += 1;
    }
  });
  summary.overs = `${Math.floor(summary.balls/6)}.${summary.balls%6}`;
  return summary;
}

function renderScoreboard(container, summary){
  if(!container) return;
  container.innerHTML = "";
  const top = document.createElement("div"); top.className="score-card";
  top.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center">
      <div><div class="score-num">${summary.totalRuns} / ${summary.wickets}</div>
      <div class="text-muted">Overs: ${summary.overs}</div></div>
      <div class="text-muted">Updated</div>
    </div>`;
  container.appendChild(top);

  // batsmen
  const batTab = document.createElement("div"); batTab.className="card p-2 mt-2";
  let batHtml = '<h6>Batsmen</h6><table class="table"><thead><tr><th>P</th><th>R</th><th>B</th><th>4s</th><th>6s</th><th>SR</th></tr></thead><tbody>';
  Object.keys(summary.batsmen).forEach(k=>{
    const v = summary.batsmen[k];
    const sr = v.balls>0?((v.runs/v.balls)*100).toFixed(2):'0.00';
    batHtml += `<tr><td>${k}${v.out? ' *':''}</td><td>${v.runs}</td><td>${v.balls}</td><td>${v.fours}</td><td>${v.sixes}</td><td>${sr}</td></tr>`;
  });
  batHtml += '</tbody></table>';
  batTab.innerHTML = batHtml; container.appendChild(batTab);

  // bowlers
  const bowlTab = document.createElement("div"); bowlTab.className="card p-2 mt-2";
  let bowlHtml = '<h6>Bowlers</h6><table class="table"><thead><tr><th>P</th><th>O</th><th>R</th><th>W</th></tr></thead><tbody>';
  Object.keys(summary.bowlers).forEach(k=>{
    const v = summary.bowlers[k];
    const overs = `${Math.floor(v.balls/6)}.${v.balls%6}`;
    bowlHtml += `<tr><td>${k}</td><td>${overs}</td><td>${v.runs}</td><td>${v.wickets}</td></tr>`;
  });
  bowlHtml += '</tbody></table>';
  bowlTab.innerHTML = bowlHtml; container.appendChild(bowlTab);
}

function renderEvents(container, events){
  if(!container) return;
  container.innerHTML='';
  events.slice().reverse().forEach(ev=>{
    const div = document.createElement("div"); div.className="commentary-item";
    div.innerHTML = `<strong>${ev.over}.${ev.ball}</strong> — ${ev.striker||'-'} to ${ev.bowler||'-'} : ${ev.runs} ${ev.extras!=='none'? '('+ev.extras+')':''} ${ev.wicket!=='none'? 'W('+ev.wicket+')': ''} <div class="text-muted">${ev.commentary||''}</div>`;
    container.appendChild(div);
  });
}

// Public init
function initLive(matchId, opts){
  const eventsCt = document.getElementById(opts.eventsContainerId);
  const boardCt = document.getElementById(opts.scoreboardContainerId);
  const submitBtn = document.getElementById(opts.submitBtnId);
  const refreshInterval = opts.fetchInterval || 3000;

  async function refresh(){
    const evs = await fetchEvents(matchId);
    renderEvents(eventsCt, evs);
    const sum = buildSummary(evs);
    renderScoreboard(boardCt, sum);
  }

  if(submitBtn){
    submitBtn.addEventListener('click', async e=>{
      e.preventDefault();
      const payload = {
        over_no: Number(document.getElementById(opts.overInputId).value||1),
        ball_no: Number(document.getElementById(opts.ballInputId).value||1),
        striker: document.getElementById(opts.strikerSelectId)?.value || "",
        non_striker: document.getElementById(opts.nonStrikerSelectId)?.value || "",
        bowler: document.getElementById(opts.bowlerSelectId)?.value || "",
        runs: Number(document.getElementById(opts.runsInputId).value||0),
        extras: document.getElementById(opts.extrasSelectId)?.value || "none",
        wicket: document.getElementById(opts.wicketSelectId)?.value || "none",
        commentary: document.getElementById(opts.commentaryId)?.value || ""
      };
      if(!payload.bowler){ alert("Select bowler"); return; }
      submitBtn.disabled = true; submitBtn.innerText="Saving...";
      const r = await postBall(matchId, payload);
      submitBtn.disabled = false; submitBtn.innerText="Add Ball";
      if(r && r.status==='ok'){ await refresh(); }
      else { alert("Save failed: "+JSON.stringify(r)); }
    });
  }

  refresh();
  const timer = setInterval(refresh, refreshInterval);
  return { stop: ()=>clearInterval(timer), refresh };
}
