"""HTML template constants for HTMLSelfRenderer.

CSS + JS live as Python string constants so the rendered HTML is one self-
contained file (no external CDN, no Mermaid, no fetch). All interactivity is
driven by JS_INTERACTIVE, which is serialized verbatim into a <script> block.

P0 #2 — zero external script tags.
P0 #3 — status export / import + dirty tracker (sessionStorage).
"""

from __future__ import annotations

CSS = """\
:root {
  --bg: #f8fafc;
  --surface: #ffffff;
  --fg: #0f172a;
  --muted: #475569;
  --border: #e2e8f0;
  --border-strong: #cbd5e1;
  --accent: #2563eb;
  --accent-fg: #ffffff;
  --passed: #059669;
  --failed: #dc2626;
  --pending: #6b7280;
  --inprogress: #d97706;
  --blocked: #4b5563;
  --skipped: #2563eb;
  --focus: #2563eb;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
               "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
  background: var(--bg);
  color: var(--fg);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
a { color: var(--accent); }
button { font-family: inherit; }
header {
  padding: 0.875rem 1.25rem;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem 1rem;
  position: sticky;
  top: 0;
  z-index: 10;
}
header h1 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}
header .toolbar {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.progress {
  flex: 1 1 200px;
  max-width: 360px;
  min-width: 180px;
}
.progress-bar {
  height: 8px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--accent);
  width: 0%;
  transition: width 0.3s ease;
}
.progress-text {
  font-size: 0.8125rem;
  color: var(--muted);
  margin-top: 0.25rem;
  font-variant-numeric: tabular-nums;
}
.btn {
  padding: 0.5rem 0.875rem;
  background: var(--surface);
  color: var(--fg);
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background 0.15s, border-color 0.15s, transform 0.05s;
}
.btn:hover { background: #f1f5f9; }
.btn:active { transform: translateY(1px); }
.btn:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: 2px;
}
.btn-primary {
  background: var(--accent);
  color: var(--accent-fg);
  border-color: var(--accent);
}
.btn-primary:hover { background: #1d4ed8; border-color: #1d4ed8; }
.btn.is-dirty {
  border-color: var(--inprogress);
  box-shadow: 0 0 0 2px rgba(217, 119, 6, 0.18);
}
main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  min-height: calc(100vh - 73px);
}
#graph-wrap {
  padding: 1rem;
  overflow: auto;
  background: var(--surface);
  margin: 1rem;
  border: 1px solid var(--border);
  border-radius: 10px;
}
#graph-wrap svg { display: block; max-width: 100%; height: auto; }
.case-node { cursor: pointer; }
.case-node:hover rect,
.case-node:hover polygon,
.case-node:hover path { filter: brightness(0.95); }
.case-node:focus { outline: none; }
.case-node:focus-visible rect,
.case-node:focus-visible polygon,
.case-node:focus-visible path {
  stroke-width: 3;
  stroke: var(--focus);
}
#detail-panel {
  padding: 1.25rem;
  background: var(--surface);
  border-left: 1px solid var(--border);
  overflow-y: auto;
  min-height: 0;
}
#detail-panel.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
  text-align: center;
  font-size: 0.95rem;
}
.case-title {
  font-size: 1.0625rem;
  font-weight: 600;
  margin: 0 0 0.5rem;
  letter-spacing: -0.005em;
}
.case-meta {
  font-size: 0.8125rem;
  color: var(--muted);
  margin-bottom: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.case-type {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  background: #eef2ff;
  color: #4338ca;
  font-weight: 500;
}
.case-type-positive { background: #ecfdf5; color: #047857; }
.case-type-negative { background: #fef2f2; color: #b91c1c; }
.case-type-edge { background: #fffbeb; color: #b45309; }
.case-type-security { background: #fdf2f8; color: #be185d; }
.case-desc {
  color: #334155;
  line-height: 1.6;
  margin-bottom: 1rem;
  font-size: 0.9375rem;
  white-space: pre-wrap;
}
.steps {
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
  counter-reset: step;
}
.steps li {
  padding: 0.625rem 0.75rem;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 6px;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
}
.step-num {
  font-weight: 600;
  color: var(--accent);
  margin-right: 0.375rem;
  font-variant-numeric: tabular-nums;
}
.status-buttons {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  margin-top: 1rem;
}
.status-btn {
  min-height: 44px;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-strong);
  background: var(--surface);
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
  text-align: center;
}
.status-btn:hover { background: #f8fafc; }
.status-btn:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: 2px;
}
.status-btn.active.passed { background: var(--passed); color: white; border-color: var(--passed); }
.status-btn.active.failed { background: var(--failed); color: white; border-color: var(--failed); }
.status-btn.active.blocked { background: var(--blocked); color: white; }
.status-btn.active.skipped { background: var(--skipped); color: white; border-color: var(--skipped); }
.note-input {
  width: 100%;
  margin-top: 0.625rem;
  padding: 0.5rem 0.625rem;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.875rem;
  resize: vertical;
  min-height: 64px;
  background: var(--surface);
  color: var(--fg);
}
.note-input:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: 2px;
  border-color: var(--focus);
}
.failure-cause {
  margin-top: 0.75rem;
  padding: 0.625rem 0.75rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  color: #991b1b;
  font-size: 0.875rem;
}
footer {
  padding: 0.75rem 1.25rem;
  background: var(--surface);
  border-top: 1px solid var(--border);
  text-align: center;
  color: var(--muted);
  font-size: 0.8125rem;
}
@media (max-width: 768px) {
  main { grid-template-columns: 1fr; }
  #detail-panel {
    border-left: none;
    border-top: 1px solid var(--border);
    max-height: 60vh;
  }
  header h1 { font-size: 1rem; }
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f172a;
    --surface: #1e293b;
    --fg: #f1f5f9;
    --muted: #94a3b8;
    --border: #334155;
    --border-strong: #475569;
  }
  body { background: var(--bg); color: var(--fg); }
  header, footer, #graph-wrap, #detail-panel { background: var(--surface); }
  .progress-bar { background: #334155; }
  .btn { background: var(--surface); color: var(--fg); border-color: var(--border-strong); }
  .btn:hover { background: #334155; }
  .steps li { background: #0f172a; border-color: var(--border); }
  .case-desc { color: #cbd5e1; }
  .note-input { background: #0f172a; color: var(--fg); }
  .case-type { background: #312e81; color: #c7d2fe; }
  .case-type-positive { background: #064e3b; color: #6ee7b7; }
  .case-type-negative { background: #7f1d1d; color: #fca5a5; }
  .case-type-edge { background: #78350f; color: #fcd34d; }
  .case-type-security { background: #831843; color: #f9a8d4; }
  .failure-cause { background: #7f1d1d; border-color: #b91c1c; color: #fecaca; }
  #detail-panel.empty { color: var(--muted); }
}
"""

INITIAL_STATUSES_JS = """\
window.__INITIAL_STATUSES__ = $statuses_json;
window.__CASEMAP_CASES__ = $cases_json;
window.__CASEMAP_NODE_TO_CASE__ = $node_to_case_json;
(function() {
  try {
    const existing = JSON.parse(localStorage.getItem('casemap_statuses_v1') || '{}');
    let touched = false;
    for (const [k, v] of Object.entries(window.__INITIAL_STATUSES__)) {
      if (!(k in existing)) { existing[k] = v; touched = true; }
    }
    if (touched) localStorage.setItem('casemap_statuses_v1', JSON.stringify(existing));
  } catch (e) { /* ignore */ }
})();
"""

JS_INTERACTIVE = r"""
const STORAGE_KEY = 'casemap_statuses_v1';
const DIRTY_KEY = 'casemap_dirty';
const CASES = window.__CASEMAP_CASES__ || {};
const NODE_TO_CASE = window.__CASEMAP_NODE_TO_CASE__ || {};
const INITIAL_STATUSES = window.__INITIAL_STATUSES__ || {};

function loadStatuses() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
  catch (e) { return {}; }
}
function saveStatuses(s) { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)); }
function getStatus(id) {
  const all = loadStatuses();
  return all[id] || { status: 'pending', note: '' };
}
function markDirty() { sessionStorage.setItem(DIRTY_KEY, '1'); refreshDirtyBadge(); }
function clearDirty() { sessionStorage.removeItem(DIRTY_KEY); refreshDirtyBadge(); }
function isDirty() { return sessionStorage.getItem(DIRTY_KEY) === '1'; }

function refreshDirtyBadge() {
  const btn = document.querySelector('.export-status-btn');
  if (!btn) return;
  if (isDirty()) btn.classList.add('is-dirty');
  else btn.classList.remove('is-dirty');
}

function setStatus(id, status) {
  const all = loadStatuses();
  const cur = all[id] || { note: '' };
  all[id] = Object.assign({}, cur, { status: status, updated_at: new Date().toISOString() });
  saveStatuses(all);
  markDirty();
  updateProgress();
  if (id === currentCaseId) renderDetail(id);
}

function setNote(id, note) {
  const all = loadStatuses();
  const cur = all[id] || { status: 'pending' };
  all[id] = Object.assign({}, cur, { note: note, updated_at: new Date().toISOString() });
  saveStatuses(all);
  markDirty();
}

function updateProgress() {
  const all = loadStatuses();
  const total = Object.keys(CASES).length;
  const done = Object.values(all).filter(function (s) {
    return s && (s.status === 'passed' || s.status === 'failed');
  }).length;
  const pct = total ? Math.round(done / total * 100) : 0;
  const fill = document.querySelector('.progress-fill');
  const text = document.querySelector('.progress-text');
  if (fill) fill.style.width = pct + '%';
  if (text) text.textContent = done + ' / ' + total + ' 已完成 (' + pct + '%)';
}

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
    return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
  });
}

function labelFor(t) {
  return ({ positive: '正向', negative: '逆向', edge: '边界', security: '安全' })[t] || t;
}

let currentCaseId = null;

function renderDetail(caseId) {
  const c = CASES[caseId];
  const panel = document.getElementById('detail-panel');
  if (!c) {
    panel.classList.add('empty');
    panel.innerHTML = '← 点击左侧节点查看详情';
    currentCaseId = null;
    return;
  }
  currentCaseId = caseId;
  panel.classList.remove('empty');
  const cur = getStatus(caseId);
  const steps = (c.steps || []);
  const stepsHtml = steps.length
    ? '<ol class="steps">' + steps.map(function (s) {
        return '<li><span class="step-num">' + s.order + '.</span>'
          + '<strong>' + escapeHtml(s.action) + '</strong>'
          + '<br><em>预期：</em>' + escapeHtml(s.expected) + '</li>';
      }).join('') + '</ol>'
    : '';
  const failHtml = (cur.status === 'failed' && cur.note)
    ? '<div class="failure-cause"><strong>失败原因：</strong>'
      + escapeHtml(cur.note) + '</div>'
    : '';
  const typeLabel = labelFor(c.type);
  const endpointHtml = c.endpoint_ref
    ? ' <span>·</span> <span>' + escapeHtml(c.endpoint_ref) + '</span>'
    : '';
  const statusList = [
    { key: 'passed', icon: '✅', label: '通过' },
    { key: 'failed', icon: '❌', label: '失败' },
    { key: 'blocked', icon: '🚫', label: '阻塞' },
    { key: 'skipped', icon: '⏭️', label: '跳过' },
  ];
  const buttonsHtml = statusList.map(function (it) {
    const active = cur.status === it.key ? ' active' : '';
    return '<button type="button" data-status="' + it.key + '"'
      + ' class="status-btn ' + it.key + active + '"'
      + ' aria-label="标记为' + it.label + '">'
      + it.icon + ' ' + it.label + '</button>';
  }).join('');

  panel.innerHTML = ''
    + '<h2 class="case-title">' + escapeHtml(c.title) + '</h2>'
    + '<div class="case-meta">'
    + '<span class="case-type case-type-' + escapeHtml(c.type) + '">' + typeLabel + '</span>'
    + endpointHtml
    + '</div>'
    + '<div class="case-desc">' + escapeHtml(c.description || '') + '</div>'
    + stepsHtml
    + '<div class="status-buttons" role="group" aria-label="标记测试结果">'
    + buttonsHtml
    + '</div>'
    + '<textarea class="note-input" placeholder="备注（可选，如失败原因）"'
    + ' aria-label="备注">' + escapeHtml(cur.note || '') + '</textarea>'
    + failHtml;

  panel.querySelectorAll('.status-buttons button').forEach(function (btn) {
    btn.addEventListener('click', function () { setStatus(caseId, btn.dataset.status); });
  });
  const noteInput = panel.querySelector('.note-input');
  if (noteInput) {
    noteInput.addEventListener('change', function (e) { setNote(caseId, e.target.value); });
  }
}

function downloadBlob(content, filename, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
}

function exportProgress() {
  const data = {
    version: 1,
    exported_at: new Date().toISOString(),
    statuses: loadStatuses(),
  };
  const date = new Date().toISOString().slice(0, 10);
  downloadBlob(JSON.stringify(data, null, 2), 'casemap-status-' + date + '.json', 'application/json');
  clearDirty();
}

function exportReport() {
  const all = loadStatuses();
  const rows = Object.keys(all).map(function (id) {
    const s = all[id];
    const c = CASES[id];
    if (!c) return '';
    const note = (s.note || '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
    return '| ' + escapeHtml(c.title) + ' | ' + labelFor(c.type)
      + ' | ' + s.status + ' | ' + note + ' |';
  }).filter(Boolean).join('\n');
  const md = '# 测试报告\n\n'
    + '| 用例 | 类型 | 状态 | 备注 |\n'
    + '|------|------|------|------|\n' + rows + '\n';
  downloadBlob(md, 'test-report.md', 'text/markdown');
}

function importProgressFromText(text) {
  const data = JSON.parse(text);
  if (!data || typeof data !== 'object') throw new Error('文件格式不正确');
  const incoming = data.statuses || {};
  const existing = loadStatuses();
  const merged = Object.assign({}, incoming, existing);
  saveStatuses(merged);
  sessionStorage.removeItem(DIRTY_KEY);
  location.reload();
}

document.addEventListener('DOMContentLoaded', function () {
  updateProgress();
  refreshDirtyBadge();

  document.addEventListener('click', function (e) {
    const target = e.target;
    const node = target && target.closest ? target.closest('.case-node') : null;
    if (node) {
      e.preventDefault();
      const caseId = node.getAttribute('data-case-id') || (NODE_TO_CASE[node.id] || node.id);
      if (caseId) renderDetail(caseId);
    }
  });

  const exportStatusBtn = document.querySelector('.export-status-btn');
  if (exportStatusBtn) exportStatusBtn.addEventListener('click', exportProgress);

  const exportReportBtn = document.querySelector('.export-report-btn');
  if (exportReportBtn) exportReportBtn.addEventListener('click', exportReport);

  const importBtn = document.querySelector('.import-btn');
  const importInput = document.getElementById('status-import');
  if (importBtn && importInput) {
    importBtn.addEventListener('click', function () { importInput.click(); });
    importInput.addEventListener('change', function (e) {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      file.text().then(function (text) {
        try { importProgressFromText(text); }
        catch (err) { alert('导入失败：' + (err && err.message ? err.message : err)); }
      });
    });
  }
});

window.addEventListener('beforeunload', function (e) {
  if (isDirty()) {
    e.preventDefault();
    e.returnValue = '测试进度尚未导出，确定离开？';
    return e.returnValue;
  }
});
"""

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light dark">
<title>{{ title }} - 测试用例脑图</title>
<style>{{ css }}</style>
</head>
<body>
<header role="banner">
  <h1>{{ title }} - 测试用例脑图</h1>
  <div class="progress" role="progressbar" aria-label="完成进度" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
    <div class="progress-bar"><div class="progress-fill"></div></div>
    <div class="progress-text">0 / 0 已完成</div>
  </div>
  <div class="toolbar">
    <button type="button" class="btn export-status-btn" aria-label="导出进度 JSON">💾 导出进度</button>
    <button type="button" class="btn import-btn" aria-label="从 JSON 文件导入进度">📥 导入进度</button>
    <input type="file" id="status-import" accept="application/json,.json" hidden>
    <button type="button" class="btn btn-primary export-report-btn" aria-label="导出 Markdown 报告">📤 导出报告</button>
  </div>
</header>
<main>
  <div id="graph-wrap" role="region" aria-label="测试用例脑图">
    {{ svg }}
  </div>
  <aside id="detail-panel" class="empty" role="region" aria-label="用例详情">
    ← 点击左侧节点查看详情
  </aside>
</main>
<footer>casemap · 由接口列表自动生成 · 用例状态保存在本地浏览器</footer>
<script>{{ init_js }}</script>
<script>{{ js }}</script>
</body>
</html>
"""
