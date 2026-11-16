// The hall: one AI idea walks past six desks and leaves with a verdict.
// The people are a picture of the screening steps. The answers come from the real engine.
import * as THREE from 'three';
import { GOLD, TIER, bar, check, clamp, disc, engineStarted, knock, mat, plastic, smooth, spring, squircle, thick, waveMaterial } from './kit3d.js';

const $ = (s) => document.querySelector(s);
const DATA = JSON.parse($('#hall-data').textContent);
const calm = !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const EMBED = new URLSearchParams(location.search).has('embed');   // playing by itself inside the home page
if (EMBED) document.body.classList.add('embed');
let paused = false, example = 0;
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const short = (s, n) => (s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s);
const DESKS = [
  { name: 'Reader', does: 'in the software, a model reads', coat: '#3b5bdb', skin: '#e8b996', hair: '#3a2a20' },
  { name: 'Checker', does: 'in the software, code', coat: '#0f766e', skin: '#c68e6a', hair: '#15110f' },
  { name: 'Law clerk', does: 'in the software, the Act written as code', coat: '#1c2d6b', skin: '#f0cfb4', hair: '#b9b4ad' },
  { name: 'Challenger', does: 'in the software, a second model', coat: '#7c3aed', skin: '#8d5a3c', hair: '#0e0c0b' },
  { name: 'Writer', does: 'in the software, a model checked by code', coat: '#9a3412', skin: '#e3ae8a', hair: '#6b3a1e' },
  { name: 'Reviewer', does: 'in the software too, a real person', coat: '#b8860b', skin: '#d9a47e', hair: '#2b2018' },
];
const N = DESKS.length, GAP = 7, START_X = -5, END_X = N * GAP - 0.4, ARCH_X = END_X + 1.4;
const WALK = 1.25, DESK = 3.3, FINAL = 1.4, STAMP = 2.0, FLIP = 0.45, LAND = 0.3;   // the verdict tile starts turning FLIP s after arrival and clicks home LAND s later
const T_FINAL = N * (WALK + DESK) + FINAL, TOTAL = T_FINAL + STAMP;
const stopX = (i) => i * GAP, SIDE = 1.1;          // the visitor stands a step to the left, so the clerk stays in view
const deskProg = (i, t) => clamp((t - (i * (WALK + DESK) + WALK)) / DESK);
const OPINION = 0.62;                                   // how far into a desk's time its person gives an opinion
const eventAt = (i) => (i < N ? i * (WALK + DESK) + WALK + OPINION * DESK : T_FINAL + FLIP + LAND);
// ------------------------------------------------------------ what each desk says ------ //
const factLabel = (x) => (x.fact === 'annex_iii' ? `Annex III ${x.value}${x.area ? ': ' + x.area.split(':')[0] : ''}`
  : x.fact === 'prohibited' ? 'Art 5: ' + x.value.replace(/_/g, ' ') : x.fact === 'role' ? 'you are the ' + x.value : x.fact.replace(/_/g, ' '));
function speeches(r) {
  const n = r.quotes.length, quotes = [...new Set(r.quotes.map((q) => q.quote))];
  const basis = r.steps.slice(1, -1);
  const st = DATA.stress;
  return [
    { op: n ? 'ok' : 'none',
      line: n ? `I read your idea and found ${n} fact${n > 1 ? 's' : ''} the Act cares about. The clearest one: “${short(quotes[0], 80)}”`
        : 'I read your idea and found nothing in the wording that the AI Act singles out.',
      more: r.quotes.map((q) => `${factLabel(q)}: “${q.quote}”`) },
    { op: 'ok',
      line: n ? `I checked every fact against your own words. All ${n} point at a sentence you wrote, so all ${n} go on to the law.`
        : 'No facts reached me, so there is nothing to check. I pass the idea on as written.',
      more: ['A fact with no real quote never reaches the law. That is the guard against a model making things up.'] },
    { op: r.tier,
      line: 'I apply the Act as it is written, so the same idea always gets the same answer. ' + (basis[0] || 'No banned practice, no high-risk area and no transparency duty fits.'),
      more: basis.slice(1).concat(r.articles.length ? ['Articles used: ' + r.articles.join(', ')] : []) },
    { op: 'none',
      line: 'My job is to look for what the reader missed. On this page the free keyword reader works alone, so I have no second opinion to add.',
      more: [st ? `In the stress test the keyword reader gets ${st.plain}% of plainly worded ideas right, but only ${st.disguised}% of disguised ones. That gap is why a second reader exists.`
        : 'With a model reader, I re-read every proposal and the law is applied again if I find something.'] },
    { op: 'ok', line: 'My memo: ' + short(r.memo || r.verdict, 170),
      more: ['I may only cite articles the law clerk used. If I cite anything else, my memo is thrown away and a plain template is used.'] },
    { op: r.review.length ? 'flag' : 'ok',
      line: r.review.length ? `I want to look at this one myself: ${short(r.review[0], 120)}.`
        : 'Nothing here is uncertain, so it goes through without waiting for me.',
      more: r.review.slice(1).map((x) => 'Also: ' + x) },
  ];
}

// ---------------------------------------------------------------------- the page ------- //
const ui = {
  intro: $('#h-intro'), walk: $('#h-walk'), verdict: $('#h-verdict'), form: $('#h-form'), text: $('#h-idea'),
  go: $('#h-go'), note: $('#h-note'), steps: [...document.querySelectorAll('.h-step')], say: $('#h-say'),
  who: $('#h-who'), line: $('#h-line'), more: $('#h-more'), skip: $('#h-skip'), out: $('#h-out'),
};
let idea = null, run = null, lines = [], focus = null, scene3d = null;

function say(i) {
  const d = DESKS[i], s = lines[i];
  ui.who.innerHTML = `<b>${esc(d.name)}</b><span>${esc(d.does)}</span>`;
  ui.line.textContent = s.line;
  ui.more.innerHTML = run?.done && s.more.length ? s.more.map((m) => `<li>${esc(m)}</li>`).join('') : '';
  ui.say.hidden = false;
  ui.steps.forEach((b, k) => b.classList.toggle('on', k === i));
}
function mark(t) {
  ui.steps.forEach((b, k) => {
    if (k >= N) { b.classList.toggle('done', t >= T_FINAL); return; }
    const p = deskProg(k, t);
    b.classList.toggle('done', p > OPINION);
    b.dataset.op = p > OPINION ? lines[k].op : '';
  });
}
const day = (iso) => new Date(iso + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
function showVerdict(r) {
  const fix = r.redesign[0];
  ui.out.innerHTML = `<span class="h-stamp ${esc(r.tier)}">${TIER[r.tier].name}</span>
    <h2>${esc(r.verdict)}.</h2>
    ${r.articles.length ? `<p class="h-arts">${r.articles.slice(0, 6).map((a) => `<span>${esc(a)}</span>`).join('')}</p>` : ''}
    ${r.obligations.length ? `<p class="h-label">What you would have to do</p><ul class="h-obl">${r.obligations.slice(0, 3).map((o) =>
      `<li><b>${esc(o.article)}</b> ${esc(o.duty)} <i>${o.in_force ? 'applies now' : 'from ' + day(o.from)}</i></li>`).join('')}
      ${r.obligations.length + r.more_obligations > 3 ? `<li class="h-dim">and ${r.obligations.length + r.more_obligations - 3} more</li>` : ''}</ul>` : ''}
    ${fix ? `<p class="h-label">What would make it lighter</p><p class="h-fix"><b>${esc(fix.change)}</b> ${esc(fix.why)}</p>` : ''}
    ${r.stake?.fine ? `<p class="h-label">What is at stake</p><p class="h-fix">${esc(r.stake.fine.text)}</p>` : ''}
    ${r.questions.map((q) => `<div class="h-ask"><p>${esc(q.text)}</p><div>${q.options.map((o) =>
      `<button type="button" data-q="${esc(q.id)}" data-add="${esc(o.add)}">${esc(o.label)}</button>`).join('')}</div></div>`).join('')}
    <p class="h-hint">Click a desk, here or in the hall, to hear that person's opinion again.</p>
    <p class="h-actions"><button type="button" class="h-btn" id="h-again">Try another idea</button><a class="h-btn ghost" href="proposals.html">Open the full app</a></p>`;
  ui.verdict.hidden = false;
  ui.verdict.scrollTop = 0;
  ui.skip.hidden = true;
  ui.say.hidden = true;
  ui.steps.forEach((b) => { b.disabled = false; b.classList.remove('on'); });
  ui.steps[N].classList.add('on');
}
function start(r, speed = 1) {
  lines = speeches(r);
  focus = null;
  run = { r, t: calm || !scene3d ? TOTAL : 0, speed, done: false, said: -1 };
  ui.intro.hidden = true; ui.verdict.hidden = true; ui.walk.hidden = false; ui.say.hidden = true; ui.skip.hidden = false;
  ui.steps.forEach((b) => { b.disabled = true; b.classList.remove('on', 'done'); b.dataset.op = ''; });
  scene3d?.prepare(r, lines);
  if (!scene3d) tick(0);
}
// the clock: the 3D scene calls this every frame; with no 3D it is called once
function tick(dt) {
  if (!run) return null;
  if (!run.done) {
    run.t = Math.min(TOTAL, run.t + dt * run.speed);
    for (let i = 0; i < N; i++) if (deskProg(i, run.t) > 0 && deskProg(i, run.t) < 1 && run.said !== i) { run.said = i; say(i); }
    mark(run.t);
    if (run.t >= TOTAL) { run.done = true; if (EMBED) embedDone(run.r); else showVerdict(run.r); }
  }
  return run;
}
// inside the home page: say the verdict, wait, then play the next example
function embedDone(r) {
  ui.who.innerHTML = `<b>Verdict</b><span>${esc(TIER[r.tier].name)}</span>`;
  ui.line.textContent = r.verdict + '.';
  ui.more.innerHTML = ''; ui.say.hidden = false; ui.skip.hidden = true;
  ui.steps.forEach((b, k) => b.classList.toggle('on', k === N));
  if (!calm) setTimeout(playNext, 3600);
}
function playNext() { start(DATA.examples[example % DATA.examples.length].result); ui.skip.hidden = true; example += 1; }

async function submit(text, preset) {
  idea = { text, answers: [], asked: [] };
  if (preset) return start(preset);
  await ask();
}
async function ask(speed = 1) {
  ui.go.disabled = true;
  ui.note.textContent = engineStarted() ? 'Checking…' : 'Loading the rules engine. The first check downloads about 10 MB, then it is quick.';
  try { start(await check(idea), speed); ui.note.textContent = ''; } catch {
    ui.note.textContent = 'The rules engine could not load. Check your connection, or pick one of the examples.';
  }
  ui.go.disabled = false;
}

ui.form.addEventListener('submit', (ev) => { ev.preventDefault(); const t = ui.text.value.trim(); if (t.length > 8) submit(t); else ui.note.textContent = 'Describe the idea in a sentence or two.'; });
document.querySelectorAll('.h-ex button').forEach((b, i) => b.addEventListener('click', () => { ui.text.value = DATA.examples[i].text; submit(DATA.examples[i].text, DATA.examples[i].result); }));
ui.skip.addEventListener('click', () => { if (run && !run.done) run.t = Math.max(run.t, T_FINAL); });
ui.steps.forEach((b, i) => b.addEventListener('click', () => pick(i)));
function pick(i) {
  if (!run?.done) return;
  focus = i < N ? i : null;
  ui.verdict.hidden = focus !== null;
  if (focus === null) { ui.say.hidden = true; ui.steps.forEach((b, k) => b.classList.toggle('on', k === N)); } else say(i);
}
ui.out.addEventListener('click', (ev) => {
  const b = ev.target.closest('button');
  if (!b) return;
  if (b.id === 'h-again') { run = null; focus = null; ui.walk.hidden = true; ui.verdict.hidden = true; ui.intro.hidden = false; scene3d?.prepare(null); ui.text.focus(); return; }
  if (b.dataset.add) { idea.answers.push(b.dataset.add); idea.asked.push(b.dataset.q); ui.out.querySelectorAll('.h-ask button').forEach((x) => { x.disabled = true; }); ask(2.2); }
});

// ----------------------------------------------------------------------- the hall ------ //
function canvasTex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  return t;
}
function person(p, walker) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.3, 0.62, 6, 16), plastic(p.coat)); body.position.y = 1.22; g.add(body);
  const head = new THREE.Group(); head.position.y = 1.98; g.add(head);
  head.add(new THREE.Mesh(new THREE.SphereGeometry(0.23, 24, 18), mat(p.skin)));
  const hair = new THREE.Mesh(new THREE.SphereGeometry(0.248, 24, 18, 0, Math.PI * 2, 0, Math.PI * 0.5), plastic(p.hair, { roughness: 0.6 })); hair.rotation.x = -0.38; head.add(hair);
  for (const x of [-0.085, 0.085]) { const eye = new THREE.Mesh(new THREE.SphereGeometry(0.027, 10, 8), mat('#14110f', { roughness: 0.3 })); eye.position.set(x, 0.02, 0.212); head.add(eye); }
  const limb = (x, y, len, r, color) => {
    const pivot = new THREE.Group(); pivot.position.set(x, y, 0);
    const m = new THREE.Mesh(new THREE.CapsuleGeometry(r, len, 4, 10), plastic(color)); m.position.y = -len / 2 - r * 0.4; pivot.add(m);
    g.add(pivot); return pivot;
  };
  const armL = limb(-0.39, 1.62, 0.5, 0.085, p.coat), armR = limb(0.39, 1.62, 0.5, 0.085, p.coat);
  armL.rotation.z = -0.12; armR.rotation.z = 0.12;
  let legL = null, legR = null;
  if (walker) { legL = limb(-0.14, 0.86, 0.6, 0.105, '#1b2238'); legR = limb(0.14, 0.86, 0.6, 0.105, '#1b2238'); }
  return { g, head, armL, armR, legL, legR };
}

function createHall(canvas) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.1;
  const phone = window.innerWidth < 700;
  renderer.shadowMap.enabled = !phone; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#050a1f');
  scene.fog = new THREE.Fog('#050a1f', 22, 70);
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 120);

  // a studio to reflect: three softboxes in a dim room, so the plastic and the gold have something to shine with
  const studio = new THREE.Scene();
  studio.add(new THREE.Mesh(new THREE.SphereGeometry(50, 32, 16), new THREE.MeshBasicMaterial({ color: '#232a44', side: THREE.BackSide })));
  for (const [x, y, z, bw, bh, power] of [[5, 24, 9, 28, 14, 3.4], [25, 8, 13, 9, 18, 2.4], [-23, 6, 11, 6, 20, 2]]) {
    const box = new THREE.Mesh(new THREE.PlaneGeometry(bw, bh), new THREE.MeshBasicMaterial({ color: new THREE.Color(power, power, power), side: THREE.DoubleSide }));
    box.position.set(x, y, z); box.lookAt(0, 0, 0); studio.add(box);
  }
  const pm = new THREE.PMREMGenerator(renderer);
  scene.environment = pm.fromScene(studio, 0.03).texture; scene.environmentIntensity = 0.5; pm.dispose();
  scene.add(new THREE.HemisphereLight('#c3ceff', '#141c44', 1.1));
  const sun = new THREE.DirectionalLight('#fff1d6', 1.7); sun.position.set(6, 12, 10); scene.add(sun, sun.target);
  sun.castShadow = !phone; sun.shadow.mapSize.setScalar(2048); sun.shadow.bias = -0.0005; sun.shadow.normalBias = 0.03;
  Object.assign(sun.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, near: 1, far: 60 });
  const wash = new THREE.PointLight('#ffcc00', 0, 30, 1.6); wash.position.set(ARCH_X, 4.5, 1.5); scene.add(wash);

  // floor, back wall, columns
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(160, 40), mat('#101d52', { roughness: 0.75 }));
  floor.rotation.x = -Math.PI / 2; floor.position.set(18, 0, 0); scene.add(floor);
  const lane = new THREE.Mesh(new THREE.PlaneGeometry(N * GAP + 12, 1.5), mat('#1d3484', { roughness: 0.5 }));
  lane.rotation.x = -Math.PI / 2; lane.position.set((N * GAP) / 2 - 3, 0.005, 0.9); scene.add(lane);
  // the back wall stays blue; each opinion sends a ring of its colour across and leaves a glow behind whoever gave it
  const WALL = new THREE.Color('#14276a');
  const { material: wallMat, wave } = waveMaterial(WALL);
  wave.uSpread.value = 4.5;
  const wall = new THREE.Mesh(new THREE.PlaneGeometry(160, 16), wallMat);
  wall.position.set(18, 8, -7.2); scene.add(wall);
  const colGeo = new THREE.CylinderGeometry(0.42, 0.48, 11, 20), colMat = mat('#2a3f8f', { roughness: 0.6 });
  const capGeo = new THREE.BoxGeometry(1.3, 0.3, 1.3);
  for (let i = -2; i <= N + 1; i++) {
    for (const z of [-6.2, 5.2]) {
      if (z > 0 && (i < 0 || i > N)) continue;
      const c = new THREE.Mesh(colGeo, colMat); c.position.set(i * GAP - GAP / 2, 5.5, z); scene.add(c);
      const base = new THREE.Mesh(capGeo, colMat); base.position.set(i * GAP - GAP / 2, 0.15, z); scene.add(base);
    }
  }
  const beam = new THREE.Mesh(new THREE.BoxGeometry(160, 0.5, 1.2), colMat); beam.position.set(18, 10.6, -6.2); scene.add(beam);

  // six desks, six people
  const desks = DESKS.map((d, i) => {
    const g = new THREE.Group(); g.position.set(stopX(i), 0, -2.6); scene.add(g);
    const base = new THREE.Mesh(new THREE.BoxGeometry(2.7, 0.96, 1.05), plastic('#22346f')); base.position.y = 0.48; g.add(base);
    const top = new THREE.Mesh(new THREE.BoxGeometry(2.9, 0.07, 1.2), GOLD()); top.position.y = 0.995; g.add(top);
    const who = person(d); who.g.position.set(0, 0, -0.95); g.add(who.g);
    const sign = new THREE.Mesh(new THREE.PlaneGeometry(2.5, 0.62), new THREE.MeshBasicMaterial({ transparent: true,
      map: canvasTex(640, 160, (c, w, h) => {
        c.fillStyle = 'rgba(8,16,48,0.92)'; c.beginPath(); c.roundRect(4, 4, w - 8, h - 8, 26); c.fill();
        c.strokeStyle = '#ffcc00'; c.lineWidth = 4; c.stroke();
        c.fillStyle = '#ffffff'; c.font = '600 74px "Space Grotesk", sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle';
        c.fillText(d.name.toUpperCase(), w / 2, h / 2 + 4);
      }) }));
    sign.position.set(0, 3.5, -1.2); g.add(sign);
    const lamp = new THREE.PointLight('#ffe2a8', 0, 9, 1.4); lamp.position.set(0, 3.3, 0.3); g.add(lamp);
    const badge = new THREE.Sprite(new THREE.SpriteMaterial({ transparent: true, depthTest: false })); badge.position.set(1.05, 2.75, -0.9); badge.scale.setScalar(0); g.add(badge);
    const hit = new THREE.Mesh(new THREE.BoxGeometry(3.2, 3.8, 2.6), new THREE.MeshBasicMaterial({ visible: false })); hit.position.set(0, 1.9, -0.4); hit.userData.i = i; g.add(hit);
    return { g, who, lamp, badge, hit, sign };
  });
  // the arch where the verdict is given: a plinth for the folder and one big tile that turns over to show the answer
  const arch = new THREE.Group(); arch.position.set(ARCH_X, 0, -2.6); scene.add(arch);
  for (const x of [-1.75, 1.75]) { const c = new THREE.Mesh(new THREE.BoxGeometry(0.5, 5.4, 0.5), GOLD()); c.position.set(x, 2.7, 0); arch.add(c); }
  const lintel = new THREE.Mesh(new THREE.BoxGeometry(4.4, 0.6, 0.6), GOLD()); lintel.position.y = 5.5; arch.add(lintel);
  const plinth = new THREE.Group(); plinth.position.set(ARCH_X, 0, -1.3); scene.add(plinth);
  const pBase = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.96, 1.2), plastic('#22346f')); pBase.position.y = 0.48; plinth.add(pBase);
  const pTop = new THREE.Mesh(new THREE.BoxGeometry(1.35, 0.07, 1.35), GOLD()); pTop.position.y = 0.995; plinth.add(pTop);
  const TILE_R = 1.28, TILE_T = 0.6, NAVY = new THREE.Color('#1c2d6b');
  const tile = new THREE.Group(); tile.position.set(ARCH_X, 3.2, -2.5); scene.add(tile);
  const tileMat = plastic(NAVY);
  tile.add(new THREE.Mesh(thick(squircle(TILE_R), TILE_T, 0.16), tileMat));
  tile.add(new THREE.Mesh(thick(squircle(TILE_R + 0.02), 0.08, 0.03), GOLD()));
  const white = new THREE.MeshPhysicalMaterial({ color: '#ffffff', roughness: 0.6, sheen: 0.4 });
  const symbol = (parts, back) => {
    const g = new THREE.Group(); g.position.z = (back ? -1 : 1) * TILE_T / 2; if (back) g.rotation.y = Math.PI;
    parts.forEach(([shape, x, y, rot = 0], i) => { const m = new THREE.Mesh(thick(shape, 0.2, 0.06), white); m.position.set(x, y, 0.08 + i * 0.012); m.rotation.z = rot; g.add(m); });
    tile.add(g); return g;
  };
  const waiting = symbol([[disc(0.15), -0.5, 0], [disc(0.15), 0, 0], [disc(0.15), 0.5, 0]]);
  const faces = {
    prohibited: symbol([[bar(1.7, 0.34), 0, 0, Math.PI / 4], [bar(1.7, 0.34), 0, 0, -Math.PI / 4]], true),          // a cross
    high_risk: symbol([[bar(1.05, 0.36), 0, 0.3, Math.PI / 2], [disc(0.2), 0, -0.62]], true),                        // !
    transparency: symbol([[disc(0.2), 0, 0.62], [bar(1.05, 0.36), 0, -0.3, Math.PI / 2]], true),                     // i: people must be told
    minimal: symbol([[bar(0.8, 0.32), -0.42, -0.25, -Math.PI / 4], [bar(1.45, 0.32), 0.22, 0.05, Math.PI / 4]], true),   // a tick
  };

  const badgeTex = {};
  const badgeFor = (op) => badgeTex[op] || (badgeTex[op] = canvasTex(128, 128, (c) => {
    const col = op === 'ok' ? '#7ddf9a' : op === 'none' ? '#9aa7b0' : op === 'flag' ? '#f5b14c' : TIER[op].color;
    c.fillStyle = col; c.beginPath(); c.arc(64, 64, 56, 0, 7); c.fill();
    c.strokeStyle = '#06102c'; c.lineWidth = 13; c.lineCap = 'round'; c.lineJoin = 'round'; c.beginPath();
    if (op === 'ok' || op === 'minimal') { c.moveTo(36, 66); c.lineTo(56, 86); c.lineTo(94, 44); }
    else if (op === 'none') { c.moveTo(40, 64); c.lineTo(88, 64); }
    else if (op === 'prohibited') { c.moveTo(42, 42); c.lineTo(86, 86); c.moveTo(86, 42); c.lineTo(42, 86); }
    else { c.moveTo(64, 34); c.lineTo(64, 70); c.moveTo(64, 92); c.lineTo(64, 93); }
    c.stroke();
  }));

  // the visitor and the folder
  const visitor = person({ coat: '#e8ecf4', skin: '#dba785', hair: '#2a1d16' }, true);
  visitor.g.position.set(START_X, 0, 0.9); scene.add(visitor.g);
  const folder = new THREE.Group(); scene.add(folder);
  folder.add(new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.05, 0.82), mat('#f4ecd6', { roughness: 0.9 })));
  const sheet = new THREE.Mesh(new THREE.PlaneGeometry(0.56, 0.76), new THREE.MeshBasicMaterial({
    map: canvasTex(280, 380, (c, w, h) => {
      c.fillStyle = '#fbf6e6'; c.fillRect(0, 0, w, h);
      c.fillStyle = '#0b1840'; c.font = '700 30px "Space Grotesk", sans-serif'; c.fillText('AI IDEA', 24, 50);
      c.fillStyle = '#c9c2ad'; for (let y = 124; y < 290; y += 26) c.fillRect(24, y, y % 52 ? w - 48 : w - 110, 8);
    }) }));
  sheet.rotation.x = -Math.PI / 2; sheet.position.y = 0.027; folder.add(sheet);
  const tabs = [...Array(5)].map((_, k) => {
    const t = new THREE.Mesh(new THREE.BoxGeometry(0.11, 0.03, 0.1), new THREE.MeshBasicMaterial({ color: '#ffcc00' }));
    t.position.set(0.34, 0.02, -0.27 + k * 0.135); folder.add(t); return t;
  });
  const band = new THREE.Mesh(new THREE.PlaneGeometry(0.56, 0.07), new THREE.MeshBasicMaterial({ color: '#fff' }));
  band.rotation.x = -Math.PI / 2; band.position.set(0, 0.029, -0.2); folder.add(band);
  const memo = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.012, 0.3), new THREE.MeshBasicMaterial({ color: '#ffffff' }));
  memo.position.set(-0.02, 0.036, 0.22); folder.add(memo);
  const flag = new THREE.Mesh(new THREE.BoxGeometry(0.11, 0.03, 0.16), new THREE.MeshBasicMaterial({ color: '#f5b14c' }));
  flag.position.set(-0.34, 0.02, -0.2); folder.add(flag);
  const stamp = new THREE.Mesh(new THREE.PlaneGeometry(0.52, 0.2), new THREE.MeshBasicMaterial({ transparent: true }));
  stamp.rotation.x = -Math.PI / 2; stamp.rotation.z = 0.16; stamp.position.set(0, 0.045, 0.02); folder.add(stamp);

  scene.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  [floor, lane, wall].forEach((m) => { m.castShadow = false; });
  desks.forEach((d) => { d.hit.castShadow = false; d.sign.castShadow = false; });
  let r = null, sp = [], nTabs = 0, last = 0, raf = 0, walkPhase = 0, w = 1, h = 1, shift = 0;
  const evCol = [...Array(N + 1)].map(() => WALL.clone()), tierCol = new THREE.Color('#ffffff');
  const camPos = new THREE.Vector3(17, 7, 30), camLook = new THREE.Vector3(17, 1.6, -2), look = camLook.clone();
  const v = new THREE.Vector3(), q = new THREE.Quaternion(), flat = new THREE.Quaternion();
  camera.position.copy(camPos);

  function prepare(result, said) {
    r = result; sp = said || [];
    nTabs = r ? Math.min(5, Math.max(r.quotes.length, 0)) : 0;
    if (r) {
      const col = TIER[r.tier].color;
      band.material.color.set(col); wash.color.set(col); tierCol.set(col);
      DESKS.forEach((d, i) => evCol[i].set(i === 2 ? col : d.coat));
      evCol[N].copy(tierCol);
      Object.entries(faces).forEach(([name, g]) => { g.userData.on = name === r.tier; });
      stamp.material.map?.dispose();
      stamp.material.map = canvasTex(520, 200, (c, cw, ch) => {
        c.strokeStyle = col; c.fillStyle = col; c.lineWidth = 12; c.beginPath(); c.roundRect(10, 10, cw - 20, ch - 20, 22); c.stroke();
        c.font = '700 84px "Space Grotesk", sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle';
        c.fillText(TIER[r.tier].name.toUpperCase(), cw / 2, ch / 2 + 6, cw - 60);
      });
      stamp.material.needsUpdate = true;
      desks.forEach((d, i) => { d.badge.material.map = badgeFor(sp[i].op); d.badge.material.needsUpdate = true; });
    }
    walkPhase = 0;
  }

  function frame(now) {
    raf = requestAnimationFrame(frame);
    if (paused) { last = now; return; }
    const dt = Math.min(0.05, (now - last) / 1000 || 0); last = now;
    const k = (rate) => 1 - Math.exp(-dt * rate);
    const state = tick(dt);
    const t = state ? state.t : 0, done = !!state?.done;
    const portrait = w < h, wide = w >= 900;

    // where the visitor is
    let x = START_X, walking = false, at = -1, tt = t;
    const standX = (i) => stopX(i) - SIDE;
    if (state) {
      let from = START_X; at = N;
      for (let i = 0; i < N; i++) {
        if (tt < WALK) { x = from + (standX(i) - from) * smooth(tt / WALK); walking = true; at = -1; break; }
        tt -= WALK; x = standX(i);
        if (tt < DESK) { at = i; break; }
        tt -= DESK; from = standX(i);
      }
      if (at === N) { const p = clamp((t - N * (WALK + DESK)) / FINAL); x = standX(N - 1) + (END_X - standX(N - 1)) * smooth(p); walking = p < 1; }
    }
    visitor.g.position.x = x;
    walkPhase += walking ? dt * 9.5 : 0;
    const sw = walking ? Math.sin(walkPhase) * 0.6 : 0;
    visitor.legL.rotation.x += (sw - visitor.legL.rotation.x) * k(18);
    visitor.legR.rotation.x += (-sw - visitor.legR.rotation.x) * k(18);
    visitor.g.position.y = walking ? Math.abs(Math.sin(walkPhase)) * 0.05 : 0;
    const face = walking ? Math.PI / 2 : at >= 0 && at < N ? Math.PI - 0.45 : 0.5;
    visitor.g.rotation.y += (face - visitor.g.rotation.y) * k(7);
    const carry = walking ? -1.15 : -0.9;
    visitor.armL.rotation.x += (carry - visitor.armL.rotation.x) * k(8);
    visitor.armR.rotation.x += (carry - visitor.armR.rotation.x) * k(8);

    // the six people
    desks.forEach((d, i) => {
      const p = state ? deskProg(i, t) : 0, active = p > 0 && p < 1, op = sp[i]?.op;
      d.lamp.intensity += ((active || focus === i ? 38 : p >= 1 ? 14 : state ? 7 : 20) - d.lamp.intensity) * k(5);
      const reading = active ? smooth((p - 0.1) / 0.15) * (1 - smooth((p - 0.55) / 0.1)) : 0;
      const opin = active ? clamp((p - OPINION) / 0.3) : 0, nod = Math.sin(opin * Math.PI * 4) * (1 - opin);
      const no = op === 'prohibited' || op === 'flag';
      d.who.head.rotation.x += ((reading * 0.5 + (no ? 0 : nod * 0.32)) - d.who.head.rotation.x) * k(12);
      d.who.head.rotation.y += ((no ? nod * 0.5 : 0) - d.who.head.rotation.y) * k(12);
      const raise = (op === 'flag' || op === 'prohibited') && p > OPINION ? -2.7 : reading * -0.9;
      d.who.armR.rotation.x += (raise - d.who.armR.rotation.x) * k(7);
      d.who.armL.rotation.x += (reading * -0.9 - d.who.armL.rotation.x) * k(7);
      d.who.g.position.y = Math.sin(now / 900 + i * 1.7) * 0.012;
      d.badge.scale.setScalar(0.62 * spring((p - OPINION) * DESK, 3.2, 0.42));
      d.g.position.y = -0.05 * knock((p - 0.16) * DESK) * (p < 1 ? 1 : 0);          // the desk takes the folder landing on it
    });

    // the folder
    const p0 = state ? deskProg(0, t) : 0;
    tabs.forEach((tab, i) => { tab.visible = !!state && i < Math.round(nTabs * clamp((p0 - 0.25) / 0.4)); tab.material.color.set(state && deskProg(1, t) > 0.6 ? '#7ddf9a' : '#ffcc00'); });
    band.visible = !!state && deskProg(2, t) > 0.6;
    memo.visible = !!state && deskProg(4, t) > 0.6;
    flag.visible = !!state && deskProg(5, t) > 0.6 && sp[5]?.op === 'flag';
    const u = state ? t - T_FINAL : -1, sFlip = u - FLIP, landed = sFlip - LAND;
    stamp.visible = landed > 0;
    stamp.scale.setScalar(1 + 1.2 * (1 - smooth(landed / 0.2)));
    const onDesk = focus !== null ? focus : (at >= 0 && at < N && tt / DESK > 0.1 && tt / DESK < 0.88 ? at : -1);
    let rate = 7;
    if (onDesk >= 0) v.set(stopX(onDesk), 1.06, -2.15);
    else if (u > 0 && focus === null) v.set(ARCH_X, 1.06 - 0.04 * knock(landed), -1.3);
    else { v.set(0, 1.28, 0.42).applyAxisAngle(THREE.Object3D.DEFAULT_UP, visitor.g.rotation.y).add(visitor.g.position); rate = 16; }
    folder.position.lerp(v, k(rate));
    folder.quaternion.slerp(flat, k(rate));
    const big = u > 0 && focus === null ? 1.45 : 1;
    folder.scale.setScalar(folder.scale.x + (big - folder.scale.x) * k(5));
    wash.intensity += ((landed > 0 ? 18 : 0) - wash.intensity) * k(4);

    // the verdict tile: it leans back, turns over a little past the mark and clicks home in the colour of the answer
    const wind = sFlip < 0 ? smooth((sFlip + 0.3) / 0.3) : Math.max(0, 1 - sFlip / 0.1);
    const angle = Math.PI * spring(sFlip, 1.4, 0.6) - 0.25 * wind, kb = knock(landed);
    tile.rotation.set(0.06 + 0.03 * Math.sin(now / 1100) + 0.06 * kb, angle - 0.2 + 0.05 * Math.sin(now / 1400), 0.012 * Math.sin(now / 1250));
    tile.position.set(ARCH_X, 3.2 + 0.05 * Math.sin(now / 800), -2.5 - 0.3 * wind - 0.2 * kb);
    tileMat.color.copy(NAVY).lerp(tierCol, r ? smooth((angle - 1.2) / 0.7) : 0);
    waiting.visible = angle < Math.PI / 2;
    Object.values(faces).forEach((g) => { g.visible = !waiting.visible && !!g.userData.on; });

    // the wall: each opinion sends a ring of its colour across and leaves a glow behind whoever gave it
    let ev = -1;
    if (state) for (let i = 0; i <= N; i++) if (t >= eventAt(i)) ev = i;
    const since = ev >= 0 ? t - eventAt(ev) : -1;
    if (ev >= 0) wave.uTint.value.copy(evCol[ev]);
    wave.uCentre.value.set(ev < N ? stopX(Math.max(ev, 0)) : ARCH_X, 3, -7.2);
    wave.uRadius.value = ev >= 0 ? since * 26 : -99;
    wave.uHalo.value = ev >= 0 ? (ev === N ? 0.12 : 0.1) * smooth(since / 0.5) : 0;

    // the camera
    if (!state) {
      const s = Math.sin(now / 6000);
      if (portrait) { camPos.set(3 + s * 3, 4.2, 19); camLook.set(3 + s * 3, 1.8, -2); } else { camPos.set(14 + s * 1.6, 3.4, 12.5); camLook.set(14 + s * 1.6, 2.0, -2.5); }
    } else {
      const cx = focus !== null ? stopX(focus) : x + SIDE;
      camPos.set(cx + 0.2, portrait ? 3.4 : 2.9, portrait ? 14 : 9.6);
      camLook.set(cx, portrait ? 2.1 : 1.6, -1.8);
    }
    camera.position.lerp(camPos, k(state ? 3.2 : 1.5));
    look.lerp(camLook, k(state ? 3.2 : 1.5));
    camera.lookAt(look);
    sun.position.set(look.x + 7, 13, 11); sun.target.position.set(look.x, 0, -2);
    const panel = !ui.intro.hidden || !ui.verdict.hidden;
    shift += ((panel ? 1 : 0) - shift) * k(4);
    if (wide) camera.setViewOffset(w, h, -Math.round(shift * Math.min(250, w * 0.17)), 0, w, h);
    else camera.setViewOffset(w, h, 0, Math.round((panel ? shift * 0.22 : 0.1) * h), w, h);
    renderer.render(scene, camera);
  }

  const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
  canvas.addEventListener('click', (ev) => {
    if (!run?.done) return;
    ptr.set((ev.clientX / w) * 2 - 1, -(ev.clientY / h) * 2 + 1);
    ray.setFromCamera(ptr, camera);
    const hit = ray.intersectObjects(desks.map((d) => d.hit))[0];
    if (hit) pick(hit.object.userData.i);
  });
  const size = () => {
    w = window.innerWidth; h = window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.fov = w < h ? 52 : 36; camera.updateProjectionMatrix();
  };
  window.addEventListener('resize', size);
  document.addEventListener('visibilitychange', () => { cancelAnimationFrame(raf); if (!document.hidden) { last = performance.now(); raf = requestAnimationFrame(frame); } });
  size();
  raf = requestAnimationFrame(frame);
  return { prepare };
}

const start3d = () => {
  try { scene3d = createHall($('#hall-canvas')); document.body.classList.add('has-3d'); } catch { scene3d = null; }
  window.HALL_READY = true;
};
(document.fonts?.ready || Promise.resolve()).then(start3d, start3d).then(() => {
  if (EMBED) {
    addEventListener('message', (ev) => { if (ev.origin === location.origin && ev.data && 'hallVisible' in ev.data) paused = !ev.data.hallVisible; });
    parent.postMessage({ hallReady: true }, location.origin);
    playNext();
    return;
  }
  const sent = new URLSearchParams(location.search).get('idea')?.trim().slice(0, 600);
  if (!sent) return;
  ui.text.value = sent;
  submit(sent, DATA.examples.find((x) => x.text === sent)?.result);
});
