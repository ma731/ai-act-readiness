// Small synthesized sounds for the hall. Web Audio only, no audio files. Silent until the visitor turns sound on.
let ctx = null, out = null, on = false;
try { on = localStorage.getItem('hall-sound') === '1'; } catch { on = false; }

export const soundOn = () => on;
export function setSound(v) {
  on = !!v;
  try { localStorage.setItem('hall-sound', on ? '1' : '0'); } catch { /* private window */ }
  if (on) ready();
}
// for tests: render into an OfflineAudioContext instead of the speakers
export function useContext(c) { ctx = c; out = null; on = true; }

function ready() {
  if (!on) return false;
  try {
    ctx ||= new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === 'suspended' && !(ctx instanceof OfflineAudioContext)) ctx.resume?.();
    if (!out) {
      const squash = ctx.createDynamicsCompressor(); squash.threshold.value = -14; squash.ratio.value = 3;
      out = ctx.createGain(); out.gain.value = 0.9; out.connect(squash); squash.connect(ctx.destination);
    }
    return true;
  } catch { return false; }
}
// one voice: quick attack, then it dies away by `dur`
function shape(t, dur, gain) {
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(gain, t + 0.006); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  g.connect(out); return g;
}
function tone(f, dur, { type = 'sine', gain = 0.15, at = 0, to = 0, cut = 0 } = {}) {
  const t = ctx.currentTime + at, o = ctx.createOscillator(); o.type = type;
  o.frequency.setValueAtTime(f, t); if (to) o.frequency.exponentialRampToValueAtTime(to, t + dur);
  let node = o;
  if (cut) { const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = cut; o.connect(lp); node = lp; }
  node.connect(shape(t, dur, gain)); o.start(t); o.stop(t + dur + 0.05);
}
let hiss = null;
function noise(dur, { type = 'bandpass', f = 1200, to = 0, q = 1, gain = 0.15, at = 0 } = {}) {
  if (!hiss || hiss.sampleRate !== ctx.sampleRate) {
    hiss = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
    const d = hiss.getChannelData(0); let s = 12345;
    for (let i = 0; i < d.length; i++) { s = (s * 16807) % 2147483647; d[i] = s / 1073741823.5 - 1; }
  }
  const t = ctx.currentTime + at, src = ctx.createBufferSource(), flt = ctx.createBiquadFilter();
  src.buffer = hiss; src.loop = true; flt.type = type; flt.Q.value = q;
  flt.frequency.setValueAtTime(f, t); if (to) flt.frequency.exponentialRampToValueAtTime(to, t + dur);
  src.connect(flt); flt.connect(shape(t, dur, gain)); src.start(t, (at * 7.3) % 0.9); src.stop(t + dur + 0.05);
}
const NOTE = { A3: 220, C4: 261.63, Eb4: 311.13, A4: 440, C5: 523.25, E5: 659.25, F4: 349.23, G5: 783.99, C6: 1046.5, D6: 1174.66, E6: 1318.5, G6: 1568 };
const CHORD = { minimal: ['C5', 'E5', 'G5', 'C6'], transparency: ['C5', 'G5', 'D6'], high_risk: ['A4', 'C5', 'E5'], prohibited: ['A3', 'C4', 'Eb4'] };

const play = (fn) => (...a) => { if (ready()) fn(...a); };
export const sfx = {
  step: play((left) => noise(0.05, { type: 'lowpass', f: left ? 420 : 340, gain: 1.6 })),
  paper: play(() => { noise(0.16, { f: 2600, to: 1400, q: 0.8, gain: 0.5 }); tone(170, 0.09, { to: 80, gain: 0.3 }); }),
  // what a person at a desk thinks: ok, nothing to add, wants a look, or no
  opinion: play((op) => {
    if (op === 'ok' || op === 'minimal') { tone(NOTE.E6, 0.5, { gain: 0.22 }); tone(NOTE.G6, 0.7, { gain: 0.2, at: 0.09 }); }
    else if (op === 'transparency') tone(NOTE.D6, 0.7, { gain: 0.24 });
    else if (op === 'none') tone(330, 0.14, { gain: 0.45, to: 300 });
    else if (op === 'prohibited') { tone(150, 0.16, { type: 'square', gain: 0.2, cut: 900 }); tone(120, 0.26, { type: 'square', gain: 0.2, cut: 800, at: 0.19 }); }
    else { tone(NOTE.A4, 0.22, { type: 'triangle', gain: 0.25 }); tone(NOTE.F4, 0.4, { type: 'triangle', gain: 0.25, at: 0.17 }); }
  }),
  whoosh: play(() => noise(0.42, { f: 320, to: 2300, q: 0.9, gain: 1.6 })),
  // the tile clicks home, then the verdict rings in its own key
  verdict: play((tier) => {
    tone(130, 0.24, { to: 45, gain: 0.6 }); noise(0.03, { type: 'highpass', f: 2500, gain: 0.3 });
    (CHORD[tier] || CHORD.minimal).forEach((n, i) => tone(NOTE[n], 1.7, { type: 'triangle', gain: 0.14, cut: 2400, at: 0.06 + i * (tier === 'prohibited' ? 0.12 : 0.07) }));
  }),
};
