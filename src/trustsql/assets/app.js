'use strict';

const $ = (id) => document.getElementById(id);
let apiToken = '';
let currentAnswer = null;
let busy = false;
const el = (tag, text, className) => {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = String(text);
  if (className) node.className = className;
  return node;
};
function announce(text) { $('announcements').textContent = text; }
function showError(id, message) { $(id).textContent = message; $(id).hidden = false; }
async function api(path, options = {}) {
  const headers = { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(apiToken ? { Authorization: `Bearer ${apiToken}` } : {}) };
  const response = await fetch(path, { ...options, headers, cache: 'no-store', credentials: 'same-origin' });
  let body;
  try { body = await response.json(); } catch { throw new Error('The server returned an unreadable response. Check the connection and retry.'); }
  if (!response.ok) {
    const detail = body.error || {};
    throw new Error(`${detail.message || 'The request could not be completed.'}${detail.request_id ? ` Request: ${detail.request_id.slice(0, 8)}` : ''}`);
  }
  return body;
}
async function connect() {
  $('global-error').hidden = true;
  try {
    const status = await api('/api/status');
    $('mode-badge').textContent = status.mode === 'demo' ? 'Deterministic demo' : 'Live · DataHub + LLM';
    $('reference-date').textContent = `As of ${status.as_of_date}`;
    $('version').textContent = `v${status.version}`;
    $('connection-label').textContent = status.storage_ready ? `${status.database === 'postgres' ? 'PostgreSQL' : 'SQLite demo'} connected` : 'Database setup needed';
    $('connection-dot').classList.toggle('offline', !status.storage_ready);
    if (!status.storage_ready) showError('global-error', 'The database is not initialized or does not meet the reader policy. Follow the setup instructions before running analysis.');
    $('example-buttons').replaceChildren();
    const labels = ['Net revenue', 'Gross revenue', 'Top products', 'Completed orders'];
    status.examples.slice(0, 4).forEach((question, i) => {
      const button = el('button', labels[i], 'example-button');
      button.type = 'button';
      button.title = question;
      button.addEventListener('click', () => { $('question').value = question; $('question').focus(); });
      $('example-buttons').append(button);
    });
    announce('Workspace connected.');
  } catch (error) {
    $('mode-badge').textContent = 'Connection required';
    $('connection-label').textContent = 'Connection required';
    $('connection-dot').classList.add('offline');
    showError('global-error', error.message);
  }
}
$('token-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  apiToken = $('api-token').value.trim();
  $('api-token').value = '';
  await connect();
});

const viewNames = { analyst: 'SQL analyst', catalog: 'Data catalog', evaluations: 'Evaluations', history: 'Run history' };
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', async () => {
  const view = button.dataset.view;
  document.querySelectorAll('.view').forEach(section => { section.hidden = section.id !== `view-${view}`; });
  document.querySelectorAll('[data-view]').forEach(nav => {
    nav.classList.toggle('active', nav === button);
    if (nav === button) nav.setAttribute('aria-current', 'page'); else nav.removeAttribute('aria-current');
  });
  $('view-name').textContent = viewNames[view];
  if (view === 'catalog') await loadCatalog();
  if (view === 'evaluations') await loadEvaluations();
  if (view === 'history') await loadHistory();
}));

function showTab(name) {
  document.querySelectorAll('[data-tab]').forEach(button => {
    const selected = button.dataset.tab === name;
    button.setAttribute('aria-selected', String(selected));
    button.tabIndex = selected ? 0 : -1;
    $(`panel-${button.dataset.tab}`).hidden = !selected;
  });
}
document.querySelectorAll('[data-tab]').forEach(button => {
  button.addEventListener('click', () => showTab(button.dataset.tab));
  button.addEventListener('keydown', event => {
    if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const tabs = [...document.querySelectorAll('[data-tab]')];
    const i = tabs.indexOf(button);
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (i + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    showTab(tabs[next].dataset.tab); tabs[next].focus();
  });
});
function table(headers, rows, moneyColumns = false) {
  const node = el('table');
  const head = el('thead'); const headRow = el('tr');
  headers.forEach(header => {
    const label = moneyColumns && header.endsWith('_cents') ? `${header.slice(0, -6).replaceAll('_', ' ')} (INR)` : header.replaceAll('_', ' ');
    const th = el('th', label); th.scope = 'col'; headRow.append(th);
  });
  head.append(headRow); node.append(head);
  const body = el('tbody');
  rows.forEach(row => {
    const tr = el('tr');
    row.forEach((value, i) => {
      const numeric = value !== null && value !== '' && Number.isFinite(Number(value));
      const formatted = moneyColumns && headers[i].endsWith('_cents') && numeric ? new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(value) / 100) : value === null ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value);
      tr.append(el('td', formatted, numeric ? 'numeric' : ''));
    });
    body.append(tr);
  });
  node.append(body); return node;
}
function renderChart(answer) {
  $('result-chart').replaceChildren();
  if (answer.columns.length !== 2 || answer.rows.length < 2 || answer.rows.length > 8 || !answer.rows.every(r => Number.isFinite(Number(r[1])) && Number(r[1]) >= 0)) return;
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.classList.add('bar-chart'); svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', `${answer.columns[1]} by ${answer.columns[0]}. Exact values are in the table below.`);
  svg.setAttribute('viewBox', `0 0 600 ${answer.rows.length * 36 + 12}`);
  const max = Math.max(...answer.rows.map(r => Number(r[1])), 1);
  answer.rows.forEach((row, i) => {
    const label = document.createElementNS(ns, 'text'); label.setAttribute('x', '0'); label.setAttribute('y', String(24 + i * 36)); label.textContent = String(row[0]).slice(0, 24);
    const rect = document.createElementNS(ns, 'rect'); rect.setAttribute('x', '180'); rect.setAttribute('y', String(9 + i * 36)); rect.setAttribute('height', '22'); rect.setAttribute('width', String(400 * Number(row[1]) / max)); rect.setAttribute('rx', '3');
    svg.append(label, rect);
  });
  $('result-chart').append(svg);
}
function renderEvidence(datasets) {
  $('evidence-count').textContent = `${datasets.length} datasets`;
  $('evidence-list').replaceChildren();
  datasets.forEach(dataset => {
    const item = el('article', null, 'evidence-dataset');
    item.append(el('h3', dataset.table), el('p', dataset.description));
    const tags = el('div', null, 'evidence-source');
    tags.append(el('span', dataset.source === 'datahub' ? 'DataHub' : 'Demo snapshot', 'small-tag'));
    tags.append(el('span', dataset.certified ? 'Curated definition' : 'Review definition', dataset.certified ? 'small-tag' : 'small-tag warn'));
    tags.append(el('span', dataset.freshness === 'fixture' ? 'Synthetic fixture' : `Freshness: ${dataset.freshness}`, 'small-tag'));
    item.append(tags); $('evidence-list').append(item);
  });
}
function renderAnswer(answer) {
  currentAnswer = answer;
  $('answer-panel').hidden = false;
  $('empty-state').hidden = true;
  $('answer-status').textContent = { answer: 'Analysis complete', clarification: 'Clarification needed', refusal: 'Request outside scope' }[answer.status];
  $('answer-heading').textContent = answer.status === 'answer' ? 'Here’s what the data shows.' : answer.status === 'clarification' ? 'Let’s make the question precise.' : 'This request needs a different approach.';
  $('answer-explanation').textContent = answer.explanation;
  $('answer-timing').textContent = `${answer.duration_ms} ms · ${answer.evidence.length} datasets`;
  $('warnings').replaceChildren(...answer.warnings.map(message => el('div', message, 'notice')));
  $('answer-tabs').hidden = answer.status !== 'answer';
  $('result-table').replaceChildren();
  if (answer.status === 'answer') {
    if (answer.rows.length) $('result-table').append(table(answer.columns, answer.rows, true));
    else $('result-table').append(el('p', 'No rows matched this question.', 'muted'));
  }
  renderChart(answer);
  $('result-caption').textContent = answer.status === 'answer' ? `${answer.row_count} ${answer.row_count === 1 ? 'row' : 'rows'} returned${answer.truncated ? ' · row limit reached' : ''}. Monetary values are displayed in INR; SQL returns paise.` : '';
  $('sql-code').textContent = answer.sql || 'No query was executed.';
  const lineage = answer.inspection?.columns || [];
  $('lineage-section').hidden = !lineage.length;
  $('lineage-table').replaceChildren();
  if (lineage.length) $('lineage-table').append(table(['Output column', 'Source columns', 'Resolution'], lineage.map(item => [item.output, item.sources.join(', ') || 'No column value origin (e.g. row count or constant)', item.resolved ? 'Resolved' : 'Partial'])));
  $('copy-sql').textContent = 'Copy SQL';
  $('trace-list').replaceChildren();
  answer.stages.forEach(stage => {
    const li = el('li');
    const mark = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    mark.setAttribute('viewBox', '0 0 24 24'); mark.setAttribute('width', '18'); mark.setAttribute('height', '18');
    mark.setAttribute('fill', 'none'); mark.setAttribute('stroke', '#245c42'); mark.setAttribute('stroke-width', '2'); mark.setAttribute('aria-hidden', 'true');
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path'); path.setAttribute('d', 'm5 12 4 4 10-10'); mark.append(path);
    const detail = el('div'); detail.append(el('strong', stage.name), el('p', stage.detail)); li.append(mark, detail); $('trace-list').append(li);
  });
  $('request-reference').textContent = `Run ${answer.request_id.slice(0, 8)}`;
  renderEvidence(answer.evidence);
  showTab('results'); announce(answer.status === 'answer' ? `Analysis complete. ${answer.row_count} rows returned.` : answer.explanation);
}
$('question-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (busy || !$('question-form').reportValidity()) return;
  busy = true; $('run-button').disabled = true; $('question').readOnly = true; $('question-form').setAttribute('aria-busy', 'true'); $('run-error').hidden = true; $('loading').hidden = false;
  $('answer-panel').hidden = true; $('empty-state').hidden = true;
  try { renderAnswer(await api('/api/query', { method: 'POST', body: JSON.stringify({ question: $('question').value.trim() }) })); }
  catch (error) { showError('run-error', error.message); $('empty-state').hidden = false; announce('Analysis failed. Read the error above.'); }
  finally { busy = false; $('run-button').disabled = false; $('question').readOnly = false; $('question-form').setAttribute('aria-busy', 'false'); $('loading').hidden = true; }
});
$('question').addEventListener('keydown', event => { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); $('question-form').requestSubmit(); } });
$('copy-sql').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(currentAnswer?.sql || ''); $('copy-sql').textContent = 'Copied'; announce('SQL copied.'); }
  catch { $('copy-sql').textContent = 'Select SQL to copy'; }
});
function loadingText(target, text = 'Loading…') { $(target).replaceChildren(el('p', text, 'muted')); }
async function loadCatalog() {
  loadingText('catalog-list');
  try {
    const data = await api('/api/catalog');
    $('catalog-count').textContent = data.datasets.length;
    $('catalog-source').textContent = data.source === 'datahub' ? 'Live DataHub metadata' : 'Versioned demo snapshot';
    $('catalog-list').replaceChildren();
    data.datasets.forEach(dataset => {
      const details = el('details', null, 'catalog-entry'); const summary = el('summary');
      summary.append(el('strong', `analytics.${dataset.table}`), el('span', `${dataset.columns.length} columns · ${dataset.source}`));
      const content = el('div', null, 'catalog-entry-content'); content.append(el('p', dataset.description), el('p', dataset.urn, 'urn'));
      const scroll = el('div', null, 'table-scroll'); scroll.append(table(['Column', 'Type', 'Description'], dataset.columns.map(c => [c.name, c.type, c.description || '—']))); content.append(scroll);
      details.append(summary, content); $('catalog-list').append(details);
    });
  } catch (error) { loadingText('catalog-list', error.message); }
}
async function loadEvaluations() {
  loadingText('evaluation-content');
  try {
    const report = await api('/api/evaluations');
    $('evaluation-content').replaceChildren();
    if (report.state === 'not_run') {
      const empty = el('div', null, 'view-empty'); empty.append(el('h2', 'No evaluation report yet.'), el('p', 'Run the offline development suite, then refresh this page. Model evaluation is separate from deterministic fixture checks.'));
      const pre = el('pre'); pre.append(el('code', 'python -m trustsql.cli evaluate')); empty.append(pre); $('evaluation-content').append(empty); return;
    }
    $('evaluation-content').append(el('div', report.label, 'notice'));
    const summary = el('div', null, 'evaluation-summary'); summary.append(el('strong', `${report.passed} / ${report.cases}`), el('span', 'checks passed across synthetic data seeds'));
    const detail = el('p', `Model: ${report.model} · Context: ${report.metadata_source} · Variant: ${report.variant}`, 'muted small');
    const scroll = el('div', null, 'table-scroll'); scroll.append(table(['Case', 'Seed', 'Split', 'Result'], report.results.map(r => [r.id, r.seed, r.split, r.passed ? 'Passed' : `Failed (${r.error_code || r.observed_status})`])));
    $('evaluation-content').append(summary, detail, scroll);
  } catch (error) { loadingText('evaluation-content', error.message); }
}
async function loadHistory() {
  loadingText('history-content');
  try {
    const { runs } = await api('/api/runs');
    $('history-content').replaceChildren();
    if (!runs.length) { $('history-content').append(el('p', 'No runs recorded yet. Ask a question to create the first audit record.', 'muted')); return; }
    $('history-content').append(table(['Run', 'Time', 'Status', 'Datasets', 'Duration', 'Mode'], runs.map(run => [run.request_id.slice(0, 8), new Date(run.created_at).toLocaleString(), run.status, run.tables.join(', ') || '—', `${run.duration_ms} ms`, run.mode])));
  } catch (error) { loadingText('history-content', error.message); }
}
$('refresh-evaluations').addEventListener('click', loadEvaluations);
$('refresh-history').addEventListener('click', loadHistory);
connect();

