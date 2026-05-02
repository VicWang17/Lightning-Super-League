const ATTRS = ["SHO","PAS","DRI","SPD","STR","STA","DEF","HEA","VIS","TKL","ACC","CRO","CON","FIN","BAL","COM","SAV","REF","POS"];

const EVENT_NAMES = {
  "kickoff": "开球", "fulltime": "结束", "halftime": "中场",
  "short_pass": "短传", "mid_pass": "中场传球", "back_pass": "回传", "long_pass": "长传",
  "through_ball": "直塞球", "wing_break": "边路突破", "cut_inside": "内切",
  "cross": "传中", "header": "头球争顶", "corner": "角球",
  "close_shot": "近距离射门", "long_shot": "远射", "goal": "进球",
  "tackle": "铲球", "intercept": "拦截", "clearance": "解围",
  "keeper_save": "门将扑救", "keeper_claim": "门将摘球",
  "foul": "犯规", "yellow_card": "黄牌", "red_card": "红牌",
  "offside": "越位", "substitution": "换人", "own_goal": "乌龙球"
};

const TACTIC_DEFS = [
  {key:"passing_style", label:"传球风格", min:0, max:4, desc:["长传","直接","平衡","短传","传控"]},
  {key:"attack_width", label:"进攻宽度", min:0, max:4, desc:["极窄","窄","平衡","宽","极宽"]},
  {key:"attack_tempo", label:"进攻节奏", min:0, max:4, desc:["极慢","慢","平衡","快","极速反击"]},
  {key:"defensive_line_height", label:"防线高度", min:0, max:4, desc:["深度回收","低","平衡","高","高位"]},
  {key:"crossing_strategy", label:"传中策略", min:0, max:4, desc:["回避","低平","平衡","高球","频繁"]},
  {key:"shooting_mentality", label:"射门心态", min:0, max:4, desc:["保守","谨慎","平衡","积极","疯狂"]},
  {key:"playmaker_focus", label:"组织者侧重", min:0, max:4, desc:["无","低","中","高","核心"]},
  {key:"pressing_intensity", label:"逼抢强度", min:0, max:4, desc:["不逼抢","低","中","高","疯狂"]},
  {key:"defensive_compactness", label:"防线收缩", min:0, max:2, desc:["松散","平衡","紧凑"]},
  {key:"marking_strategy", label:"盯人策略", min:0, max:2, desc:["区域","混合","人盯人"]},
  {key:"offside_trap", label:"越位陷阱", min:0, max:2, desc:["不设置","偶尔","频繁"]},
  {key:"tackling_aggression", label:"铲抢侵略性", min:0, max:3, desc:["干净","温和","积极","粗暴"]},
];

function defaultPlayer(pos, suffix, teamPrefix) {
  const attrs = {};
  ATTRS.forEach(a => attrs[a] = 10);
  const biases = {
    GK:  {SAV:16, REF:15, POS:14, COM:12},
    CB:  {DEF:16, HEA:15, STR:14, TKL:13},
    SB:  {SPD:15, CRO:14, DEF:12, STA:14},
    DMF: {DEF:14, TKL:14, PAS:13, STA:14},
    CMF: {PAS:15, VIS:14, STA:14, CON:13},
    AMF: {PAS:15, VIS:15, DRI:14, SHO:12},
    WF:  {SPD:16, DRI:14, CRO:14, ACC:14},
    ST:  {SHO:16, HEA:14, STR:14, SPD:13},
  };
  if (biases[pos]) Object.assign(attrs, biases[pos]);
  return {
    player_id: `${teamPrefix}_${pos}_${suffix}`,
    name: `${teamPrefix} ${pos} ${suffix}`,
    position: pos,
    attributes: attrs,
    skills: [],
    stamina: 100,
    height: 175,
    foot: "right"
  };
}

function defaultTeam(name, formation, isHome) {
  const prefix = name;
  let players;
  if (formation === "F02") {
    players = [
      defaultPlayer("GK","门将",prefix), defaultPlayer("CB","中卫A",prefix), defaultPlayer("CB","中卫B",prefix),
      defaultPlayer("CMF","中场A",prefix), defaultPlayer("CMF","中场B",prefix),
      defaultPlayer("AMF","前腰",prefix), defaultPlayer("WF","边锋",prefix), defaultPlayer("ST","前锋",prefix),
    ];
  } else {
    players = [
      defaultPlayer("GK","门将",prefix), defaultPlayer("CB","中卫A",prefix), defaultPlayer("CB","中卫B",prefix),
      defaultPlayer("SB","边卫",prefix), defaultPlayer("DMF","后腰",prefix),
      defaultPlayer("CMF","中场A",prefix), defaultPlayer("CMF","中场B",prefix), defaultPlayer("ST","前锋",prefix),
    ];
  }
  const bench = [
    defaultPlayer("WF","替补边锋",prefix), defaultPlayer("CMF","替补中场",prefix), defaultPlayer("CB","替补中卫",prefix),
  ];
  let tactics;
  if (isHome) {
    tactics = {passing_style:1, attack_width:2, attack_tempo:4, defensive_line_height:3, crossing_strategy:2, shooting_mentality:3, playmaker_focus:0, pressing_intensity:3, defensive_compactness:2, marking_strategy:1, offside_trap:1, tackling_aggression:2};
  } else {
    tactics = {passing_style:4, attack_width:2, attack_tempo:2, defensive_line_height:1, crossing_strategy:3, shooting_mentality:2, playmaker_focus:1, pressing_intensity:1, defensive_compactness:2, marking_strategy:0, offside_trap:0, tackling_aggression:1};
  }
  return { team_id: name.replace(/\s/g,"_"), name, formation_id: formation, players, bench, tactics };
}

let homeTeam = defaultTeam("雷霆 FC","F01",true);
let awayTeam = defaultTeam("闪电联","F02",false);
let steps = [];
let autoInterval = null;

// ===== Render =====
function renderTactics(side) {
  const container = document.getElementById(side+"Tactics");
  const team = side==="home"?homeTeam:awayTeam;
  container.innerHTML = TACTIC_DEFS.map((t) => {
    const val = team.tactics[t.key];
    return `<div class="tactic-row">
      <label>${t.label}</label>
      <input type="range" min="${t.min}" max="${t.max}" value="${val}" data-key="${t.key}" data-side="${side}">
      <span class="tactic-val">${t.desc[val]??val}</span>
    </div>`;
  }).join("");
  container.querySelectorAll("input[type=range]").forEach(el => {
    el.oninput = e => {
      const k = e.target.dataset.key;
      const s = e.target.dataset.side;
      const t = s==="home"?homeTeam:awayTeam;
      t.tactics[k] = parseInt(e.target.value);
      const def = TACTIC_DEFS.find(d=>d.key===k);
      e.target.nextElementSibling.textContent = def.desc[t.tactics[k]]??t.tactics[k];
    };
  });
}

function renderPlayers(side) {
  const container = document.getElementById(side+"Players");
  const team = side==="home"?homeTeam:awayTeam;
  const all = [...team.players, ...team.bench];
  container.innerHTML = all.map((p, idx) => {
    const onField = idx < team.players.length;
    const attrRows = ATTRS.map(a => `
      <div class="attr-row"><label>${a}</label>
        <input type="number" min="1" max="20" value="${p.attributes[a]}"
          data-side="${side}" data-idx="${idx}" data-attr="${a}">
      </div>`).join("");
    return `
      <div class="player-card">
        <div class="player-header" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'grid':'none'">
          <span class="player-name">${p.name}</span>
          <span class="player-pos">${p.position}${onField?"":"(替补)"}</span>
        </div>
        <div class="player-attrs" style="display:none">${attrRows}</div>
      </div>`;
  }).join("");
  container.querySelectorAll("input[type=number]").forEach(el => {
    el.onchange = e => {
      const t = e.target.dataset.side==="home"?homeTeam:awayTeam;
      const all = [...t.players, ...t.bench];
      all[parseInt(e.target.dataset.idx)].attributes[e.target.dataset.attr] = parseInt(e.target.value);
    };
  });
}

window.toggleSection = function(id) {
  const el = document.getElementById(id);
  el.classList.toggle("open");
};

// ===== API =====
async function api(path, body) {
  const r = await fetch(path, {
    method: body?"POST":"GET",
    headers: {"Content-Type":"application/json"},
    body: body?JSON.stringify(body):undefined
  });
  return r.json();
}

async function initMatch() {
  const seed = parseInt(document.getElementById("seedInput").value) || 0;
  const homeAdv = document.getElementById("homeAdvCheck").checked;
  homeTeam.name = document.getElementById("homeNameInput").value;
  awayTeam.name = document.getElementById("awayNameInput").value;
  homeTeam.formation_id = document.getElementById("homeFormation").value;
  awayTeam.formation_id = document.getElementById("awayFormation").value;
  homeTeam.team_id = homeTeam.name.replace(/\s/g,"_");
  awayTeam.team_id = awayTeam.name.replace(/\s/g,"_");

  const data = await api("/api/init", {
    homeTeam, awayTeam, seed, homeAdvantage: homeAdv
  });
  if (data.success) {
    updateState(data.state, data.events);
    steps = [];
    document.getElementById("btnStep").disabled = false;
    document.getElementById("btnAuto").disabled = false;
    document.getElementById("candidatesWrap").style.display = "none";
  }
}

async function step() {
  const data = await api("/api/step", {});
  if (data.success) {
    steps.push(data.step);
    updateState(data.state, null, data.step);
    if (data.done) {
      document.getElementById("btnStep").disabled = true;
      document.getElementById("btnAuto").disabled = true;
    }
  }
}

async function reset() {
  await api("/api/reset", {});
  steps = [];
  document.getElementById("scoreDisplay").textContent = "0 - 0";
  document.getElementById("matchTime").textContent = "0'00\"";
  document.getElementById("matchHalf").textContent = "上半场";
  document.getElementById("matchPossession").textContent = "控球: 主队";
  document.getElementById("matchZone").textContent = "区域 [1,1]";
  document.getElementById("currControl").textContent = "0.00";
  document.getElementById("currShift").textContent = "0.00";
  document.getElementById("globalMomentum").textContent = "0.00";
  document.getElementById("possessionPct").textContent = "50%";
  document.getElementById("eventsList").innerHTML = "";
  document.getElementById("controlMatrix").innerHTML = "";
  document.getElementById("shiftMatrix").innerHTML = "";
  document.getElementById("candidatesWrap").style.display = "none";
  document.getElementById("btnStep").disabled = true;
  document.getElementById("btnAuto").disabled = true;
}

function toggleAuto() {
  if (autoInterval) {
    clearInterval(autoInterval);
    autoInterval = null;
    document.getElementById("btnAuto").textContent = "▶️ 自动播放";
  } else {
    document.getElementById("btnAuto").textContent = "⏸️ 暂停";
    autoInterval = setInterval(async () => {
      if (document.getElementById("btnStep").disabled) {
        clearInterval(autoInterval); autoInterval = null;
        document.getElementById("btnAuto").textContent = "▶️ 自动播放";
        return;
      }
      await step();
    }, 500);
  }
}

// ===== Visualization =====
function updateState(state, events, stepInfo) {
  document.getElementById("scoreDisplay").textContent = `${state.score.home} - ${state.score.away}`;
  document.getElementById("matchTime").textContent = formatMinute(state.minute);
  document.getElementById("matchHalf").textContent = state.half === 1 ? "上半场" : state.half === 2 ? "下半场" : "结束";
  document.getElementById("matchPossession").textContent = `控球: ${state.possession==="home"?"主队":"客队"}`;
  document.getElementById("matchZone").textContent = `区域 [${state.active_zone[0]},${state.active_zone[1]}]`;
  document.getElementById("currControl").textContent = state.control.toFixed(2);
  document.getElementById("currShift").textContent = (state.control_shift?.[state.active_zone[0]]?.[state.active_zone[1]] ?? 0).toFixed(2);
  document.getElementById("globalMomentum").textContent = (state.global_momentum ?? 0).toFixed(2);

  const totalTicks = state.possession_ticks[0] + state.possession_ticks[1];
  const pct = totalTicks > 0 ? Math.round(state.possession_ticks[0]/totalTicks*100) : 50;
  document.getElementById("possessionPct").textContent = `${pct}%`;

  renderMatrix("controlMatrix", state.control_matrix, state.active_zone, v => {
    const r = Math.min(255, Math.round((v+1)*128));
    const b = Math.min(255, Math.round((1-v)*128));
    return `rgb(${r},180,${b})`;
  });
  const bd = state.control_breakdown;
  if (bd) {
    const zone = state.active_zone;
    const natural = state.control_matrix[zone[0]][zone[1]];
    const shift = (state.control_shift?.[zone[0]]?.[zone[1]] ?? 0);
    document.getElementById("controlBreakdown").textContent =
      `分解: 天然=${natural.toFixed(2)} 偏移=${shift.toFixed(2)} 最终=${bd.final.toFixed(2)}`;
  }
  renderMatrix("shiftMatrix", state.control_shift || [[0,0,0],[0,0,0],[0,0,0]], state.active_zone, v => {
    if (v > 0) return `rgba(74,222,128,${Math.min(1, v/0.5)})`;
    return `rgba(251,113,133,${Math.min(1, -v/0.5)})`;
  });

  if (events) renderEvents(events);
  else if (stepInfo && stepInfo.events) {
    for (const ev of stepInfo.events) {
      appendEvent(ev);
    }
  }

  if (stepInfo) renderCandidates(stepInfo);
}

function renderMatrix(id, matrix, activeZone, colorFn) {
  const el = document.getElementById(id);
  let html = "";
  for (let r=0;r<3;r++) {
    for (let c=0;c<3;c++) {
      const v = matrix[r][c];
      const active = activeZone[0]===r && activeZone[1]===c;
      const bg = colorFn(v);
      const tc = (bg.includes("rgba") && v > 0.5) || (bg.includes("rgb") && (r+c)<2) ? "#000" : "#e2e8f0";
      html += `<div class="cell ${active?"active":""}" style="background:${bg};color:${tc}">
        <span class="zone-label">[${r},${c}]</span>${v.toFixed(2)}
      </div>`;
    }
  }
  el.innerHTML = html;
}

function renderCandidates(stepInfo) {
  const wrap = document.getElementById("candidatesWrap");
  wrap.style.display = "block";
  const chart = document.getElementById("candidatesChart");
  const detail = document.getElementById("candidatesDetail");

  const cands = stepInfo.candidates || [];
  const selIdx = stepInfo.selected_index;

  chart.innerHTML = cands.map((c,i) => {
    const pct = (c.probability*100).toFixed(1);
    const w = Math.max(2, c.probability*100);
    const cn = EVENT_NAMES[c.type] || c.type;
    return `<div class="candidate-bar">
      <div class="candidate-label">${cn}</div>
      <div class="candidate-track">
        <div class="candidate-fill ${i===selIdx?"selected":""}" style="width:${w}%">
          <span class="candidate-pct">${pct}%</span>
        </div>
      </div>
    </div>`;
  }).join("");

  const pre = stepInfo.pre_state;
  const flags = [];
  if (pre.home_flags.high_press_active) flags.push("主队高位逼抢");
  if (pre.away_flags.high_press_active) flags.push("客队高位逼抢");
  if (pre.home_flags.deep_defense_active) flags.push("主队深度防守");
  if (pre.away_flags.deep_defense_active) flags.push("客队深度防守");
  if (pre.home_flags.man_marking_active) flags.push("主队人盯人");
  if (pre.away_flags.man_marking_active) flags.push("客队人盯人");
  if (pre.home_flags.counter_focus_active) flags.push("主队反击专注");
  if (pre.away_flags.counter_focus_active) flags.push("客队反击专注");
  if (pre.home_flags.offside_trap_active) flags.push("主队越位陷阱");
  if (pre.away_flags.offside_trap_active) flags.push("客队越位陷阱");

  const selCn = EVENT_NAMES[stepInfo.event_type] || stepInfo.event_type;

  detail.innerHTML = `
    <b>影响因子:</b> 控球=${pre.control.toFixed(2)} · 势头=${pre.momentum.toFixed(2)} · 区域=[${pre.active_zone}] · 反击加成=${pre.counter_boost[0]}/${pre.counter_boost[1]}<br>
    <b>活跃战术:</b> ${flags.join(", ") || "无"}<br>
    <b>选中:</b> ${selCn} ${stepInfo.event && stepInfo.event.result ? "("+stepInfo.event.result+")" : ""}
    ${stepInfo.event && stepInfo.event.narrative ? " · <i>"+stepInfo.event.narrative+"</i>" : ""}
  `;
}

function eventRowHTML(ev) {
  const cn = EVENT_NAMES[ev.type] || ev.type;
  const cls = ev.type==="goal"?"goal":(ev.result==="fail"||ev.result==="blocked"||ev.result==="saved")?"turnover":"";
  return `
    <div class="event-row ${cls}">
      <span class="col-time">${formatMinute(ev.minute)}</span>
      <span class="col-type">${cn}</span>
      <span class="col-team">${ev.team||""}</span>
      <span class="col-player">${ev.player_name||""}</span>
      <span class="col-player2">${ev.player2_name||""}</span>
      <span class="col-opp">${ev.opponent_name||""}</span>
      <span class="col-zone">${ev.zone||""}</span>
      <span class="col-result ${ev.result||""}">${ev.result||""}</span>
      <span class="col-desc" title="${ev.narrative||""}">${ev.narrative||""}</span>
    </div>`;
}

function renderEvents(events) {
  const el = document.getElementById("eventsList");
  el.innerHTML = events.map(eventRowHTML).join("");
  el.scrollTop = el.scrollHeight;
}

function appendEvent(ev) {
  const el = document.getElementById("eventsList");
  const div = document.createElement("div");
  div.innerHTML = eventRowHTML(ev);
  el.appendChild(div.firstElementChild);
  el.scrollTop = el.scrollHeight;
}

function formatMinute(m) {
  const min = Math.floor(m);
  const sec = Math.floor((m - min) * 60);
  return `${min}'${sec.toString().padStart(2,"0")}`;
}

// ===== Protocol check =====
if (location.protocol === "file:") {
  document.body.innerHTML = `
    <div style="max-width:600px;margin:80px auto;padding:40px;background:#1e293b;border-radius:16px;color:#e2e8f0;text-align:center;font-family:sans-serif;">
      <h2 style="color:#fb7185;margin-bottom:16px;">⚠️ 请通过 HTTP 访问</h2>
      <p style="line-height:1.8;color:#94a3b8;">
        你当前是通过 <code>file://</code> 直接打开 HTML 文件，这会导致 API 请求失败。<br><br>
        请先在终端启动 preview server：<br>
        <code style="background:#0f172a;padding:8px 16px;border-radius:8px;display:inline-block;margin:12px 0;">
          cd match-engine/preview && go run main.go
        </code><br>
        然后在浏览器访问：<br>
        <a href="http://localhost:8080" style="color:#38bdf8;font-size:1.2rem;font-weight:600;">http://localhost:8080</a>
      </p>
    </div>`;
  throw new Error("file protocol not supported");
}

// ===== Init =====
document.getElementById("btnInit").onclick = initMatch;
document.getElementById("btnStep").onclick = step;
document.getElementById("btnReset").onclick = reset;
document.getElementById("btnAuto").onclick = toggleAuto;

renderTactics("home");
renderTactics("away");
renderPlayers("home");
renderPlayers("away");
