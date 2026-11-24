/* AgentOps 前端：类型化 fetch 封装 + 统一错误映射 + 加载/空态 */
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

async function api(path, options = {}) {
  try {
    const res = await fetch(path, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
    if (res.status === 204) return null;
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || `请求失败 (${res.status})`);
    return data;
  } catch (e) {
    toast(e.message || '网络连接失败，请检查服务是否启动');
    throw e;
  }
}

function toast(msg) {
  const el = $('#toast'); el.textContent = msg; el.classList.add('show');
  clearTimeout(toast._t); toast._t = setTimeout(() => el.classList.remove('show'), 2600);
}

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const levelTag = (l) => `<span class="tag ${l}">${l}</span>`;
const statusTag = (s) => `<span class="tag s-${s}">${{todo:'待开始',running:'进行中',done:'已完成',blocked:'阻塞'}[s] || s}</span>`;

const VIEW_TITLES = {
  overview: ['工作台概览', 'AI Agent 驱动的软件工程全流程调度与可靠性监控'],
  tasks: ['任务管理', '任务的创建、跟踪与分级标记'],
  planning: ['分级规划', 'AI 任务分级与层级化拆解（L1 自动 / L2 协作 / L3 人工）'],
  analysis: ['失效分析', '缺陷帕累托分析、Agent 失效评分与可靠性评级'],
};

function switchView(view) {
  $$('.view').forEach(v => v.classList.remove('active'));
  $('#view-' + view).classList.add('active');
  $$('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.view === view));
  const [t, s] = VIEW_TITLES[view]; $('#page-title').textContent = t; $('#page-sub').textContent = s;
  loadView(view);
}

$$('.nav-item').forEach(b => b.addEventListener('click', () => switchView(b.dataset.view)));
$$('[data-goto]').forEach(b => b.addEventListener('click', () => switchView(b.dataset.goto)));

async function loadView(view) {
  try {
    if (view === 'overview') await renderOverview();
    if (view === 'tasks') await renderTasks();
    if (view === 'planning') await renderPlanning();
    if (view === 'analysis') await renderAnalysis();
  } catch (_) { /* api() 已提示 */ }
}

/* ---------- 概览 ---------- */
async function renderOverview() {
  const [o, rel, tasks] = await Promise.all([
    api('/api/analysis/overview'), api('/api/analysis/reliability'), api('/api/tasks?limit=6'),
  ]);
  $('#stats').innerHTML = [
    ['任务总数', o.total_tasks, '覆盖 2 个项目', 'c1'],
    ['已完成', o.done_tasks, `完成率 ${o.completion_rate}%`, 'c2'],
    ['进行中', o.running_tasks, 'Agent 协同执行', ''],
    ['阻塞任务', o.blocked_tasks, '需人工介入', 'c3'],
    ['缺陷总数', o.total_defects, `Agent 成功率 ${o.agent_success_rate}%`, 'c4'],
  ].map(([l, v, d, c]) => `<div class="stat ${c}"><div class="label">${l}</div><div class="value">${v}</div><div class="delta">${d}</div></div>`).join('');

  const levels = [['L1 自动完成', o.l1_count, 'var(--L1)'], ['L2 人机协作', o.l2_count, 'var(--L2)'], ['L3 纯人工', o.l3_count, 'var(--L3)']];
  const max = Math.max(1, ...levels.map(x => x[1]));
  $('#level-chart').innerHTML = levels.map(([label, n, color]) => `
    <div class="bar-row"><div class="bar-label">${label}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${n/max*100}%;background:${color}"></div></div>
      <div class="bar-val">${n} 项</div></div>`).join('') +
    `<p class="muted" style="margin-top:18px">分级机制：L1 由 Agent 全自动完成；L2 由人与 Agent 协作；L3 涉及高风险决策，由纯人工完成。</p>`;

  const dist = rel.distribution || {A:0,B:0,C:0,D:0};
  $('#reliability').innerHTML = `
    <div style="display:flex;align-items:center;gap:22px;margin-bottom:14px">
      <div class="grade ${rel.grade}" style="width:64px;height:64px;border-radius:14px;font-size:28px">${rel.grade}</div>
      <div><div style="font-size:26px;font-weight:800">${rel.average}<span style="font-size:14px;color:var(--muted)"> / 100</span></div>
      <div class="muted">平均失效评分 · 样本 ${rel.sample_size} 个</div></div></div>
    ${Object.entries(dist).map(([g,n]) => `<div class="bar-row"><div class="bar-label">${g} 级可靠</div>
      <div class="bar-track"><div class="bar-fill" style="width:${n/(rel.sample_size||1)*100}%"></div></div><div class="bar-val">${n}</div></div>`).join('')}`;

  $('#recent-tasks').innerHTML = taskTable(tasks.items, false);
}

/* ---------- 任务表格 ---------- */
function taskTable(items, actions = true) {
  if (!items.length) return '<div class="empty-state" style="padding:30px">暂无任务</div>';
  return `<table><thead><tr><th>ID</th><th>任务</th><th>项目</th><th>等级</th><th>状态</th><th>负责人</th><th>优先级</th>${actions?'<th>操作</th>':''}</tr></thead><tbody>
    ${items.map(t => `<tr><td>#${t.id}</td><td><b>${esc(t.title)}</b><div class="muted" style="font-size:11px">${esc(t.description).slice(0,42)}</div></td>
      <td>${esc(t.project)}</td><td>${levelTag(t.level)}</td><td>${statusTag(t.status)}</td><td>${esc(t.owner)}</td><td>P${t.priority}</td>
      ${actions?`<td><button class="link" onclick="openPlan(${t.id})">规划</button> · <button class="link" onclick="simRun(${t.id})">模拟执行</button> · <button class="link" onclick="delTask(${t.id})">删除</button></td>`:''}</tr>`).join('')}
  </tbody></table>`;
}

async function renderTasks() {
  const status = $('#filter-status').value, level = $('#filter-level').value;
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  if (level) params.set('level', level);
  const data = await api('/api/tasks?' + params);
  let items = data.items;
  const kw = ($('#filter-kw').value || '').trim();
  if (kw) items = items.filter(t => (t.title + t.description).includes(kw));
  $('#task-table').innerHTML = taskTable(items);
}
$('#filter-status').addEventListener('change', renderTasks);
$('#filter-level').addEventListener('change', renderTasks);
$('#filter-kw').addEventListener('input', renderTasks);

/* ---------- 分级规划 ---------- */
async function renderPlanning() {
  const data = await api('/api/tasks?limit=100');
  $('#plan-list').innerHTML = data.items.map(t => `
    <div class="plan-item" onclick="openPlan(${t.id})">
      <div><div class="t">${esc(t.title)}</div><div class="m">${esc(t.project)} · 负责人 ${esc(t.owner)}</div></div>
      <div>${levelTag(t.level)} <span class="muted">查看规划 →</span></div>
    </div>`).join('');
}

async function openPlan(id) {
  switchView('planning');
  const p = await api(`/api/tasks/${id}/plan`);
  const steps = p.steps.map(s => `<div class="step"><div class="step-no">${s.step_no}</div>
    <div class="step-title">${esc(s.title)}<div class="step-meta">负责方：${esc(s.agent)} · 预估 ${s.est_minutes} 分钟</div></div>
    ${levelTag(s.level)}</div>`).join('');
  $('#plan-result').innerHTML = `
    <div class="level-hero ${p.level}"><div class="level-badge">${p.level}</div>
      <div><h2>${p.label}</h2><p>${esc(p.task.title)} · 共 ${p.steps.length} 个规划步骤 · 预估 ${p.total_minutes} 分钟</p></div></div>
    <div class="step-tree">${steps}</div>`;
  $('#plan-result').scrollIntoView({behavior:'smooth', block:'nearest'});
}

$('#btn-plan').addEventListener('click', async () => {
  const title = $('#plan-title').value.trim();
  if (!title) return toast('请输入任务标题');
  const r = await api('/api/planning/classify', {method:'POST', body:{title, description:$('#plan-desc').value}});
  const steps = (window.__tpl || null);
  $('#plan-result').innerHTML = `
    <div class="level-hero ${r.level}"><div class="level-badge">${r.level}</div>
      <div><h2>${r.label}</h2><p>风险评分 <b>${r.risk_score}</b> / 100 · ${r.auto_assignable ? '可由 Agent 全自动完成' : '需要人工参与关键环节'}</p></div></div>
    <ul class="reason-list">${r.reasons.map(x => `<li>${esc(x)}</li>`).join('')}</ul>
    <p class="muted" style="margin-bottom:10px">建议的任务拆解（层级规划）：</p>
    <div class="step-tree">${PLAN_TPL[r.level].map(s => `<div class="step"><div class="step-no">${s.step_no}</div>
      <div class="step-title">${s.title}<div class="step-meta">负责方：${s.agent} · 预估 ${s.est_minutes} 分钟</div></div>${levelTag(s.level)}</div>`).join('')}</div>`;
});
const PLAN_TPL = {
  L1:[{step_no:1,title:'任务解析与目标澄清',level:'L1',agent:'Planner-Agent',est_minutes:5},{step_no:2,title:'自动生成与自检',level:'L1',agent:'Coder-Agent',est_minutes:25},{step_no:3,title:'自动化校验与交付',level:'L1',agent:'QA-Agent',est_minutes:10}],
  L2:[{step_no:1,title:'需求拆解与计划生成',level:'L2',agent:'Planner-Agent',est_minutes:15},{step_no:2,title:'候选方案生成（AI）',level:'L1',agent:'Coder-Agent',est_minutes:25},{step_no:3,title:'人工评审与修正',level:'L2',agent:'human',est_minutes:30},{step_no:4,title:'回归验证与合并',level:'L2',agent:'QA-Agent',est_minutes:15}],
  L3:[{step_no:1,title:'目标澄清与风险识别',level:'L3',agent:'human',est_minutes:20},{step_no:2,title:'资料检索与草案辅助',level:'L1',agent:'Retriever-Agent',est_minutes:20},{step_no:3,title:'人工决策与最终签署',level:'L3',agent:'human',est_minutes:45},{step_no:4,title:'失效复盘记录',level:'L2',agent:'Reviewer-Agent',est_minutes:15}],
};

/* ---------- 失效分析 ---------- */
async function renderAnalysis() {
  const [o, rel, pareto, scores, runs] = await Promise.all([
    api('/api/analysis/overview'), api('/api/analysis/reliability'),
    api('/api/analysis/pareto'), api('/api/analysis/failure-scores'), api('/api/agent-runs'),
  ]);
  $('#analysis-stats').innerHTML = [
    ['平均失效评分', rel.average, `评级 ${rel.grade} · 样本 ${rel.sample_size}`, 'c1'],
    ['缺陷总数', o.total_defects, '按类别帕累托分析', 'c4'],
    ['Agent 成功率', o.agent_success_rate + '%', `执行 ${runs.items.length} 次`, 'c2'],
    ['阻塞任务', o.blocked_tasks, '触发 L3 人工升级', 'c3'],
    ['关键少数缺陷', pareto.vital_few.length, pareto.vital_few.join(' / '), ''],
  ].map(([l,v,d,c]) => `<div class="stat ${c}"><div class="label">${l}</div><div class="value">${v}</div><div class="delta">${d}</div></div>`).join('');

  const max = Math.max(1, ...pareto.items.map(i => i.count));
  $('#pareto').innerHTML = `<p class="muted" style="margin-bottom:10px">柱形=缺陷数量，红线=累计占比（80% 分界）</p>` +
    pareto.items.map(i => `<div class="bar-row"><div class="bar-label">${i.category}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${i.count/max*100}%"></div>
      <div class="cum-line" style="left:${Math.min(100,i.cumulative)}%"></div></div>
      <div class="bar-val">${i.count} · ${i.cumulative}%</div></div>`).join('') +
    `<p class="muted" style="margin-top:14px">关键少数（累计≤80%）：<b>${pareto.vital_few.join('、')}</b></p>`;

  $('#score-list').innerHTML = scores.items.slice(0, 10).map(s => `<div class="score-row">
    <div class="grade ${s.reliability}">${s.reliability}</div><div class="score-name">${esc(s.title)}</div>
    <div class="score-num" style="color:${s.score<70?'var(--danger)':s.score<85?'var(--warn)':'var(--ok)'}">${s.score}</div></div>`).join('');

  $('#review-list').innerHTML = `<table><thead><tr><th>任务</th><th>等级</th><th>失效评分</th><th>评级</th><th>复盘结论 / 改进动作</th></tr></thead><tbody>` +
    scores.items.map(s => `<tr><td>${esc(s.title)}</td><td>${levelTag(s.level)}</td><td><b>${s.score}</b></td><td><span class="grade ${s.reliability}" style="width:24px;height:24px;font-size:12px">${s.reliability}</span></td>
      <td>${s.score < 70 ? 'Agent 失效：升级为 L3 人工主导，补充人工评审节点并重新规划' :
           s.score < 85 ? '部分失效：保留 L2 人机协作，增加自动校验规则与回归用例' :
           '运行稳定：维持 L1 自动执行，持续监控缺陷趋势'}</td></tr>`).join('') + '</tbody></table>';
}

/* ---------- 任务操作 ---------- */
async function simRun(id) {
  const outcomes = ['success','success','failure','escalated'];
  const outcome = outcomes[Math.floor(Math.random()*outcomes.length)];
  await api(`/api/tasks/${id}/runs`, {method:'POST', body:{agent_name:'Coder-Agent', outcome, latency_ms: 800+Math.floor(Math.random()*2400), retries: outcome==='failure'?2:0}});
  toast(outcome==='escalated' ? 'Agent 失效 → 已自动升级为 L3 人工介入' : outcome==='failure' ? '本次执行失败，已记录失效事件' : 'Agent 执行成功');
  loadView($('.nav-item.active').dataset.view);
}
async function delTask(id) {
  if (!confirm('确定删除该任务？')) return;
  await api('/api/tasks/' + id, {method:'DELETE'});
  toast('已删除'); loadView('tasks');
}

/* ---------- 新建任务弹窗 ---------- */
$('#btn-new').addEventListener('click', () => { $('#modal').classList.add('show'); $('#f-plan-preview').textContent = ''; });
$('#modal-close').addEventListener('click', () => $('#modal').classList.remove('show'));
$('#modal-cancel').addEventListener('click', () => $('#modal').classList.remove('show'));
$('#modal').addEventListener('click', e => { if (e.target === $('#modal')) $('#modal').classList.remove('show'); });
let previewTimer;
async function previewPlan() {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(async () => {
    const title = $('#f-title').value.trim(); if (!title) return;
    try {
      const r = await api('/api/planning/classify', {method:'POST', body:{title, description:$('#f-desc').value}});
      $('#f-plan-preview').innerHTML = `AI 建议分级：<b>${r.level} ${r.label}</b>（风险分 ${r.risk_score}）— ${r.reasons[0]}`;
    } catch(_) {}
  }, 350);
}
$('#f-title').addEventListener('input', previewPlan);
$('#f-desc').addEventListener('input', previewPlan);
$('#f-submit').addEventListener('click', async () => {
  const title = $('#f-title').value.trim();
  if (!title) return toast('请输入任务标题');
  const payload = {
    title, description: $('#f-desc').value, project: $('#f-project').value || 'Demo',
    owner: $('#f-owner').value || 'unassigned', priority: Number($('#f-priority').value),
    level: $('#f-level').value || undefined, status: 'todo',
  };
  const created = await api('/api/tasks', {method:'POST', body:payload});
  $('#modal').classList.remove('show');
  ['f-title','f-desc'].forEach(id => $('#'+id).value = '');
  toast(`任务已创建，AI 分级为 ${created.level}`);
  switchView('tasks');
});

/* 初始化：自动登录（演示用）+ 加载概览 */
(async function init() {
  try { await api('/api/auth/login', {method:'POST', body:{username:'admin', password:'admin123'}}); } catch(_) {}
  const params = new URLSearchParams(location.search);
  const view = params.get('view');
  if (view && VIEW_TITLES[view]) {
    switchView(view);
    const planId = params.get('plan');
    if (planId && view === 'planning') setTimeout(() => openPlan(Number(planId)), 250);
    const classify = params.get('classify');
    if (classify && view === 'planning') setTimeout(() => {
      $('#plan-title').value = classify;
      $('#btn-plan').click();
    }, 250);
    const modal = params.get('modal');
    if (modal === 'new') setTimeout(() => $('#modal').classList.add('show'), 200);
  } else {
    loadView('overview');
  }
})();
