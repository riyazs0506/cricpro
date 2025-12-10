// innings_control.js — minimal helpers to mark innings start/end and lock scoring

function startInnings(matchId, inningsNo){
  fetch(`/match/${matchId}/innings/start`, { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({innings: inningsNo})})
    .then(r=>r.json()).then(d=>{
      if(d.status==='ok'){ alert("Innings started"); location.reload(); } else alert("Error: "+d.error);
    }).catch(e=>alert("Network err"));
}

function endInnings(matchId, inningsNo){
  fetch(`/match/${matchId}/innings/end`, { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({innings: inningsNo})})
    .then(r=>r.json()).then(d=>{
      if(d.status==='ok'){ alert("Innings ended"); location.reload(); } else alert("Error: "+d.error);
    }).catch(e=>alert("Network err"));
}
