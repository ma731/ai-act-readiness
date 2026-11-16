// Shared by the home page hero and the hall: the look (glossy toy plastic, thick rounded pieces),
// the motion (springs and knocks), the verdict tile, and the rules engine in the browser.
import * as THREE from 'three';

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const smooth = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
// a damped spring from 0 to 1 (a little past, then back) and the shudder after a knock
export const spring = (t, f = 3, d = 0.5) => { if (t <= 0) return 0; const w = 2 * Math.PI * f, wd = w * Math.sqrt(1 - d * d); return 1 - Math.exp(-d * w * t) * (Math.cos(wd * t) + ((d * w) / wd) * Math.sin(wd * t)); };
export const knock = (u) => (u <= 0 ? 0 : Math.exp(-u * 9) * Math.sin(u * 22));

export const TIER = {
  prohibited: { name: 'Prohibited', color: '#f97a6d' },
  high_risk: { name: 'High-risk', color: '#f5b14c' },
  transparency: { name: 'Transparency', color: '#7fb2f5' },
  minimal: { name: 'Minimal', color: '#7ddf9a' },
};

export const mat = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.78, ...o });
export const plastic = (color, o = {}) => new THREE.MeshPhysicalMaterial({ color, roughness: 0.42, clearcoat: 1, clearcoatRoughness: 0.08, ...o });   // glossy, like a toy
export const GOLD = () => new THREE.MeshPhysicalMaterial({ color: '#f2bf2e', metalness: 0.45, roughness: 0.3, clearcoat: 1, clearcoatRoughness: 0.1 });
// thick pieces with rounded-over edges, centred on z = 0
export const thick = (shape, depth, bevel = 0.05, round = 6) => {
  const g = new THREE.ExtrudeGeometry(shape, { depth: depth - 2 * bevel, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel, bevelOffset: -bevel, bevelSegments: round, curveSegments: 24 });
  g.translate(0, 0, -depth / 2 + bevel); return g;
};
export const squircle = (r, n = 4.4) => new THREE.Shape(Array.from({ length: 120 }, (_, i) => { const a = (i / 120) * Math.PI * 2, c = Math.cos(a), q = Math.sin(a); return new THREE.Vector2(r * Math.sign(c) * Math.abs(c) ** (2 / n), r * Math.sign(q) * Math.abs(q) ** (2 / n)); }));
export const bar = (w, h) => { const r = h / 2, sh = new THREE.Shape(); sh.absarc(w / 2 - r, 0, r, -Math.PI / 2, Math.PI / 2); sh.absarc(-w / 2 + r, 0, r, Math.PI / 2, Math.PI * 1.5); sh.closePath(); return sh; };
export const disc = (r) => new THREE.Shape().absarc(0, 0, r, 0, Math.PI * 2);

// a studio to reflect: three softboxes in a dim room, so plastic and gold have something to shine with
export function studioEnv(renderer, room = '#232a44') {
  const studio = new THREE.Scene();
  studio.add(new THREE.Mesh(new THREE.SphereGeometry(50, 32, 16), new THREE.MeshBasicMaterial({ color: room, side: THREE.BackSide })));
  for (const [x, y, z, bw, bh, power] of [[5, 24, 9, 28, 14, 3.4], [25, 8, 13, 9, 18, 2.4], [-23, 6, 11, 6, 20, 2]]) {
    const box = new THREE.Mesh(new THREE.PlaneGeometry(bw, bh), new THREE.MeshBasicMaterial({ color: new THREE.Color(power, power, power), side: THREE.DoubleSide }));
    box.position.set(x, y, z); box.lookAt(0, 0, 0); studio.add(box);
  }
  const pm = new THREE.PMREMGenerator(renderer), tex = pm.fromScene(studio, 0.03).texture;
  pm.dispose();
  return tex;
}

// A wall that keeps its own colour. A verdict sends a ring of its colour out from uCentre (uRadius is how far
// it has got; it fades as it travels) and leaves a soft glow of that colour around the centre (uHalo, 0..1).
export function waveMaterial(base, o = {}) {
  const wave = { uBase: { value: new THREE.Color(base) }, uTint: { value: new THREE.Color(base) }, uCentre: { value: new THREE.Vector3() },
    uRadius: { value: -99 }, uHalo: { value: 0 }, uSpread: { value: 5 } };
  const m = mat('#ffffff', { roughness: 0.95, ...o });
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, wave);
    sh.vertexShader = 'varying vec3 vWorld;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvWorld = (modelMatrix * vec4(transformed, 1.0)).xyz;');
    sh.fragmentShader = 'uniform vec3 uBase, uTint, uCentre; uniform float uRadius, uHalo, uSpread; varying vec3 vWorld;\n' + sh.fragmentShader.replace('#include <color_fragment>',
      '#include <color_fragment>\nfloat wd = distance(vWorld, uCentre);\nfloat ring = exp(-pow((wd - uRadius) / 1.5, 2.0)) * exp(-max(uRadius, 0.0) / 12.0);\n'
      + 'float halo = uHalo * exp(-wd * wd / (uSpread * uSpread));\ndiffuseColor.rgb = mix(uBase, uTint, clamp(ring * 0.5 + halo, 0.0, 1.0));');
  };
  return { material: m, wave };
}

// The verdict tile: a chunky rounded square with a gold band and a raised white symbol on each side.
// show(side, name) picks the symbol on side 0 (front) or 1 (back): 'waiting' or a tier.
export function makeTile(R = 1.28, T = 0.6) {
  const group = new THREE.Group(), body = plastic('#1c2d6b');
  group.add(new THREE.Mesh(thick(squircle(R), T, 0.2, 16), body));
  group.add(new THREE.Mesh(thick(squircle(R + 0.02), 0.08, 0.03), GOLD()));
  const white = new THREE.MeshPhysicalMaterial({ color: '#ffffff', roughness: 0.6, sheen: 0.4 }), k = R / 1.28;
  const PARTS = {
    waiting: [[disc(0.15), -0.5, 0], [disc(0.15), 0, 0], [disc(0.15), 0.5, 0]],
    prohibited: [[bar(1.7, 0.34), 0, 0, Math.PI / 4], [bar(1.7, 0.34), 0, 0, -Math.PI / 4]],          // a cross
    high_risk: [[bar(1.05, 0.36), 0, 0.3, Math.PI / 2], [disc(0.2), 0, -0.62]],                        // !
    transparency: [[disc(0.2), 0, 0.62], [bar(1.05, 0.36), 0, -0.3, Math.PI / 2]],                     // i: people must be told
    minimal: [[bar(0.8, 0.32), -0.42, -0.25, -Math.PI / 4], [bar(1.45, 0.32), 0.22, 0.05, Math.PI / 4]],   // a tick
  };
  const sides = [0, 1].map((side) => {
    const face = new THREE.Group(); face.position.z = (side ? -1 : 1) * T / 2; if (side) face.rotation.y = Math.PI; face.scale.setScalar(k);
    group.add(face);
    return Object.fromEntries(Object.entries(PARTS).map(([name, parts]) => {
      const g = new THREE.Group(); g.visible = false; face.add(g);
      parts.forEach(([shape, x, y, rot = 0], i) => { const m = new THREE.Mesh(thick(shape, 0.2, 0.06), white); m.position.set(x, y, 0.08 + i * 0.012); m.rotation.z = rot; g.add(m); });
      return [name, g];
    }));
  });
  const show = (side, name) => Object.entries(sides[side]).forEach(([n, g]) => { g.visible = n === name; });
  show(0, 'waiting');
  return { group, body, show };
}

export { check, engineStarted } from './engine.js';
