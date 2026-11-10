// Numbers that count up once, and a small voice guide. Pre-recorded lines play as mp3
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
  const PAGE_LINE = { 'index.html': 'intro', 'proposals.html': 'intake', 'cases.html': 'eu', 'stress.html': 'stress',
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
    intake: ['how', 'highrisk', 'case'], documents: ['case', 'fairness', 'obligations'] };
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
        <input id="g-q" type="text" autocomplete="off" placeholder="Ask a question" maxlength="200">
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
  const route = text => {
    const t = text.toLowerCase();
    if (/this page|explain|here|what am i/.test(t)) return here;
    const hit = ASK.find(([, re]) => re.test(t));
    return hit ? hit[0] : 'fallback';
  };
  const setChips = () => {
    chips.innerHTML = [['here', 'Explain this page'], ...(CHIPS[here] || CHIPS.intro).map(k => [k, LABEL[k]]), ['why', LABEL.why]]
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
    add('you', b.textContent); answer(b.dataset.k === 'here' ? here : b.dataset.k);
  });
  form.addEventListener('submit', e => {
    e.preventDefault();
    const text = q.value.trim(); if (!text) return;
    q.value = ''; add('you', text); answer(route(text));
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
      r.onresult = ev => { const text = ev.results[0][0].transcript; add('you', text); answer(route(text)); };
      r.onend = r.onerror = () => mic.classList.remove('on');
      try { r.start(); } catch (e) { mic.classList.remove('on'); }
    });
  }
})();
