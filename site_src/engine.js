// The real screener (src/screener/ask.py) in the browser, through Pyodide. About 10 MB the first time.
const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.27.2/full/';
const PY_FILES = ['src/__init__.py', 'src/rules.py', 'src/screener/__init__.py', 'src/screener/law.py',
  'src/screener/readers.py', 'src/screener/pipeline.py', 'src/screener/redesign.py', 'src/screener/value.py',
  'src/screener/ask.py'];
let py = null;
const engine = () => py || (py = (async () => {
  await new Promise((res, rej) => {
    const s = document.createElement('script'); s.src = PYODIDE + 'pyodide.js'; s.onload = res; s.onerror = rej;
    document.head.appendChild(s);
  });
  const pyo = await window.loadPyodide({ indexURL: PYODIDE });
  pyo.FS.mkdirTree('/app/src/screener');
  const texts = await Promise.all(PY_FILES.map((f) => fetch('py/' + f).then((r) => { if (!r.ok) throw new Error(f); return r.text(); })));
  PY_FILES.forEach((f, i) => pyo.FS.writeFile('/app/' + f, texts[i]));
  pyo.runPython("import sys; sys.path.insert(0, '/app')");
  return pyo;
})().catch((err) => { py = null; throw err; }));
export const engineStarted = () => !!py;
// idea: { text, answers: [sentences from follow-ups], asked: [their ids] }
export const check = async (idea) => {
  const pyo = await engine();
  pyo.globals.set('_args', JSON.stringify(idea));
  return JSON.parse(pyo.runPython('import json\nfrom src.screener.ask import check\n_a = json.loads(_args)\n'
    + "json.dumps(check(_a['text'], _a['answers'], _a['asked']))"));
};
