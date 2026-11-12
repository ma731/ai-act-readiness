// Numbers that count up once, and a small voice guide that can also check an idea against
// the AI Act by running the site's own Python screener in the browser (Pyodide). Pre-recorded lines play as mp3
// (same voice in every browser, works on Pages); anything else, like live numbers,
// uses the best voice this browser has.
(() => {
  const up = document.currentScript?.dataset.up || '';
  const page = document.body.dataset.page || 'index.html';
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- numbers ----
  const nums = [...document.querySelectorAll('.num[data-count]')];
  const fmt = n => Math.round(n).toLocaleString('en-US');
  if (!still && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver(es => es.forEach(en => {
      if (!en.isIntersecting) return;
      io.unobserve(en.target);
      const el = en.target, to = +el.dataset.count, t0 = performance.now(), dur = 900;
      const step = t => {
        const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 4);
        el.textContent = fmt(to * e);
        if (k < 1) requestAnimationFrame(step); else el.textContent = fmt(to);
      };
      el.textContent = '0';
      requestAnimationFrame(step);
    }), { threshold: 0.4 });
    nums.forEach(n => io.observe(n));
  }

  // ---- guide ----
  const PAGE_LINE = { 'index.html': 'intro', 'supply.html': 'supply', 'proposals.html': 'intake', 'cases.html': 'eu', 'stress.html': 'stress',
    'inventory.html': 'case', 'evidence.html': 'fairness', 'roadmap.html': 'obligations', 'documents.html': 'documents' };
  const here = PAGE_LINE[page] || (page.startsWith('docs/') ? 'documents' : 'intro');
  const ASK = [
    ['live', /how many|numbers?|count|right now|today|stats/],
    ['how', /how (does|do|is)|work|model|code|quote|decid/],
    ['case', /cierzo|case stud|insur|six|inventor/],
    ['fairness', /fair|bias|born|abroad|price|pricing|health|evidence|survey/],
    ['obligations', /oblig|deadline|date|due|overdue|roadmap|when/],
    ['eu', /public|sector|eu data|europe|commission|live|tech watch|dataset/],
    ['stress', /stress|test|disguis|accura|keyword/],
    ['highrisk', /high.?risk|annex/],
    ['aiact', /ai act|regulation|law|omnibus|what is/],
    ['legal', /legal|advice|lawyer|real\b/],
    ['who', /who|built|marco|author|made/],
    ['why', /why|accenture|matter|business|value/],
    ['data', /data|source|ine|osakidetza/],
    ['runs', /azure|claude|openai|key|offline|run/],
  ];
  const CHIPS = { intro: ['how', 'case', 'eu'], eu: ['live', 'highrisk', 'how'], case: ['fairness', 'obligations', 'how'],
    fairness: ['case', 'data', 'legal'], obligations: ['case', 'highrisk', 'legal'], stress: ['how', 'runs', 'eu'],
    intake: ['how', 'highrisk', 'case'], supply: ['highrisk', 'how', 'case'], documents: ['case', 'fairness', 'obligations'] };
  const LABEL = { how: 'How does it work?', case: 'The case study', eu: 'The live EU data', live: 'Live numbers',
    fairness: 'Fairness findings', obligations: 'What is due when?', highrisk: 'What is high-risk?', data: 'Where is the data from?',
    legal: 'Is this legal advice?', runs: 'What does it run on?', why: 'Why now?', who: 'Who built this?' };

  let lines = null, manifest = {}, audio = null, muted = false;
  try { muted = localStorage.getItem('guide-muted') === '1'; } catch (e) {}
  const load = async () => {
    if (lines) return;
    try {
      [lines, manifest] = await Promise.all([fetch(up + 'guide/lines.json').then(r => r.json()),
        fetch(up + 'guide/manifest.json').then(r => r.json())]);
    } catch (e) { lines = {}; }
  };
  const voice = () => {
    const vs = speechSynthesis.getVoices().filter(v => /^en[-_]/i.test(v.lang));
    const rank = v => (/natural|neural/i.test(v.name) ? 4 : 0) + (/online/i.test(v.name) ? 2 : 0)
      + (/(ava|aria|jenny|sonia|libby|emma|samantha|google uk english female|google us english)/i.test(v.name) ? 3 : 0);
    return vs.sort((a, b) => rank(b) - rank(a))[0] || null;
  };
  const stop = () => {
    if (audio) { audio.pause(); audio = null; }
    if ('speechSynthesis' in window) speechSynthesis.cancel();
    orb.classList.remove('talking');
  };
  const synth = text => {
    if (!('speechSynthesis' in window)) return;
    const u = new SpeechSynthesisUtterance(text), v = voice();
    if (v) { u.voice = v; u.lang = v.lang; } else u.lang = 'en-GB';
    u.rate = 0.97; u.pitch = 0.95;
    u.onstart = () => orb.classList.add('talking'); u.onend = u.onerror = () => orb.classList.remove('talking');
    speechSynthesis.speak(u);
  };
  const say = (text, key) => {
    stop();
    if (muted) return;
    const file = key && manifest[key];
    if (!file) return synth(text);
    const a = new Audio(up + 'guide/voice/' + file);
    audio = a;
    a.onplay = () => orb.classList.add('talking');
    a.onended = a.onpause = () => orb.classList.remove('talking');
    a.play().catch(err => { if (audio === a && err?.name !== 'AbortError') synth(text); });
  };

  const liveAnswer = async () => {
    try {
      const d = await (await fetch(up + 'data/cases.json')).json();
      const use = d.rows.filter(r => r.st === 'Implemented' || r.st === 'Pilot');
      const hr = use.filter(r => r.s === 'high_risk' || r.s === 'prohibited').length;
      const tr = use.filter(r => r.s === 'transparency').length;
      const n = new Set(d.rows.map(r => r.c)).size;
      return `Right now the European Commission's catalogue lists ${use.length.toLocaleString('en-US')} AI systems in use or piloted ` +
        `by public bodies in ${n - 1} EU countries and EU institutions. On a first pass, ${hr} look high-risk under the AI Act, ` +
        `and ${tr} only need to tell people they are talking to an AI.`;
    } catch (e) { return 'I could not load the live numbers just now. The EU public sector page has them.'; }
  };

  // build the UI
  const wrap = document.createElement('div');
  wrap.className = 'guide';
  wrap.innerHTML = `
    <div class="g-panel" id="g-panel" role="dialog" aria-label="Veredicto guide" hidden>
      <div class="g-head"><b>Guide</b><span class="g-sub">Ask about this page, the case study or the live data</span>
        <button type="button" class="g-icon" data-mute aria-pressed="${muted}" aria-label="Mute the voice">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4z"/><path class="g-wave" d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13"/><path class="g-x" d="m16 9 6 6m0-6-6 6"/></svg></button>
        <button type="button" class="g-icon" data-close aria-label="Close the guide"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg></button></div>
      <div class="g-log" aria-live="polite"></div>
      <div class="g-chips"></div>
      <form class="g-form"><label class="sr" for="g-q">Ask a question</label>
        <input id="g-q" type="text" autocomplete="off" placeholder="Ask a question or describe an AI idea" maxlength="600">
        <button type="button" class="g-icon g-mic" data-mic aria-label="Ask by voice" hidden><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg></button>
        <button type="submit" class="g-send">Ask</button></form>
    </div>
    <button type="button" class="orb" aria-expanded="false" aria-controls="g-panel"><span class="orb-core" aria-hidden="true"></span><span class="orb-label">Guide</span></button>`;
  document.body.appendChild(wrap);
  const orb = wrap.querySelector('.orb'), panel = wrap.querySelector('.g-panel'), log = wrap.querySelector('.g-log');
  const chips = wrap.querySelector('.g-chips'), form = wrap.querySelector('.g-form'), q = wrap.querySelector('#g-q');

  const add = (who, text) => {
    const p = document.createElement('p');
    p.className = 'g-msg ' + who; p.textContent = text;
    log.appendChild(p); log.scrollTop = log.scrollHeight;
  };
  const answer = async key => {
    await load();
    const text = key === 'live' ? await liveAnswer() : (lines[key] || lines.fallback || '');
    add('bot', text); say(text, key === 'live' ? null : key);
  };
  // ---- idea check: the real screener, in the browser ----
  const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.27.2/full/';
  const PY_FILES = ['src/__init__.py', 'src/rules.py', 'src/screener/__init__.py', 'src/screener/law.py',
    'src/screener/readers.py', 'src/screener/pipeline.py', 'src/screener/redesign.py', 'src/screener/value.py',
    'src/screener/ask.py'];
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const TIERS = { prohibited: 'Prohibited', high_risk: 'High-risk', transparency: 'Transparency', minimal: 'Minimal' };
  let py = null, mode = 'ask', idea = null;
  const engine = () => py || (py = (async () => {
    await new Promise((res, rej) => {
      const s = document.createElement('script'); s.src = PYODIDE + 'pyodide.js'; s.onload = res; s.onerror = rej;
      document.head.appendChild(s);
    });
    const pyo = await window.loadPyodide({ indexURL: PYODIDE });
    pyo.FS.mkdirTree('/app/src/screener');
    const texts = await Promise.all(PY_FILES.map(f => fetch(up + 'py/' + f).then(r => { if (!r.ok) throw new Error(f); return r.text(); })));
    PY_FILES.forEach((f, i) => pyo.FS.writeFile('/app/' + f, texts[i]));
    pyo.runPython("import sys; sys.path.insert(0, '/app')");
    return pyo;
  })().catch(err => { py = null; throw err; }));
  const runCheck = async () => {
    const pyo = await engine();
    pyo.globals.set('_args', JSON.stringify(idea));
    return JSON.parse(pyo.runPython('import json\nfrom src.screener.ask import check\n_a = json.loads(_args)\n'
      + "json.dumps(check(_a['text'], _a['answers'], _a['asked']))"));
  };
  const day = iso => new Date(iso + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  const factLabel = x => x.fact === 'annex_iii' ? `Annex III ${x.value}${x.area ? ': ' + x.area.split(':')[0] : ''}`
    : x.fact === 'prohibited' ? 'Art 5: ' + x.value.replace(/_/g, ' ') : x.fact === 'role' ? 'you are the ' + x.value : x.fact.replace(/_/g, ' ');
  const card = (r, again) => {
    const el = document.createElement('div');
    el.className = 'g-card';
    const quotes = {};
    r.quotes.forEach(x => { (quotes[x.quote] = quotes[x.quote] || []).push(factLabel(x)); });
    el.innerHTML = `${again ? '<p class="g-label">Updated with your answer</p>' : ''}
      <span class="stamp ${esc(r.tier)}">${TIERS[r.tier] || esc(r.tier)}</span>
      <p class="g-verdict">${esc(r.verdict)}.</p>
      <p class="g-label">How I got there</p><ol class="g-steps">${r.steps.map(s => `<li>${esc(s)}</li>`).join('')}</ol>
      ${Object.keys(quotes).length ? `<p class="g-label">Your words that decided it</p><ul class="g-quotes">${Object.entries(quotes).map(([qt, fs]) =>
        `<li><mark>${esc(qt)}</mark><span>${esc([...new Set(fs)].join(' · '))}</span></li>`).join('')}</ul>` : ''}
      ${r.obligations.length ? `<p class="g-label">What you would have to do</p><ul class="g-obl">${r.obligations.map(o =>
        `<li><b>${esc(o.article)}</b> ${esc(o.duty)} <span>${o.in_force ? 'applies now' : 'from ' + day(o.from)}</span></li>`).join('')}
        ${r.more_obligations ? `<li class="g-more">and ${r.more_obligations} more</li>` : ''}</ul>` : ''}
      ${r.redesign.length ? `<p class="g-label">What would make it ${r.redesign[0].to === 'minimal' ? 'allowed with no AI Act duties' : 'lighter'}</p>
        <ul class="g-fix">${r.redesign.map(x => `<li><span class="stamp ${esc(x.to)}">${TIERS[x.to]}</span>
        <b>${esc(x.change)}</b><span>${esc(x.why)}</span></li>`).join('')}</ul>` : ''}
      ${r.stake ? `<p class="g-label">What is at stake</p><div class="g-stake">
        ${r.stake.fine ? `<p><b>Fine ceiling.</b> ${esc(r.stake.fine.text)}</p>` : ''}
        ${r.stake.costs.map(c => `<p>${esc(c)}</p>`).join('')}
        ${r.tier === 'high_risk' ? `<p class="g-src">Costs: ${esc(r.stake.source)}. Estimates for the 2021 draft, an order of magnitude.</p>` : ''}</div>` : ''}
      ${r.review.length ? `<p class="g-flag">A person should check: ${esc(r.review.join('; '))}.</p>` : ''}
      ${r.questions.map(qq => `<div class="g-ask"><p>${esc(qq.text)}</p><div>${qq.options.map(o =>
        `<button type="button" data-q="${esc(qq.id)}" data-add="${esc(o.add)}">${esc(o.label)}</button>`).join('')}</div></div>`).join('')}
      <p class="g-fine">First pass: the free keyword reader plus the law in code, the same engine as the rest of the site. Not legal advice.</p>`;
    log.appendChild(el);
    log.scrollTop = el.offsetTop - 8;   // show the verdict first, not the end of the card
  };
  const checkIdea = async again => {
    const wait = document.createElement('p');
    wait.className = 'g-msg bot g-wait';
    wait.textContent = py ? 'Checking...' : 'Loading the rules engine. The first check downloads about 10 MB, then it is quick.';
    log.appendChild(wait); log.scrollTop = log.scrollHeight;
    try {
      const r = await runCheck();
      wait.remove(); card(r, again);
      const fix = r.redesign[0] ? ` One way to change that: ${r.redesign[0].change}` : '';
      const next = fix || (r.questions[0] ? ' ' + r.questions[0].text : '');
      say(`${TIERS[r.tier]}. ${r.verdict}.${next}`);
    } catch (err) {
      wait.textContent = 'I could not load the rules engine just now. Check the connection, or open the proposal intake page to see the same checks.';
    }
  };
  const looksLikeIdea = text => text.split(/\s+/).length >= 6 && !/\?\s*$/.test(text)
    && !/^(what|how|why|who|is|are|can|could|does|do|where|when|explain|tell|show)\b/i.test(text);
  const startIdea = async () => {
    mode = 'idea';
    await load();
    add('bot', lines.idea); say(lines.idea, 'idea');
    engine().catch(() => {});   // start the download while they type
    q.placeholder = 'For example: rank job applicants from their CVs';
    q.focus({ preventScroll: true });
  };
  log.addEventListener('click', e => {
    const b = e.target.closest('.g-ask button'); if (!b || !idea) return;
    b.closest('.g-card').querySelectorAll('.g-ask button').forEach(x => { x.disabled = true; });
    b.classList.add('picked');
    idea.answers.push(b.dataset.add); idea.asked.push(b.dataset.q);
    add('you', b.textContent); checkIdea(true);
  });

  const route = text => {
    const t = text.toLowerCase();
    if (/this page|explain|here|what am i/.test(t)) return here;
    const hit = ASK.find(([, re]) => re.test(t));
    return hit ? hit[0] : 'fallback';
  };
  const setChips = () => {
    chips.innerHTML = [['idea', 'Check an idea'], ['here', 'Explain this page'], ...(CHIPS[here] || CHIPS.intro).map(k => [k, LABEL[k]]), ['why', LABEL.why]]
      .map(([k, l]) => `<button type="button" data-k="${k}">${l}</button>`).join('');
  };
  const open = async () => {
    panel.hidden = false; orb.setAttribute('aria-expanded', 'true'); wrap.classList.add('open');
    if (!log.childElementCount) { setChips(); await answer(here); }
    q.focus({ preventScroll: true });
  };
  const close = () => { stop(); panel.hidden = true; orb.setAttribute('aria-expanded', 'false'); wrap.classList.remove('open'); orb.focus(); };
  orb.addEventListener('click', () => (panel.hidden ? open() : close()));
  wrap.querySelector('[data-close]').addEventListener('click', close);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !panel.hidden) close(); });
  chips.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    add('you', b.textContent);
    if (b.dataset.k === 'idea') return startIdea();
    mode = 'ask'; answer(b.dataset.k === 'here' ? here : b.dataset.k);
  });
  form.addEventListener('submit', e => {
    e.preventDefault();
    const text = q.value.trim(); if (!text) return;
    q.value = ''; add('you', text);
    if (mode === 'idea' || looksLikeIdea(text)) {
      mode = 'ask'; q.placeholder = 'Ask a question or describe an AI idea';
      idea = { text: text.replace(/^(check|screen)( my idea)?:?\s*/i, ''), answers: [], asked: [] };
      checkIdea(false);
    } else answer(route(text));
  });
  document.addEventListener('click', async e => {
    if (!e.target.closest('[data-guide="idea"]')) return;
    if (panel.hidden) await open();
    add('you', 'Check an idea'); startIdea();
  });
  const mute = wrap.querySelector('[data-mute]');
  mute.addEventListener('click', () => {
    muted = !muted; mute.setAttribute('aria-pressed', String(muted)); if (muted) stop();
    try { localStorage.setItem('guide-muted', muted ? '1' : '0'); } catch (e) {}
  });

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SR) {
    const mic = wrap.querySelector('[data-mic]');
    mic.hidden = false;
    mic.addEventListener('click', () => {
      stop();
      const r = new SR(); r.lang = 'en-US'; r.interimResults = false;
      mic.classList.add('on');
      r.onresult = ev => { q.value = ev.results[0][0].transcript; form.requestSubmit(); };
      r.onend = r.onerror = () => mic.classList.remove('on');
      try { r.start(); } catch (e) { mic.classList.remove('on'); }
    });
  }
})();
