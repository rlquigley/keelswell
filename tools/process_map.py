#!/usr/bin/env python3
"""Draw README.md's process maps as swim-lane SVGs in docs/.

    python3 tools/process_map.py

A map is data: its lanes, its steps on a grid of (lane, slot), and links that
name the side they leave one step by and the side they enter the next by.
`via` lists corners, in (lane, slot) units, for a link whose plain route would
cut through a step. To change a map, edit its data and run the script;
tools/tests/test_process_map.py fails while a committed map is stale.
"""
from pathlib import Path
from xml.sax.saxutils import escape

DOCS = Path(__file__).resolve().parent.parent / "docs"
SIZE = {"step": (84, 38), "ask": (84, 52), "end": (80, 28)}
FILL, LINE, INK, HEAD, BANDS = "#bccfdd", "#35546a", "#14232e", "#cfd9e2", ("#f6f8fa", "#e9eef2")
FONT = 'font-family="Helvetica, Arial, sans-serif"'

HIGH_LEVEL = {
    "file": "process-map-high-level.svg",
    "title": "Keelswell high-level process map",
    "across": True, "head": 84, "pitch": 104, "lane": 84,
    "lanes": ["You", "AI planners", "AI builders", "AI reviewers"],
    "steps": {
        "start": (0, 0, "end", "Start"),
        "idea": (0, 1, "step", "Share an\nidea"),
        "plan": (1, 1, "step", "Plan the\nproduct"),
        "stories": (1, 2, "step", "Write the\nstories"),
        "waves": (2, 2, "step", "Group into\nwaves"),
        "build": (2, 3, "step", "Build a\nwave"),
        "test": (3, 3, "step", "Test and\nreview"),
        "pass": (3, 4, "ask", "Pass?"),
        "pr": (2, 5, "step", "Open a pull\nrequest"),
        "merge": (0, 6, "step", "Review and\nmerge"),
        "done": (2, 6, "ask", "Epic\ndone?"),
        "audit": (3, 6, "step", "Audit the\nepic"),
        "next": (3, 7, "end", "Next epic"),
    },
    "links": [
        ("start", "E", "idea", "W"),
        ("idea", "S", "plan", "N"),
        ("plan", "E", "stories", "W"),
        ("stories", "S", "waves", "N"),
        ("waves", "E", "build", "W"),
        ("build", "S", "test", "N"),
        ("test", "E", "pass", "W"),
        ("pass", "N", "build", "E", "No"),
        ("pass", "E", "pr", "S", "Yes"),
        ("pr", "N", "merge", "W"),
        ("merge", "S", "done", "N"),
        ("done", "S", "audit", "N", "Yes"),
        ("done", "W", "build", "N", "No", [(2, 5.5), (1.6, 5.5), (1.6, 3)]),
        ("audit", "E", "next", "W"),
    ],
}

DETAILED = {
    "file": "process-map-detailed.svg",
    "title": "Keelswell detailed process map",
    "across": False, "head": 34, "pitch": 64, "lane": 150,
    "lanes": ["You", "AI planners", "AI lead", "AI coders", "AI reviewers"],
    "steps": {
        "start": (0, 0, "end", "Start"),
        "install": (0, 1, "step", "Install\nKeelswell"),
        "idea": (0, 2, "step", "Share an\nidea"),
        "research": (1, 3, "step", "Research the\nidea"),
        "brief": (1, 4, "step", "Write the\nproduct brief"),
        "prd": (1, 5, "step", "Write the\nPRD"),
        "hasui": (1, 6, "ask", "Has a\nUI?"),
        "ux": (1, 7, "step", "Design the\nUX"),
        "arch": (1, 8, "step", "Design the\narchitecture"),
        "stories": (1, 9, "step", "Write epics\nand stories"),
        "plan": (0, 10, "step", "Approve the\nplan"),
        "deps": (2, 11, "step", "Map story\ndependencies"),
        "draft": (2, 12, "step", "Draft the\nwave plan"),
        "waveplan": (0, 13, "step", "Approve the\nwave plan"),
        "wave": (0, 14, "step", "Start a\nwave"),
        "ready": (2, 15, "ask", "Ready to\nstart?"),
        "blocked": (0, 15, "end", "Blocked"),
        "workspace": (2, 16, "step", "Open a\nworkspace"),
        "design": (4, 17, "step", "Design the\ntests"),
        "details": (2, 18, "step", "Write story\ndetails"),
        "questions": (2, 19, "ask", "Open\nquestions?"),
        "answer": (0, 19, "step", "Answer the\nquestions"),
        "failing": (2, 20, "step", "Write failing\ntests"),
        "code": (3, 21, "step", "Code each\nstory"),
        "run": (2, 22, "step", "Run all\ntests"),
        "green": (2, 23, "ask", "Tests\npass?"),
        "fresh": (4, 24, "step", "Fresh-eyes\nreview"),
        "approved": (4, 25, "ask", "Approved?"),
        "resume": (0, 25, "step", "Resume in a\nnew session"),
        "commits": (0, 26, "step", "Approve the\ncommits"),
        "critical": (2, 27, "ask", "Critical\nwave?"),
        "specialist": (4, 27, "step", "Specialist\nreview"),
        "serious": (4, 28, "ask", "Serious\nissues?"),
        "record": (2, 29, "step", "Record the\nreview"),
        "pr": (2, 30, "step", "Open a pull\nrequest"),
        "wrap": (2, 31, "step", "Wrap up the\nsession"),
        "merge": (0, 32, "step", "Merge the\npull request"),
        "cleanup": (2, 33, "step", "Clean up the\nworkspace"),
        "epic": (2, 34, "ask", "Epic\ndone?"),
        "audit": (4, 35, "step", "Audit the\nepic"),
        "closure": (2, 36, "step", "Open the\nclosure PR"),
        "closed": (0, 37, "step", "Merge the\nclosure PR"),
        "more": (0, 38, "ask", "More\nepics?"),
        "done": (0, 39, "end", "Done"),
    },
    "links": [
        ("start", "S", "install", "N"),
        ("install", "S", "idea", "N"),
        ("idea", "E", "research", "N"),
        ("research", "S", "brief", "N"),
        ("brief", "S", "prd", "N"),
        ("prd", "S", "hasui", "N"),
        ("hasui", "S", "ux", "N", "Yes"),
        ("hasui", "E", "arch", "E", "No", [(1.42, 6), (1.42, 8)]),
        ("ux", "S", "arch", "N"),
        ("arch", "S", "stories", "N"),
        ("stories", "W", "plan", "N"),
        ("plan", "E", "deps", "N"),
        ("deps", "S", "draft", "N"),
        ("draft", "W", "waveplan", "N"),
        ("waveplan", "S", "wave", "N"),
        ("wave", "E", "ready", "N"),
        ("ready", "W", "blocked", "E", "No"),
        ("ready", "S", "workspace", "N", "Yes"),
        ("workspace", "E", "design", "N"),
        ("design", "S", "details", "E"),
        ("details", "S", "questions", "N"),
        ("questions", "W", "answer", "E", "Yes"),
        ("questions", "S", "failing", "N", "No"),
        ("answer", "S", "failing", "W"),
        ("failing", "E", "code", "N"),
        ("code", "W", "run", "N"),
        ("run", "S", "green", "N"),
        ("green", "E", "code", "S", "No"),
        ("green", "S", "fresh", "W", "Yes"),
        ("fresh", "S", "approved", "N"),
        ("approved", "W", "resume", "E", "No"),
        ("resume", "N", "code", "S", "", [(0, 24.5), (3, 24.5)]),
        ("approved", "S", "commits", "E", "Yes"),
        ("commits", "S", "critical", "W"),
        ("critical", "E", "specialist", "W", "Yes"),
        ("critical", "S", "record", "N", "No"),
        ("specialist", "S", "serious", "N"),
        ("serious", "E", "code", "E", "Yes", [(4.42, 28), (4.42, 21)]),
        ("serious", "S", "record", "E", "No"),
        ("record", "S", "pr", "N"),
        ("pr", "S", "wrap", "N"),
        ("wrap", "W", "merge", "N"),
        ("merge", "E", "cleanup", "N"),
        ("cleanup", "S", "epic", "N"),
        ("epic", "W", "wave", "W", "No", [(-0.42, 34), (-0.42, 14)]),
        ("epic", "S", "audit", "W", "Yes"),
        ("audit", "S", "closure", "E"),
        ("closure", "W", "closed", "N"),
        ("closed", "S", "more", "N"),
        ("more", "W", "wave", "W", "Yes", [(-0.42, 38), (-0.42, 14)]),
        ("more", "S", "done", "N", "No"),
    ],
}

SKILLS = {
    "file": "process-map-skills.svg",
    "title": "Keelswell skills map",
    "across": False, "head": 34, "pitch": 64, "lane": 200,
    "size": {"step": (136, 38), "ask": (96, 52), "end": (96, 28)},
    "lanes": ["You", "Wave skills", "Session skills"],
    "steps": {
        "start": (0, 0, "end", "Start"),
        "status": (2, 1, "step", "/bmad-status-wave\ncheck status"),
        "create": (1, 2, "step", "/bmad-create-wave\nplan the waves"),
        "stopped": (2, 2, "end", "Stopped wave"),
        "dev": (1, 3, "step", "/bmad-dev-wave\nbuild one wave"),
        "resume": (2, 3, "step", "/bmad-resume-wave\nresume a wave"),
        "wrap": (2, 4, "step", "/bmad-wrap\nend each session"),
        "merge": (0, 5, "step", "Merge the\npull request"),
        "mergewave": (1, 6, "step", "/bmad-merge-wave\nclean up the wave"),
        "epic": (1, 7, "ask", "Epic\ndone?"),
        "close": (1, 8, "step", "/bmad-close-epic\nclose the epic"),
        "closed": (0, 9, "step", "Merge the\nclosure PR"),
        "next": (0, 10, "end", "Next epic"),
    },
    "links": [
        ("start", "E", "status", "N"),
        ("status", "W", "create", "N"),
        ("create", "S", "dev", "N"),
        ("stopped", "S", "resume", "N"),
        ("resume", "W", "dev", "E"),
        ("dev", "S", "wrap", "W"),
        ("wrap", "S", "merge", "E"),
        ("merge", "S", "mergewave", "W"),
        ("mergewave", "S", "epic", "N"),
        ("epic", "W", "dev", "W", "No", [(0.42, 7), (0.42, 3)]),
        ("epic", "S", "close", "N", "Yes"),
        ("close", "S", "closed", "E"),
        ("closed", "S", "next", "N"),
    ],
}

MAPS = (HIGH_LEVEL, DETAILED, SKILLS)


def n(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def center(m, lane, slot):
    along, side = m["head"] + (slot + 0.5) * m["pitch"], (lane + 0.5) * m["lane"]
    return (along, side) if m["across"] else (side, along)


def port(m, name, side):
    lane, slot, shape, _ = m["steps"][name]
    (x, y), (w, h) = center(m, lane, slot), m.get("size", SIZE)[shape]
    return {"N": (x, y - h / 2), "S": (x, y + h / 2), "E": (x + w / 2, y), "W": (x - w / 2, y)}[side]


def route(m, a, out, b, into, via):
    """The link's points: one corner when it turns once, two when it leaves
    and enters along the same axis, or the corners `via` gives."""
    p, q = port(m, a, out), port(m, b, into)
    corners = [center(m, *v) for v in via]
    if not corners and p[0] != q[0] and p[1] != q[1]:
        if out in "EW" and into in "NS":
            corners = [(q[0], p[1])]
        elif out in "NS" and into in "EW":
            corners = [(p[0], q[1])]
        elif out in "EW":
            corners = [((p[0] + q[0]) / 2, p[1]), ((p[0] + q[0]) / 2, q[1])]
        else:
            corners = [(p[0], (p[1] + q[1]) / 2), (q[0], (p[1] + q[1]) / 2)]
    points = [p, *corners, q]
    if any(x1 != x2 and y1 != y2 for (x1, y1), (x2, y2) in zip(points, points[1:])):
        raise ValueError(f"{a} -> {b}: a segment is not straight")
    return points


def text(x, y, lines, size=12, weight="normal", anchor="middle"):
    top = y - (len(lines) - 1) * size * 0.6
    spans = "".join(f'<tspan x="{n(x)}" y="{n(top + i * size * 1.2)}">{escape(t)}</tspan>'
                    for i, t in enumerate(lines))
    return (f'<text {FONT} font-size="{size}" font-weight="{weight}" fill="{INK}" '
            f'text-anchor="{anchor}" dominant-baseline="central">{spans}</text>')


def rect(x, y, w, h, fill, rx=0):
    return (f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" rx="{n(rx)}" '
            f'fill="{fill}" stroke="{LINE}"/>')


def draw(m):
    cells = [s[:2] for s in m["steps"].values()]
    if len(cells) != len(set(cells)):
        raise ValueError(f"{m['file']}: two steps share a cell")
    along = m["head"] + (max(s[1] for s in cells) + 1) * m["pitch"]
    side = len(m["lanes"]) * m["lane"]
    w, h = (along, side) if m["across"] else (side, along)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{n(w)}" height="{n(h)}" '
           f'viewBox="0 0 {n(w)} {n(h)}" role="img">',
           f'<title>{escape(m["title"])}</title>',
           f'<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
           f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{LINE}"/></marker></defs>',
           f'<rect width="{n(w)}" height="{n(h)}" fill="#ffffff"/>']
    for i, name in enumerate(m["lanes"]):
        lo, size = i * m["lane"], m["lane"]
        band, head = ((0, lo, w, size), (0, lo, m["head"], size)) if m["across"] else \
            ((lo, 0, size, h), (lo, 0, size, m["head"]))
        out += [rect(*band, BANDS[i % 2]), rect(*head, HEAD),
                text(head[0] + head[2] / 2, head[1] + head[3] / 2, [name], 13, "bold")]
    for name, (lane, slot, shape, label) in m["steps"].items():
        (x, y), (sw, sh) = center(m, lane, slot), m.get("size", SIZE)[shape]
        if shape == "ask":
            out.append(f'<path d="M{n(x)},{n(y - sh / 2)} L{n(x + sw / 2)},{n(y)} L{n(x)},{n(y + sh / 2)} '
                       f'L{n(x - sw / 2)},{n(y)} Z" fill="{FILL}" stroke="{LINE}"/>')
        else:
            out.append(rect(x - sw / 2, y - sh / 2, sw, sh, FILL, sh / 2 if shape == "end" else 3))
        out.append(text(x, y, label.split("\n")))
    for link in m["links"]:
        label = link[4] if len(link) > 4 else ""
        points = route(m, *link[:4], link[5] if len(link) > 5 else ())
        out.append(f'<polyline points="{" ".join(f"{n(x)},{n(y)}" for x, y in points)}" fill="none" '
                   f'stroke="{LINE}" stroke-width="1.3" marker-end="url(#arrow)"/>')
        if label:  # a chip on the first segment, near the decision, or beside a short one
            (x1, y1), (x2, y2) = points[0], points[1]
            length, half = abs(x2 - x1) + abs(y2 - y1), len(label) * 3.5 + 4
            if length >= 36:
                mx, my = x1 + (x2 - x1) / length * 18, y1 + (y2 - y1) / length * 18
            elif x1 == x2:
                mx, my = x1 + half + 4, (y1 + y2) / 2
            else:
                mx, my = (x1 + x2) / 2, y1 - 12
            out += [f'<rect x="{n(mx - half)}" y="{n(my - 8)}" width="{n(2 * half)}" height="16" '
                    f'rx="3" fill="#ffffff" stroke="{LINE}" stroke-width="0.6"/>',
                    text(mx, my, [label], 11, "bold")]
    return "\n".join(out + ["</svg>"]) + "\n"


def main():
    for m in MAPS:
        (DOCS / m["file"]).write_text(draw(m))
        print(f"wrote docs/{m['file']}")


if __name__ == "__main__":
    main()
