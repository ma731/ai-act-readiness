// Screen your file: drop a CSV of proposals, watch each one pass the six people, get the verdicts back.
// The sample file plays from results made at build time; your own file runs the real engine in this browser.
import { check, engineStarted } from './engine.js';

const $ = (s) => document.querySelector(s);
const DATA = JSON.parse($('#screen-data').textContent);
const calm = !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const TIERS = { prohibited: 'Prohibited', high_risk: 'High-risk', transparency: 'Transparency', minimal: 'Minimal' };
const GLYPH = {
  prohibited: '<path d="M13 13l14 14M27 13L13 27"/>', high_risk: '<path d="M20 11v11"/><path d="M20 28.5v.01"/>',
  transparency: '<path d="M20 11.5v.01"/><path d="M20 18v11"/>', minimal: '<path d="M12 21l5.5 5.5L28 15"/>',
};
const FILL = { prohibited: '#f0685a', high_risk: '#f2a53a', transparency: '#5d9cf0', minimal: '#4fc57c' };
const tile = (t) => `<svg class="tile" viewBox="0 0 40 40" aria-hidden="true"><rect x="1.5" y="1.5" width="37" height="37" rx="12" fill="${FILL[t]}"/><rect x="1.5" y="1.5" width="37" height="18" rx="12" fill="#fff" opacity=".16"/><rect x="1.5" y="1.5" width="37" height="37" rx="12" fill="none" stroke="#ffcc00" stroke-width="1.5"/><g fill="none" stroke="#fff" stroke-width="4.4" stroke-linecap="round" stroke-linejoin="round">${GLYPH[t]}</g></svg>`;
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const ui = {
  drop: $('#sc-drop'), file: $('#sc-file'), pick: $('#sc-pick'), sample: $('#sc-sample'), note: $('#sc-note'),
  run: $('#sc-run'), people: [...document.querySelectorAll('.sc-person')], folder: $('#sc-folder'), now: $('#sc-now'),
  bar: $('#sc-bar'), list: $('#sc-list'), counts: Object.fromEntries([...document.querySelectorAll('[data-count]')].map((el) => [el.dataset.count, el])),
  done: $('#sc-done'), save: $('#sc-save'), again: $('#sc-again'), name: $('#sc-name'),
};
let results = [], token = 0;

// ------------------------------------------------------------------ reading the file --- //
function parseCSV(text) {
  const rows = []; let row = [], cell = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += c; }
    else if (c === '"') q = true;
    else if (c === ',' || c === ';' && !text.includes(',')) { row.push(cell); cell = ''; }
    else if (c === '\n' || c === '\r') { if (c === '\r' && text[i + 1] === '\n') i++; row.push(cell); cell = ''; if (row.some((x) => x.trim())) rows.push(row); row = []; }
    else cell += c;
  }
  row.push(cell); if (row.some((x) => x.trim())) rows.push(row);
  return rows;
}
function toProposals(text) {
  const rows = parseCSV(text.replace(/^﻿/, ''));
  if (!rows.length) return [];
  const head = rows[0].map((h) => h.trim().toLowerCase());
  const col = (...names) => head.findIndex((h) => names.includes(h));
  let t = col('proposal', 'description', 'text', 'idea', 'use case'), body = rows.slice(1);
  if (t < 0) { t = rows[0].length - 1; body = rows; }             // no header we know: the last column is the text
  const id = col('id'), title = col('title', 'name'), company = col('company', 'organisation', 'organization');
  return body.map((r, i) => ({ id: (r[id] || `R${String(i + 1).padStart(2, '0')}`).trim(), title: (r[title] || '').trim(), company: (r[company] || '').trim(),
    proposal: (r[t] || '').trim().slice(0, 4000) })).filter((p) => p.proposal.length > 8).slice(0, 300);
}

// ------------------------------------------------------------------ the run ------------ //
function rowHTML(p, r) {
  const quotes = [...new Set(r.quotes.map((x) => x.quote))];
  return `<details><summary>${tile(r.tier)}<span class="sc-id">${esc(p.id)}</span>
    <span class="sc-what"><b>${esc(p.title || p.proposal.slice(0, 60))}</b>${p.company ? `<span>${esc(p.company)}</span>` : ''}</span>
    <span class="stamp ${r.tier}">${TIERS[r.tier]}</span>${r.review.length ? '<span class="sc-flag">Review</span>' : ''}
    <span class="sc-arts">${esc(r.articles.slice(0, 3).join(', '))}</span></summary>
    <div class="sc-detail"><p><b>${esc(r.verdict)}.</b> ${esc(r.steps.slice(1, -1)[0] || '')}</p>
    ${quotes.length ? `<p class="sc-q">Decided by: ${quotes.slice(0, 2).map((x) => `<mark>${esc(x)}</mark>`).join(' ')}</p>` : ''}
    ${r.obligations.length ? `<ul>${r.obligations.slice(0, 3).map((o) => `<li><b>${esc(o.article)}</b> ${esc(o.duty)}</li>`).join('')}</ul>` : ''}
    ${r.review.length ? `<p class="sc-rev">A person should check: ${esc(r.review[0])}.</p>` : ''}</div></details>`;
}
async function screen(proposals, name, known) {
  const mine = ++token;
  results = [];
  ui.drop.hidden = true; ui.run.hidden = false; ui.done.hidden = true; ui.list.innerHTML = '';
  ui.name.textContent = `${name} · ${proposals.length} proposal${proposals.length === 1 ? '' : 's'}`;
  Object.values(ui.counts).forEach((el) => { el.textContent = '0'; });
  if (!known && !engineStarted()) ui.now.innerHTML = '<b>Loading the rules engine.</b><span>The first file downloads about 10 MB, then it is quick.</span>';
  const each = calm ? 0 : Math.max(140, Math.min(900, 22000 / proposals.length));
  const count = { prohibited: 0, high_risk: 0, transparency: 0, minimal: 0, review: 0 };
  for (let i = 0; i < proposals.length; i++) {
    const p = proposals[i];
    let r;
    try { r = known?.[p.id] || await check({ text: p.proposal, answers: [], asked: [] }); } catch {
      ui.now.innerHTML = '<b>The rules engine could not load.</b><span>Check your connection, or use the sample file.</span>'; return;
    }
    if (mine !== token) return;
    ui.now.innerHTML = `<b>${esc(p.id)} · ${esc(p.title || 'Proposal')}</b><span>${esc(p.proposal.slice(0, 150))}${p.proposal.length > 150 ? '…' : ''}</span>`;
    if (each) {     // the folder goes down the line; each person lights up as it passes
      ui.folder.style.transition = 'none'; ui.folder.style.left = '0%'; ui.folder.dataset.tier = '';
      ui.folder.getBoundingClientRect();
      ui.folder.style.transition = `left ${each * 0.82}ms linear`; ui.folder.style.left = '100%';
      ui.people.forEach((el, k) => setTimeout(() => { if (mine === token) { el.classList.add('on'); setTimeout(() => el.classList.remove('on'), Math.max(160, each * 0.3)); } }, (each * 0.82 * (k + 0.5)) / ui.people.length));
      await wait(each * 0.86);
      if (mine !== token) return;
      ui.folder.dataset.tier = r.tier;
      await wait(each * 0.14);
    }
    results.push({ p, r });
    count[r.tier] += 1; if (r.review.length) count.review += 1;
    for (const [k, el] of Object.entries(ui.counts)) if (el.textContent !== String(count[k])) { el.textContent = count[k]; el.closest('.fact')?.animate?.([{ transform: 'scale(1.06)' }, { transform: 'none' }], { duration: 260, easing: 'ease-out' }); }
    const li = document.createElement('li'); li.innerHTML = rowHTML(p, r); ui.list.prepend(li);
    ui.bar.style.transform = `scaleX(${(i + 1) / proposals.length})`;
  }
  ui.now.innerHTML = `<b>Done: ${proposals.length} screened.</b><span>${count.review} waiting for a person. Open any row to see why.</span>`;
  ui.done.hidden = false;
}

function download() {
  const cell = (x) => `"${String(x ?? '').replace(/"/g, '""')}"`;
  const lines = [['id', 'company', 'title', 'tier', 'verdict', 'articles', 'needs_review', 'review_reason', 'next_deadline'].join(',')]
    .concat(results.map(({ p, r }) => [p.id, p.company, p.title, r.tier, r.verdict, r.articles.join('; '), r.review.length ? 'yes' : 'no', r.review[0] || '', r.next_deadline || ''].map(cell).join(',')));
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob(['﻿' + lines.join('\r\n')], { type: 'text/csv' })); a.download = 'veredicto-screening.csv';
  document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

async function take(file) {
  if (!file) return;
  if (!/\.(csv|txt)$/i.test(file.name)) { ui.note.textContent = 'That is not a CSV. In Excel, use File, Save as, CSV, then drop it here.'; return; }
  const proposals = toProposals(await file.text());
  if (!proposals.length) { ui.note.textContent = 'No proposals found. The file needs a column called proposal (title, id and company are optional).'; return; }
  ui.note.textContent = '';
  screen(proposals, file.name);
}
ui.pick.addEventListener('click', () => ui.file.click());
ui.file.addEventListener('change', () => { take(ui.file.files[0]); ui.file.value = ''; });
ui.sample.addEventListener('click', () => screen(DATA.rows, 'proposals_sample.csv', DATA.results));
['dragenter', 'dragover'].forEach((t) => ui.drop.addEventListener(t, (ev) => { ev.preventDefault(); ui.drop.classList.add('over'); }));
['dragleave', 'drop'].forEach((t) => ui.drop.addEventListener(t, (ev) => { ev.preventDefault(); ui.drop.classList.remove('over'); }));
ui.drop.addEventListener('drop', (ev) => take(ev.dataTransfer.files[0]));
ui.save.addEventListener('click', download);
ui.again.addEventListener('click', () => { token += 1; ui.run.hidden = true; ui.drop.hidden = false; });
window.SCREEN_READY = true;
