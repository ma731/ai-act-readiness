"""Pre-record the guide's lines with a free neural voice (Microsoft Edge TTS).

    pip install edge-tts
    python scripts/build_voice.py

Reads site_src/guide/lines.json, renders any line not yet recorded to
site_src/guide/voice/<hash>.mp3 and writes site_src/guide/manifest.json (id -> file).
The mp3s are committed so the voice works on GitHub Pages. Re-run after editing a line.
"""
import asyncio
import hashlib
import json
import sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1] / "site_src" / "guide"
OUT = ROOT / "voice"
VOICE = "en-US-AvaNeural"   # warm and natural; slowed a little so it sounds calm
RATE, PITCH = "-6%", "-2Hz"


def spoken(text: str) -> str:
    return text.replace("2024/1689", "2024 slash 1689").replace('"', "")


async def render(text: str, path: Path) -> None:
    await edge_tts.Communicate(spoken(text), VOICE, rate=RATE, pitch=PITCH).save(str(path))


async def main() -> None:
    lines = json.loads((ROOT / "lines.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    manifest, todo = {}, []
    for key, text in lines.items():
        key_hash = hashlib.sha1(f"{VOICE}|{RATE}|{PITCH}|{spoken(text)}".encode()).hexdigest()
        name = key_hash[:12] + ".mp3"
        manifest[key] = name
        if not (OUT / name).exists():
            todo.append((text, OUT / name))
    for i in range(0, len(todo), 6):
        await asyncio.gather(*(render(t, p) for t, p in todo[i:i + 6]))
    keep = set(manifest.values())
    for f in OUT.glob("*.mp3"):
        if f.name not in keep:
            f.unlink()
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"{len(lines)} lines, {len(todo)} recorded now, voice {VOICE}")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
