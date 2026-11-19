"""Collapse-my-qubit game for the profile README.

Usage:
  python scripts/qubit.py measure   # needs env ISSUE_TITLE, PLAYER
  python scripts/qubit.py render    # just redraw README section + state.svg

A visitor opens an issue titled "qubit|0" or "qubit|1" (their guess).
The current state |psi> = cos(t/2)|0> + sin(t/2)e^{i phi}|1> is measured with
the Born rule, the result is recorded, and a fresh random state is prepared.
"""
import json
import math
import os
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "qubit.json"
README = ROOT / "README.md"
STATE_SVG = ROOT / "assets" / "state.svg"
REPO = "abdullah5341/abdullah5341"
START, END = "<!-- QUBIT:START -->", "<!-- QUBIT:END -->"
RNG = secrets.SystemRandom()


def load():
    if DATA.exists():
        return json.loads(DATA.read_text(encoding="utf-8"))
    return {"theta": math.pi / 2, "phi": 0.0, "total": 0, "counts": {"0": 0, "1": 0},
            "correct": 0, "players": {}, "recent": []}


def save(d):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(d, indent=2), encoding="utf-8")


def amps(d):
    return math.cos(d["theta"] / 2), math.sin(d["theta"] / 2)


def new_state(d):
    # uniform on the Bloch sphere: cos(theta) uniform in [-1, 1]
    d["theta"] = math.acos(1 - 2 * RNG.random())
    d["phi"] = RNG.random() * 2 * math.pi


def state_svg(d):
    t, ph = d["theta"], d["phi"]
    cx, cy, r = 160, 150, 105
    # simple oblique projection of the Bloch vector
    x, y, z = math.sin(t) * math.cos(ph), math.sin(t) * math.sin(ph), math.cos(t)
    px = cx + r * (y * 0.95 - x * 0.35)
    py = cy - r * (z * 0.95 - x * 0.22)
    a, b = amps(d)
    p0 = a * a
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 320" width="320" height="320" role="img" aria-label="Bloch sphere of the current qubit state, P(0) = {p0:.0%}">
<style>text{{font-family:'JetBrains Mono',ui-monospace,Menlo,Consolas,monospace}}
@keyframes pulse{{0%,100%{{r:7}}50%{{r:10}}}}.tip{{animation:pulse 1.6s ease-in-out infinite}}</style>
<defs><radialGradient id="g" cx=".38" cy=".3" r=".8"><stop offset="0" stop-color="#8b5cf6" stop-opacity=".4"/><stop offset="1" stop-color="#140f38" stop-opacity=".9"/></radialGradient>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
<rect width="320" height="320" rx="18" fill="#0d0b22"/>
<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#g)" stroke="#a78bfa" stroke-width="1.4"/>
<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{r*0.28:.1f}" fill="none" stroke="#a78bfa" opacity=".5"/>
<line x1="{cx}" y1="{cy-r-8}" x2="{cx}" y2="{cy+r+8}" stroke="#8f86c9" stroke-dasharray="3 4"/>
<text x="{cx}" y="{cy-r-14}" fill="#e9e5ff" font-size="14" text-anchor="middle">|0⟩</text>
<text x="{cx}" y="{cy+r+24}" fill="#e9e5ff" font-size="14" text-anchor="middle">|1⟩</text>
<line x1="{cx}" y1="{cy}" x2="{px:.1f}" y2="{py:.1f}" stroke="#67e8f9" stroke-width="3" stroke-linecap="round" filter="url(#glow)"/>
<circle class="tip" cx="{px:.1f}" cy="{py:.1f}" r="7" fill="#67e8f9" filter="url(#glow)"/>
<circle cx="{cx}" cy="{cy}" r="3" fill="#e9e5ff"/>
<rect x="18" y="292" width="{284*p0:.1f}" height="10" rx="5" fill="#a78bfa"/>
<rect x="{18+284*p0:.1f}" y="292" width="{284*(1-p0):.1f}" height="10" rx="5" fill="#67e8f9"/>
<text x="18" y="286" fill="#c4b5fd" font-size="11">P|0⟩ {p0:.0%}</text>
<text x="302" y="286" fill="#67e8f9" font-size="11" text-anchor="end">P|1⟩ {1-p0:.0%}</text>
</svg>'''


def issue_link(guess):
    title = f"qubit|{guess}"
    body = ("Just press **Submit new issue** 👇 — a GitHub Action will measure the qubit, "
            "update the README and reply here within about a minute.")
    from urllib.parse import quote
    return f"https://github.com/{REPO}/issues/new?title={quote(title)}&body={quote(body)}"


def section(d):
    a, b = amps(d)
    p0 = a * a
    v = d["total"]
    lines = [
        START,
        '<div align="center">',
        "",
        f'<img src="assets/state.svg?v={v}" width="260" alt="current qubit state"/>',
        "",
        f"**Right now my qubit is in** &nbsp;`|ψ⟩ = {a:.3f}|0⟩ + {b:.3f}·e^(i{d['phi']:.2f})|1⟩`",
        "",
        f"P(|0⟩) = **{p0:.0%}** &nbsp;·&nbsp; P(|1⟩) = **{1-p0:.0%}** &nbsp;— guess the outcome, then collapse it:",
        "",
        f'<a href="{issue_link(0)}"><img src="assets/btn0.svg" height="46" alt="Guess |0⟩"/></a>'
        f'&nbsp;&nbsp;<a href="{issue_link(1)}"><img src="assets/btn1.svg" height="46" alt="Guess |1⟩"/></a>',
        "",
    ]
    if d["recent"]:
        r = d["recent"][0]
        mark = "✅ called it" if r["guess"] == r["outcome"] else "❌ the universe disagreed"
        lines.append(f"<sub>Last observer: <b>@{r['player']}</b> guessed |{r['guess']}⟩ → measured "
                     f"<b>|{r['outcome']}⟩</b> at P={r['p']:.0%} · {mark}</sub>")
        lines.append("")
        acc = d["correct"] / v if v else 0
        lines.append(f"<sub>🧪 {v} measurements · |0⟩ ×{d['counts']['0']} · |1⟩ ×{d['counts']['1']} · "
                     f"observers called it {acc:.0%} of the time</sub>")
        lines.append("")
        top = sorted(d["players"].items(), key=lambda kv: (-kv[1]["correct"], kv[1]["plays"], kv[0]))[:5]
        lines += ["| 🏆 Observer | Correct | Measurements |", "|:--|:--:|:--:|"]
        for name, s in top:
            lines.append(f"| [@{name}](https://github.com/{name}) | {s['correct']} | {s['plays']} |")
    else:
        lines.append("<sub>No one has collapsed it yet — be the first observer.</sub>")
    lines += ["", "</div>", END]
    return "\n".join(lines)


def render(d):
    STATE_SVG.write_text(state_svg(d), encoding="utf-8")
    text = README.read_text(encoding="utf-8")
    pat = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    text = pat.sub(lambda _: section(d), text)
    README.write_text(text, encoding="utf-8")


def measure(d):
    title = os.environ.get("ISSUE_TITLE", "").strip()
    player = os.environ.get("PLAYER", "")
    m = re.fullmatch(r"qubit\|([01])", title)
    if not m or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", player):
        Path("comment.md").write_text("I couldn't read that guess. Use the |0⟩ / |1⟩ buttons on the profile. 🙏",
                                      encoding="utf-8")
        return False
    guess = int(m.group(1))
    a, _ = amps(d)
    p0 = a * a
    outcome = 0 if RNG.random() < p0 else 1
    p = p0 if outcome == 0 else 1 - p0
    hit = guess == outcome
    d["total"] += 1
    d["counts"][str(outcome)] += 1
    d["correct"] += int(hit)
    s = d["players"].setdefault(player, {"plays": 0, "correct": 0})
    s["plays"] += 1
    s["correct"] += int(hit)
    d["recent"].insert(0, {"player": player, "guess": guess, "outcome": outcome, "p": round(p, 4),
                           "at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    d["recent"] = d["recent"][:20]
    verdict = ("🎯 **You called it!**" if hit else "🌀 **Not this time** — that's quantum mechanics for you.")
    new_state(d)
    na, _ = amps(d)
    Path("comment.md").write_text(
        f"{verdict}\n\nYou guessed **|{guess}⟩**. The qubit had P(|{outcome}⟩) = {p:.0%} and collapsed to "
        f"**|{outcome}⟩**.\n\nI've prepared a fresh random state (P(|0⟩) = {na*na:.0%}) — go back to "
        f"[my profile](https://github.com/abdullah5341) to see it and try again. "
        f"Thanks for being observer #{d['total']}! ⚛️",
        encoding="utf-8")
    return True


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    data = load()
    if cmd == "measure":
        measure(data)
    save(data)
    render(data)
