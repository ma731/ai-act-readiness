// The home page hero: one big tile in a studio. Type an AI idea and the tile turns over to its
// verdict while the studio takes the verdict's colour. Until then it plays four examples.
import * as THREE from 'three';
import { TIER, check, engineStarted, knock, makeTile, smooth, spring, studioEnv, waveMaterial } from './kit3d.js';

const $ = (s) => document.querySelector(s);
const DATA = JSON.parse($('#hero-data').textContent);
const calm = !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const ui = { hero: $('.shero'), canvas: $('#hero-canvas'), form: $('#hero-form'), idea: $('#hero-idea'), go: $('#hero-go'), out: $('#hero-out'), chips: [...document.querySelectorAll('.hero-ex button')] };
const WAITING = { color: '#3f7bff' }, STUDIO = '#0b2a7a';
let stage = null, auto = null, turn = 0;

// ---------------------------------------------------------------------- the words ------ //
function render(r, label, quote) {
  const why = r.steps.slice(1, -1)[0] || 'Nothing in the wording is singled out by the AI Act.';
  const n = r.obligations.length + r.more_obligations;
  ui.out.innerHTML = `<p class="ho-label">${esc(label)}</p>
    ${quote ? `<p class="ho-idea">“${esc(quote)}”</p>` : ''}
    <p class="ho-verdict"><span class="ho-stamp">${TIER[r.tier].name}</span><b>${esc(r.verdict)}.</b></p>
    <p class="ho-why">${esc(why)}${n ? ` <span>${n} obligation${n > 1 ? 's' : ''} follow.</span>` : ''}</p>
    <p class="ho-links"><a href="hall.html?idea=${encodeURIComponent(r.text)}">Watch six people decide it</a><a href="proposals.html">Open the app</a></p>`;
  ui.hero.dataset.tier = r.tier;
  stage?.turnTo(r.tier);
}
function example(i, label = 'Example') {
  const ex = DATA.examples[i];
  ui.chips.forEach((b, k) => b.setAttribute('aria-pressed', k === i));
  render(ex.result, `${label} · ${ex.label}`, ex.text);
}
const stop = () => { clearInterval(auto); auto = null; };
function play() {
  if (calm) return;
  auto = setInterval(() => { if (!document.hidden) { turn = (turn + 1) % DATA.examples.length; example(turn); } }, 4600);
}

ui.chips.forEach((b, i) => b.addEventListener('click', () => { stop(); turn = i; example(i, 'You picked'); }));
ui.idea.addEventListener('focus', stop);
ui.form.addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const text = ui.idea.value.trim();
  stop();
  if (text.length < 9) { ui.out.innerHTML = '<p class="ho-label">Describe the idea in a sentence, for example “a tool that ranks job applicants”.</p>'; return; }
  ui.chips.forEach((b) => b.setAttribute('aria-pressed', 'false'));
  ui.go.disabled = true;
  ui.out.innerHTML = `<p class="ho-label">${engineStarted() ? 'Checking…' : 'Loading the rules engine. The first check downloads about 10 MB, then it is quick.'}</p>`;
  delete ui.hero.dataset.tier;
  stage?.turnTo('waiting');
  try { render(await check({ text, answers: [], asked: [] }), 'Your idea'); } catch {
    ui.out.innerHTML = '<p class="ho-label">The rules engine could not load. Check your connection, or pick one of the examples.</p>';
  }
  ui.go.disabled = false;
});

// ---------------------------------------------------------------------- the studio ----- //
function createStage(canvas) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.toneMapping = THREE.NeutralToneMapping; renderer.toneMappingExposure = 1;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(26, 1, 1, 120);
  scene.environment = studioEnv(renderer, '#4a4f5c'); scene.environmentIntensity = 0.6;

  // a seamless backdrop: floor, a curved sweep and a wall in one piece
  const WALL = -2.6, FLOOR = -3.4, RAD = 2.4, pts = [[FLOOR, 30]];
  for (let i = 0; i <= 18; i++) { const a = (i / 18) * Math.PI / 2; pts.push([FLOOR + RAD - Math.cos(a) * RAD, WALL + RAD - Math.sin(a) * RAD]); }
  pts.push([FLOOR + RAD + 40, WALL]);
  const pos = [], idx = [];
  pts.forEach(([y, z], i) => { pos.push(-70, y, z, 70, y, z); if (i) { const a = (i - 1) * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); } });
  const sweep = new THREE.BufferGeometry();
  sweep.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); sweep.setIndex(idx); sweep.computeVertexNormals();
  const { material, wave } = waveMaterial(STUDIO, { side: THREE.DoubleSide });
  const backdrop = new THREE.Mesh(sweep, material); backdrop.receiveShadow = true; scene.add(backdrop);
  wave.uCentre.value.set(0.4, 0.2, WALL); wave.uSpread.value = 3.6;

  // one big soft key from the upper right, so the tile's shadow falls on the wall down to the left
  const key = new THREE.SpotLight('#fff8ee', 1500, 0, 0.8, 1, 2); key.position.set(8, 9, 12); key.target.position.set(1, -0.2, -1);
  key.castShadow = true; key.shadow.mapSize.setScalar(2048); key.shadow.radius = 10; key.shadow.blurSamples = 16; key.shadow.bias = -0.0004; key.shadow.normalBias = 0.03;
  scene.add(key, key.target);
  const bounce = new THREE.HemisphereLight('#ffffff', STUDIO, 0.9); scene.add(bounce);   // the studio's colour bounces up into the white parts

  const tile = makeTile(1.6, 0.76);
  tile.group.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  scene.add(tile.group);

  const col = (name) => new THREE.Color((TIER[name] || WAITING).color), studio = new THREE.Color(STUDIO);
  let n = 0, t0 = -10, last = 0, raf = 0, w = 1, h = 1, shown = 'waiting', seen = true;
  let bodyFrom = col('waiting'), bodyTo = bodyFrom.clone(), glowFrom = 0, glowTo = 0;   // the glow on the wall: none while waiting
  tile.body.color.copy(bodyTo);

  function turnTo(name) {
    if (name === shown) return;
    shown = name; n += 1; t0 = performance.now() / 1000;
    tile.show(n % 2, name);
    bodyFrom = tile.body.color.clone(); bodyTo = col(name);
    glowFrom = glowTo; glowTo = TIER[name] ? 0.14 : 0;
    if (calm) t0 = -10;
  }

  function frame(ms) {
    raf = requestAnimationFrame(frame);
    const now = ms / 1000; last = now;
    // the flip: lean back, turn over a little past the mark, click home
    const s = now - t0 - 0.16, wind = s < 0 ? smooth((s + 0.16) / 0.16) : Math.max(0, 1 - s / 0.1), go = n ? spring(s, 1.4, 0.6) : 1;
    const landed = s - 0.3, kb = knock(landed), float = calm ? 0 : 1;
    tile.group.rotation.set(0.1 + 0.03 * Math.sin(now * 0.9) * float + 0.05 * kb, (n - 1 + go) * Math.PI - 0.25 * wind - 0.24 + 0.04 * Math.sin(now * 0.7 + 1) * float, 0.015 * Math.sin(now * 0.8 + 2) * float);
    tile.group.position.set(0, 0.15 + 0.06 * Math.sin(now * 1.3) * float, -0.3 * wind - 0.18 * kb);
    tile.body.color.copy(bodyFrom).lerp(bodyTo, smooth((Math.min(go, 1) - 0.38) / 0.24));
    // the studio stays blue. The old glow fades as the tile leaves; the new verdict's colour ripples out when it clicks home
    const before = landed < 0;
    wave.uTint.value.copy(before ? bodyFrom : bodyTo);
    wave.uHalo.value = before ? glowFrom * (1 - smooth((s + 0.16) / 0.4)) : glowTo * smooth(landed / 0.5);
    wave.uRadius.value = before || !n ? -99 : landed * 30;
    bounce.groundColor.copy(studio).lerp(wave.uTint.value, 0.35 * wave.uHalo.value);

    // long lens, a little above and to the right; the tile sits right of the words, or above them on a phone
    const portrait = w < 760, dist = Math.max(15, 2.6 / (Math.tan((13 * Math.PI) / 180) * (w / h)));
    camera.position.set(1.2 * (dist / 15), 1.0 * (dist / 15), dist - (portrait ? 0 : 0.5 * Math.sin(now * 0.2) * float));
    camera.lookAt(0, 0.1, 0);
    if (portrait) camera.setViewOffset(w, h, 0, Math.round(h / 2 - 190), w, h); else camera.setViewOffset(w, h, -Math.round(w * 0.23), 0, w, h);
    renderer.render(scene, camera);
  }
  const size = () => {
    w = canvas.clientWidth || 1; h = canvas.clientHeight || 1;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
  };
  const run = () => { cancelAnimationFrame(raf); if (seen && !document.hidden) raf = requestAnimationFrame(frame); };
  new ResizeObserver(size).observe(canvas);
  new IntersectionObserver(([e]) => { seen = e.isIntersecting; run(); }).observe(canvas);
  document.addEventListener('visibilitychange', run);
  size(); run();
  return { turnTo };
}

try { stage = createStage(ui.canvas); document.body.classList.add('has-3d'); } catch { stage = null; }
// the page arrives already showing the first example; the tile turns to it, then the others follow
setTimeout(() => { if (!document.activeElement || document.activeElement !== ui.idea) { example(0); play(); } }, calm ? 0 : 900);
window.HERO_READY = true;

// the hall playing further down the page only runs while it is on screen
const hallFrame = document.querySelector('.hall-frame iframe');
if (hallFrame) {
  let visible = false;
  const tell = () => hallFrame.contentWindow?.postMessage({ hallVisible: visible }, location.origin);
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; tell(); }).observe(hallFrame);
  addEventListener('message', (ev) => { if (ev.origin === location.origin && ev.data?.hallReady) tell(); });
}
