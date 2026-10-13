#!/usr/bin/env python3
"""
Build the Business Analyst Services business-architecture site.

Reads the three model files in data/ and emits the static pages at the repo
root. The site is a rendering of the data, never a parallel copy of it: to
change the model, edit data/*.json and re-run this script.

    python3 build.py

No third-party dependencies.
"""

import html
import json
import os
import re
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")

ORG = "Business Analyst Services"

# Absolute path the site is served from, used only by 404.html — GitHub Pages
# serves that file for any missing path, including nested ones, where relative
# asset links would resolve against the wrong directory. "" for a user site
# served at the domain root; "/<repo>/" for a project site. Override with
# --base when building.
SITE_BASE = ""  # replaced from data/site.json at import time

NAV = [
    ("index.html", "Overview"),
    ("capability-map.html", "Capability map"),
    ("concept-model.html", "Concept model"),
    ("value-streams.html", "Value streams"),
    ("method.html", "Method"),
    ("downloads.html", "Downloads"),
]


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


SITE = load("site.json")

# The date the model last changed. Read from data/site.json, never from the
# clock: the Pages workflow rebuilds and fails if the generated HTML differs
# from what is committed, and a clock-derived date would break that check the
# day after any commit. Bump it by hand when the model changes.
BUILT = SITE.get("updated") or date.today().isoformat()


SITE_BASE = SITE.get("base", "")

CAP = load("capabilities.json")
CON = load("concepts.json")
VS = load("valuestreams.json")
BUNDLE = load("ba-skills-bundle.json")

DOMAINS = CAP["domains"]
SLOT = {d["id"]: i for i, d in enumerate(DOMAINS)}
DOMNAME = {d["id"]: d["name"] for d in DOMAINS}
L3 = [(d, l2, l3) for d in DOMAINS for l2 in d["l2"] for l3 in l2["l3"]]
CAPNAME = {l3["id"]: l3["name"] for _, _, l3 in L3}
CAPL2 = {l3["id"]: l2["name"] for _, l2, l3 in L3}
CAPDOM = {l3["id"]: d["id"] for d, _, l3 in L3}
OBJ = {o["id"]: o for o in CON["objects"]}
SRC2CON = {s: o for o in CON["objects"] for s in o["consolidates"]}
# Distinct business objects surfaced by the capability map. Not the same as the
# consolidates labels: "Client" appears there as a concept object introduced
# during consolidation, with no originating capability-map object.
SRC_OBJECTS = sorted({l3["businessObject"] for _, _, l3 in L3})
INTRODUCED = sorted(set(SRC2CON) - set(SRC_OBJECTS))
ROLE = {r["id"]: r for r in VS["roles"]}
TYPEVAR = {"Party": "--t-party", "Resource": "--t-resource", "Record": "--t-record"}

USED = {c for s in VS["valueStreams"] for st in s["stages"] for c in st["capabilities"]}
UNUSED = sorted(set(CAPNAME) - USED)
STAGE_OF = {}
for _s in VS["valueStreams"]:
    for _st in _s["stages"]:
        for _c in _st["capabilities"]:
            STAGE_OF.setdefault(_c, []).append((_s["id"], _st["name"]))


def e(s):
    return html.escape(str(s), quote=True)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# --------------------------------------------------------------------------- #
# Shared chrome
# --------------------------------------------------------------------------- #

THEME_BOOT = (
    "(function(){try{var t=localStorage.getItem('bas-ba-theme');"
    "if(t==='dark'||t==='light'){document.documentElement.setAttribute('data-theme',t);}}"
    "catch(e){}})();"
)


def head(title, desc, current, base=""):
    nav = "".join(
        '<li><a href="{href}"{cur}>{label}</a></li>'.format(
            href=h, label=e(l), cur=' aria-current="page"' if h == current else ""
        )
        for h, l in NAV
    )
    base = f'<base href="{e(base)}">\n' if base else ""
    return f"""<!doctype html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)} · {e(ORG)} Business Architecture</title>
<meta name="description" content="{e(desc)}">
<meta name="color-scheme" content="light dark">
{base}<link rel="stylesheet" href="assets/css/site.css">
<script>{THEME_BOOT}</script>
</head>
<body>
<a class="skip" href="#main">Skip to main content</a>
<header class="site-head">
  <div class="head-in">
    <a class="wordmark" href="index.html">
      <span class="mk" aria-hidden="true">BAS</span>
      <span>Business Architecture<small>{e(ORG)}</small></span>
    </a>
    <nav class="site-nav" aria-label="Sections">
      <ul>{nav}</ul>
    </nav>
    <button type="button" id="theme-toggle" class="theme-btn" hidden>Dark mode</button>
  </div>
</header>
<main id="main">
"""


def foot(extra_js=""):
    scripts = '<script src="assets/js/site.js"></script>'
    if extra_js:
        scripts += f"\n<script>{extra_js}</script>"
    return f"""</main>
<footer class="site-foot">
  <div class="foot-in">
    <p><strong>{e(ORG)}</strong> — a business analysis consulting, training and
    advisory practice in Sydney, Australia.
    <a href="https://business-analyst.services">business-analyst.services</a></p>
    <p>This model was produced with the PlausibleBA skills library and is published
    as a worked example. Last updated {e(BUILT)}.
    <a href="method.html">How it was made</a> · <a href="downloads.html">Download the model</a></p>
  </div>
</footer>
{scripts}
</body>
</html>
"""


def write(name, body):
    with open(os.path.join(ROOT, name), "w", encoding="utf-8") as fh:
        fh.write(body)
    print(f"  wrote {name:26s} {len(body) // 1024:>4d} KB")


def legend_domains():
    return '<ul class="legend">' + "".join(
        f'<li><span class="sw" style="background:var(--s{SLOT[d["id"]]})" aria-hidden="true"></span>{e(d["name"])}</li>'
        for d in DOMAINS
    ) + "</ul>"


def table(caption, headers, rows, open_label, numeric=()):
    def cls(i):
        return ' class="num"' if i in numeric else ""

    th = "".join(
        '<th scope="col"{0}>{1}</th>'.format(cls(i), e(h)) for i, h in enumerate(headers)
    )
    tr = "".join(
        "<tr>" + "".join("<td{0}>{1}</td>".format(cls(i), c) for i, c in enumerate(r)) + "</tr>"
        for r in rows
    )
    return f"""<details class="tbl">
<summary>{e(open_label)}</summary>
<div class="tw"><table>
<caption>{e(caption)}</caption>
<thead><tr>{th}</tr></thead>
<tbody>{tr}</tbody>
</table></div>
</details>"""


# --------------------------------------------------------------------------- #
# Squarified treemap
# --------------------------------------------------------------------------- #

# Rough advance width for the label fonts. Measured against the rendered
# figures rather than guessed: enough to decide whether a label fits its tile.
_WIDE = set("MWmw@%&ABCDGHKNOQRSUVXYZ")
_NARROW = set("iljtfIr.,;:'|()[]-")


def text_width(txt, size):
    """Estimated advance width, calibrated against the rendered figures. Errs
    high so a label is truncated rather than allowed to spill; the clip path on
    each tile is the hard backstop."""
    u = 0.0
    for ch in txt:
        if ch == " ":
            u += 0.30
        elif ch in _NARROW:
            u += 0.34
        elif ch in _WIDE:
            u += 0.78
        else:
            u += 0.62
    return u * size * 1.15


def fit(txt, size, avail):
    """Truncate to an ellipsis so the label never spills past its tile."""
    if avail <= 10:
        return ""
    if text_width(txt, size) <= avail:
        return txt
    out = txt
    while out and text_width(out + "\u2026", size) > avail:
        out = out[:-1]
    out = out.rstrip(" -&")
    return (out + "\u2026") if len(out) >= 2 else ""


def squarify(items, x, y, w, h):
    """items: [(key, value)] -> [(key, x, y, w, h)], largest first."""
    out = []
    items = sorted(items, key=lambda t: -t[1])
    total = sum(v for _, v in items)
    if total <= 0 or w <= 0 or h <= 0:
        return out
    scale = (w * h) / total
    vals = [(k, v * scale) for k, v in items]

    def worst(row, length):
        if not row or length == 0:
            return float("inf")
        s = sum(r[1] for r in row)
        return max((length * length * max(r[1] for r in row)) / (s * s),
                   (s * s) / (length * length * min(r[1] for r in row)))

    def lay(row, x, y, w, h, horizontal):
        s = sum(r[1] for r in row)
        res = []
        if horizontal:
            rw = s / h if h else 0
            oy = y
            for k, v in row:
                rh = v / rw if rw else 0
                res.append((k, x, oy, rw, rh))
                oy += rh
            return res, x + rw, y, w - rw, h
        rh = s / w if w else 0
        ox = x
        for k, v in row:
            rw2 = v / rh if rh else 0
            res.append((k, ox, y, rw2, rh))
            ox += rw2
        return res, x, y + rh, w, h - rh

    row = []
    while vals:
        horizontal = w <= h
        length = h if horizontal else w
        item = vals[0]
        if not row or worst(row + [item], length) <= worst(row, length):
            row.append(item)
            vals.pop(0)
        else:
            placed, x, y, w, h = lay(row, x, y, w, h, w <= h)
            out += placed
            row = []
    if row:
        placed, x, y, w, h = lay(row, x, y, w, h, w <= h)
        out += placed
    return out


# --------------------------------------------------------------------------- #
# Page: overview
# --------------------------------------------------------------------------- #

def page_index():
    stats = [
        (len(CAPNAME), "level-3 capabilities", "capability-map.html"),
        (len(DOMAINS), "capability domains", "capability-map.html"),
        (len(CON["objects"]), "concept objects", "concept-model.html"),
        (len(CON["relationships"]), "relationships", "concept-model.html"),
        (sum(len(s["stages"]) for s in VS["valueStreams"]), "value stream stages", "value-streams.html"),
        (f"{len(USED)}/{len(CAPNAME)}", "capabilities mapped to a stage", "value-streams.html"),
    ]
    tiles = "".join(
        f'<li class="stat"><span class="n">{e(n)}</span><span class="l">{e(l)}</span></li>'
        for n, l, _ in stats
    )
    cards = [
        ("capability-map.html", "Capability map",
         f"What the practice is able to do — {len(DOMAINS)} domains decomposed to "
         f"{len(CAPNAME)} level-3 capabilities, each tied to the thing it acts on."),
        ("concept-model.html", "Concept model",
         f"What the practice manages — {len(CON['objects'])} objects classified as Party, "
         f"Resource or Record, with {len(CON['relationships'])} relationships between them."),
        ("value-streams.html", "Value streams",
         "How value reaches a client and a learner — two streams, defined by the state "
         "change at each stage rather than by activity or department."),
    ]
    card_html = "".join(
        f'<li class="card"><h3><a href="{h}">{e(t)}</a></h3><p>{e(d)}</p>'
        f'<p class="go"><a href="{h}">Open {e(t.lower())} &rarr;</a></p></li>'
        for h, t, d in cards
    )

    return head(
        "Overview",
        f"The business architecture of {ORG}: a capability map, concept model and "
        "value streams, published as a worked PlausibleBA example.",
        "index.html",
    ) + f"""
<div class="page-head">
  <p class="eyebrow">Worked example</p>
  <h1>The business architecture of a business analysis practice</h1>
  <p class="lede">{e(ORG)} teaches business architecture. This is the practice
  modelled with its own method — a capability map, a concept model and two value
  streams, built in one session and published whole, including the parts that are
  still rough.</p>
</div>

<ul class="stats">{tiles}</ul>

<section class="section">
  <h2>The three artefacts</h2>
  <ul class="cards">{card_html}</ul>
</section>

<section class="section">
  <h2>What the model argues</h2>
  <p>Read in sequence the three artefacts make one claim, and it is a claim about
  the business rather than about the diagrams.</p>
  <p>Both value streams terminate in the same place. Consulting delivery ends at
  <strong>Realise &amp; Reinvest</strong>; a training cohort ends at
  <strong>Sustain &amp; Improve</strong>. Each exits into
  <a href="concept-model.html">Outcome&nbsp;&amp;&nbsp;Insight</a>, and that object
  feeds back into <strong>IP Asset</strong> and <strong>Course</strong> — the two
  resources the next engagement and the next cohort are built from.</p>
  <p>That loop is the difference between a consultancy that sells hours and one that
  compounds. An engagement that produces only deliverables leaves nothing behind; an
  engagement that also produces a playbook makes the next one cheaper to deliver and
  easier to sell. The model makes the loop explicit so it can be measured — which is
  why <em>reusable assets harvested per engagement</em> sits in the metric set
  alongside days sales outstanding.</p>
</section>

<section class="section">
  <h2>Where it is incomplete</h2>
  <div class="note">
    <p><strong>14 of {len(CAPNAME)} capabilities sit outside both value streams.</strong>
    Most are genuinely enabling — vendor selection and subscription administration do
    not advance a value item for anyone.</p>
    <p>But two clusters are not: <strong>manuscript authoring, editorial review and
    publishing</strong>, and <strong>product backlog management, software development
    and automated testing</strong>. A book shipped and the platform is a real product,
    so a third stream — <em>IP to Published Asset</em> — would likely absorb all six.
    It is not modelled here. <a href="value-streams.html#unmapped">See the full list</a>.</p>
  </div>
</section>

<section class="section">
  <h2>Using it</h2>
  <ul class="bullets">
    <li><strong>As a reference.</strong> The shape — 7 domains, Party/Resource/Record,
    stages defined by entry and exit state — transfers to any professional services
    practice. The content does not.</li>
    <li><strong>As data.</strong> Every artefact is downloadable as a four-tab register,
    and the whole model as a single JSON bundle for import into
    <a href="https://vcc.plausibleba.com">VCC</a> or the
    <a href="https://www.plausibleba.com/canvas">PlausibleBA canvas</a>.
    <a href="downloads.html">Downloads</a>.</li>
    <li><strong>As a check on the method.</strong> The
    <a href="method.html">method page</a> records what was elicited, what was decided
    at each checkpoint, and which calls are arguable.</li>
  </ul>
</section>
""" + foot()


# --------------------------------------------------------------------------- #
# Page: capability map
# --------------------------------------------------------------------------- #

def page_capability_map():
    W, H = 1160, 720
    dom_items = [(d["id"], sum(len(l2["l3"]) for l2 in d["l2"])) for d in DOMAINS]
    dom_rects = squarify(dom_items, 0, 0, W, H)
    dom_by_id = {d["id"]: d for d in DOMAINS}

    parts = []
    clips = []
    for did, x, y, w, h in dom_rects:
        dom = dom_by_id[did]
        s = SLOT[did]
        n = sum(len(l2["l3"]) for l2 in dom["l2"])
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" '
            f'fill="var(--s{s})" fill-opacity="0.15" stroke="var(--s{s})" stroke-width="1.5"/>'
        )
        dom_label = fit(dom["name"], 13, w - 26 - text_width(f" {n}", 13))
        if dom_label:
            clips.append(
                f'<clipPath id="clip-dom-{did}"><rect x="{x:.1f}" y="{y:.1f}" '
                f'width="{max(w - 6, 1):.1f}" height="30"/></clipPath>'
            )
            parts.append(
                f'<g clip-path="url(#clip-dom-{did})">'
                f'<text class="dl" x="{x + 12:.1f}" y="{y + 20:.1f}">{e(dom_label)}'
                f'<tspan class="dc"> {n}</tspan></text></g>'
            )
        inner = squarify([(l2["id"], len(l2["l3"])) for l2 in dom["l2"]],
                         x + 5, y + 30, max(w - 10, 1), max(h - 35, 1))
        l2_by_id = {l2["id"]: l2 for l2 in dom["l2"]}
        for key, cx, cy, cw, ch in inner:
            l2 = l2_by_id[key]
            cnt = len(l2["l3"])
            names = " · ".join(c["name"] for c in l2["l3"])
            name_fit = fit(l2["name"], 11.5, cw - 20)
            label = ""
            if name_fit and ch >= 24:
                clip_id = f"clip-{key}"
                clips.append(
                    f'<clipPath id="{clip_id}"><rect x="{cx + 1:.1f}" y="{cy + 1:.1f}" '
                    f'width="{max(cw - 10, 1):.1f}" height="{max(ch - 2, 1):.1f}"/></clipPath>'
                )
                label = f'<g clip-path="url(#{clip_id})">'
                label += (f'<text class="cn" x="{cx + 8:.1f}" y="{cy + 18:.1f}" '
                          f'fill="var(--on-s{SLOT[did]})">{e(name_fit)}</text>')
                if ch >= 40:
                    label += (f'<text class="cc" x="{cx + 8:.1f}" y="{cy + 33:.1f}" '
                              f'fill="var(--on-s{SLOT[did]})">{cnt}</text>')
                label += "</g>"
            parts.append(
                f'<g class="cell" tabindex="0" role="listitem" '
                f'aria-label="{e(l2["name"])}, {e(dom["name"])} domain, {cnt} capabilities: {e(names)}" '
                f'data-n="{e(l2["name"])}" data-d="{e(dom["name"])}" data-c="{cnt}" data-l="{e(names)}">'
                f'<rect x="{cx + 1:.1f}" y="{cy + 1:.1f}" width="{max(cw - 2, 1):.1f}" '
                f'height="{max(ch - 2, 1):.1f}" rx="4" fill="var(--s{SLOT[did]})"/>'
                + label
                + '</g>'
            )

    dom_rows = []
    for d in DOMAINS:
        n3 = sum(len(l2["l3"]) for l2 in d["l2"])
        dom_rows.append([
            f'<span class="chip" style="--c:var(--s{SLOT[d["id"]]});--on-c:var(--on-s{SLOT[d["id"]]})">{e(d["id"])}</span>',
            e(d["name"]), str(len(d["l2"])), str(n3),
            f"{n3 / len(CAPNAME) * 100:.1f}%",
        ])

    reg_rows = []
    for d, l2, l3 in L3:
        stages = STAGE_OF.get(l3["id"])
        stage_txt = ("; ".join(f"{sid} · {nm}" for sid, nm in stages) if stages
                     else '<span class="chip plain">not in a value stream</span>')
        reg_rows.append([
            f'<span class="mono">{e(l3["id"])}</span>', e(d["name"]), e(l2["name"]),
            e(l3["name"]), e(l3["businessObject"]),
            f'<a href="concept-model.html#{slug(SRC2CON[l3["businessObject"]]["name"])}">'
            f'{e(SRC2CON[l3["businessObject"]]["name"])}</a>',
            stage_txt,
        ])

    js = """
window.basTip('#treemap', '.cell', function (el) {
  return '<b>' + el.dataset.n + '</b><div class="m">' + el.dataset.d + ' · ' +
         el.dataset.c + ' capabilities</div><div class="d">' + el.dataset.l + '</div>';
});
"""

    return head(
        "Capability map",
        f"{len(CAPNAME)} level-3 capabilities across {len(DOMAINS)} domains, "
        "with the business object each one acts on.",
        "capability-map.html",
    ) + f"""
<div class="page-head">
  <p class="eyebrow">Phase 1</p>
  <h1>Capability map</h1>
  <p class="lede">What the practice is able to do, independent of who does it or how
  it is organised. {len(DOMAINS)} domains, {sum(len(d["l2"]) for d in DOMAINS)} level-2
  capabilities, {len(CAPNAME)} level-3 capabilities. Level 3 is the unit of analysis;
  levels 1 and 2 are grouping only.</p>
</div>

<section class="section">
  <h2 id="treemap-heading">The map</h2>
  {legend_domains()}
  <div class="chart scrolls" id="treemap">
    <svg viewBox="0 0 {W} {H}" role="list"
         aria-labelledby="treemap-heading" aria-describedby="treemap-desc">
      <style>
        .dl {{ fill: var(--ink); font-size: 13px; font-weight: 650; }}
        .dc {{ fill: var(--ink-3); font-weight: 500; }}
        .cn {{ font-size: 11.5px; font-weight: 600; pointer-events: none; }}
        .cc {{ font-size: 10.5px; font-weight: 500; pointer-events: none; }}
        .cell rect {{ transition: opacity .12s; }}
        .cell:hover rect, .cell:focus rect {{ opacity: .8; }}
        .cell:focus {{ outline: none; }}
        .cell:focus rect {{ stroke: var(--ink); stroke-width: 3; }}
      </style>
      <defs>{''.join(clips)}</defs>
      {''.join(parts)}
    </svg>
    <div class="tip" role="status" aria-live="polite"></div>
  </div>
  <p class="fig-note" id="treemap-desc">Tile area is proportional to the number of
  level-3 capabilities. Every tile is labelled with its name and count, and is
  reachable by keyboard — colour carries the domain only as a secondary cue. Full
  figures are in the tables below.</p>

  {table("Level-1 domains with level-2 and level-3 counts.",
         ["ID", "Domain", "L2", "L3", "% of map"], dom_rows,
         f"Domain summary ({len(DOMAINS)} rows)", numeric=(2, 3, 4))}

  {table("Every level-3 capability with its business object and value stream stages.",
         ["ID", "Domain", "L2 capability", "L3 capability", "Business object",
          "Concept object", "Value stream stages"], reg_rows,
         f"Full capability register ({len(reg_rows)} rows)")}
</section>

<section class="section">
  <h2>How to read it</h2>
  <ul class="bullets">
    <li><strong>A capability is an ability, not a process or a team.</strong>
    &ldquo;Requirements Elicitation&rdquo; is something the practice can do; it says
    nothing about who does it, in what order, or how often.</li>
    <li><strong>Every level-3 capability names the object it acts on.</strong> That
    column is what seeds the <a href="concept-model.html">concept model</a> —
    {len(SRC_OBJECTS)} business objects surfaced here, consolidated to
    {len(CON["objects"])} there.</li>
    <li><strong>The map is deliberately whole-practice.</strong> Consulting delivery,
    training, IP and publishing, and the platform all appear. A services-only map would
    be tidier and would hide where the leverage is.</li>
  </ul>
</section>
""" + foot(js)


# --------------------------------------------------------------------------- #
# Page: concept model
# --------------------------------------------------------------------------- #

def page_concept_model():
    W, H = 1240, 760
    NW, NH = 176, 52
    bands = [
        ("Party", 86, ["P1", "P2", "P4", "P5", "P3", "P6"]),
        ("Resource", 316, ["R6", "R1", "R2", "R3", "R4", "R5"]),
        ("Record", 546, ["D1", "D2", "D3", "D4", "D5"]),
        (None, 656, ["D9", "D7", "D6", "D8", "D10"]),
    ]
    pos = {}
    for _, y, ids in bands:
        margin, span = 40, W - 80
        slotw = span / len(ids)
        for i, pid in enumerate(ids):
            cx = margin + slotw * i + slotw / 2
            pos[pid] = (cx - NW / 2, y, cx)

    def path(a, b):
        ax, ay, acx = pos[a]
        bx, by, bcx = pos[b]
        if abs(ay - by) < 4:
            lift = 44 if acx < bcx else -44
            return (f"M {acx:.0f} {ay:.0f} C {acx:.0f} {ay - lift:.0f}, "
                    f"{bcx:.0f} {ay - lift:.0f}, {bcx:.0f} {ay:.0f}")
        if ay < by:
            gap = by - ay - NH
            return (f"M {acx:.0f} {ay + NH:.0f} C {acx:.0f} {ay + NH + gap * 0.55:.0f}, "
                    f"{bcx:.0f} {by - gap * 0.55:.0f}, {bcx:.0f} {by:.0f}")
        gap = ay - by - NH
        return (f"M {acx:.0f} {ay:.0f} C {acx:.0f} {ay - gap * 0.55:.0f}, "
                f"{bcx:.0f} {by + NH + gap * 0.55:.0f}, {bcx:.0f} {by + NH:.0f}")

    edges = []
    for r in CON["relationships"]:
        var = TYPEVAR[OBJ[r["from"]]["type"]]
        edges.append(
            f'<path class="edge" data-a="{r["from"]}" data-b="{r["to"]}" d="{path(r["from"], r["to"])}" '
            f'stroke="var({var})" fill="none" stroke-width="1.6" marker-end="url(#ar-{OBJ[r["from"]]["type"].lower()})"/>'
        )

    nodes = []
    for pid, o in OBJ.items():
        x, y, cx = pos[pid]
        var = TYPEVAR[o["type"]]
        out_n = sum(1 for r in CON["relationships"] if r["from"] == pid)
        in_n = sum(1 for r in CON["relationships"] if r["to"] == pid)
        nodes.append(
            f'<g class="node" data-id="{pid}" tabindex="0" role="listitem" '
            f'aria-label="{e(o["name"])}, {o["type"]}. {e(o["definition"])} '
            f'{out_n} outbound and {in_n} inbound relationships." '
            f'data-n="{e(o["name"])}" data-t="{o["type"]}" data-def="{e(o["definition"])}" '
            f'data-abs="{e(", ".join(o["consolidates"]))}">'
            f'<rect x="{x:.0f}" y="{y:.0f}" width="{NW}" height="{NH}" rx="8" fill="var({var})"/>'
            f'<text class="nn" x="{cx:.0f}" y="{y + 22:.0f}" text-anchor="middle" '
            f'fill="var(--on-{o["type"].lower()})">{e(o["name"])}</text>'
            f'<text class="ni" x="{cx:.0f}" y="{y + 39:.0f}" text-anchor="middle" '
            f'fill="var(--on-{o["type"].lower()})">{pid} · {o["type"]}</text>'
            f'</g>'
        )

    band_labels = "".join(
        f'<text class="bl" x="40" y="{y - 14:.0f}">{lbl.upper()}</text>'
        for lbl, y, _ in bands if lbl
    )
    markers = "".join(
        f'<marker id="ar-{t.lower()}" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" '
        f'markerHeight="6" orient="auto-start-reverse">'
        f'<path d="M0 0 L8 4 L0 8 z" fill="var({v})"/></marker>'
        for t, v in TYPEVAR.items()
    )

    def type_block(t):
        rows = []
        for o in CON["objects"]:
            if o["type"] != t:
                continue
            rows.append(
                f'<tr id="{slug(o["name"])}"><td><span class="mono">{e(o["id"])}</span></td>'
                f'<td><strong>{e(o["name"])}</strong></td><td>{e(o["definition"])}</td>'
                f'<td>{e(", ".join(o["consolidates"]))}</td></tr>'
            )
        n = sum(1 for o in CON["objects"] if o["type"] == t)
        blurb = {
            "Party": "Someone who acts — a person or an organisation with agency in the model.",
            "Resource": "Something used to produce value. Consumed, applied or drawn on, not evidenced.",
            "Record": "Evidence that something happened or was agreed. The things the practice can point at.",
        }[t]
        return f"""<h3 id="type-{t.lower()}">
  <span class="chip" style="--c:var({TYPEVAR[t]});--on-c:var(--on-{t.lower()})">{t}</span> &nbsp;{n} objects</h3>
<p>{blurb}</p>
<div class="tw"><table>
<caption>{t} objects, with the capability-map business objects each one absorbs.</caption>
<thead><tr><th scope="col">ID</th><th scope="col">Object</th><th scope="col">Definition</th>
<th scope="col">Absorbs</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>"""

    if INTRODUCED:
        introduced_txt = (
            "<strong>" + ", ".join(e(i) for i in INTRODUCED) + "</strong> was introduced "
            "during consolidation as the party behind Opportunity and Contract. No "
            "capability names it as the thing it acts on, which is itself worth "
            "noticing: the practice has no capability whose object is the client "
            "relationship."
        )
    else:
        introduced_txt = "None — every object traces back to a capability."
    n_from_map = len(CON["objects"]) - len(INTRODUCED)
    n_src = len(SRC_OBJECTS)

    rel_rows = [
        [f'<span class="mono">{e(r["from"])}</span>',
         f'<a href="#{slug(OBJ[r["from"]]["name"])}">{e(OBJ[r["from"]]["name"])}</a>',
         e(r["label"]),
         f'<span class="mono">{e(r["to"])}</span>',
         f'<a href="#{slug(OBJ[r["to"]]["name"])}">{e(OBJ[r["to"]]["name"])}</a>']
        for r in CON["relationships"]
    ]

    js = """
window.basTip('#graph', '.node', function (el) {
  return '<b>' + el.dataset.n + '</b><div class="m">' + el.dataset.id + ' · ' +
         el.dataset.t + '</div><div class="d">' + el.dataset.def +
         '</div><div class="m" style="margin:5px 0 0">Absorbs: ' + el.dataset.abs + '</div>';
});
(function () {
  var svg = document.querySelector('#graph svg');
  if (!svg) { return; }
  var edges = [].slice.call(svg.querySelectorAll('.edge'));
  var nodes = [].slice.call(svg.querySelectorAll('.node'));
  function on(g) {
    var id = g.dataset.id, linked = {};
    linked[id] = 1;
    edges.forEach(function (p) {
      var hit = p.dataset.a === id || p.dataset.b === id;
      p.classList.toggle('on', hit);
      if (hit) { linked[p.dataset.a] = 1; linked[p.dataset.b] = 1; }
    });
    nodes.forEach(function (n) { n.classList.toggle('on', !!linked[n.dataset.id]); });
    svg.classList.add('focusing');
  }
  function off() {
    svg.classList.remove('focusing');
    edges.forEach(function (p) { p.classList.remove('on'); });
    nodes.forEach(function (n) { n.classList.remove('on'); });
  }
  nodes.forEach(function (g) {
    g.addEventListener('mouseenter', function () { on(g); });
    g.addEventListener('focus', function () { on(g); });
    g.addEventListener('mouseleave', off);
    g.addEventListener('blur', off);
  });
})();
"""

    return head(
        "Concept model",
        f"{len(CON['objects'])} objects classified as Party, Resource or Record, with "
        f"{len(CON['relationships'])} relationships.",
        "concept-model.html",
    ) + f"""
<div class="page-head">
  <p class="eyebrow">Phase 2</p>
  <h1>Concept model</h1>
  <p class="lede">What the practice manages: the things it holds facts about, and how
  they relate. The {len(CAPNAME)} capabilities surfaced {len(SRC_OBJECTS)} business objects;
  those consolidate to {len(CON["objects"])} concept objects with
  {len(CON["relationships"])} relationships. Every one of the {len(SRC_OBJECTS)} is
  accounted for — none were dropped.</p>
</div>

<section class="section">
  <h2 id="graph-heading">The model</h2>
  <ul class="legend">
    <li><span class="sw" style="background:var(--t-party)" aria-hidden="true"></span>Party — who acts</li>
    <li><span class="sw" style="background:var(--t-resource)" aria-hidden="true"></span>Resource — what is used</li>
    <li><span class="sw" style="background:var(--t-record)" aria-hidden="true"></span>Record — what is evidenced</li>
  </ul>
  <div class="chart scrolls" id="graph">
    <svg viewBox="0 0 {W} {H}" role="list" style="min-width:900px"
         aria-labelledby="graph-heading" aria-describedby="graph-desc">
      <defs>{markers}</defs>
      <style>
        .nn {{ font-size: 12.5px; font-weight: 650; pointer-events: none; }}
        .ni {{ font-size: 10px; font-weight: 500; pointer-events: none; }}
        .bl {{ fill: var(--ink-3); font-size: 9.5px; font-weight: 700; letter-spacing: .09em; }}
        .edge {{ stroke-opacity: .34; transition: stroke-opacity .12s; }}
        .node rect {{ transition: opacity .12s; }}
        .node:focus {{ outline: none; }}
        .node:focus rect {{ stroke: var(--ink); stroke-width: 3; }}
        svg.focusing .edge {{ stroke-opacity: .07; }}
        svg.focusing .edge.on {{ stroke-opacity: .95; stroke-width: 2.4; }}
        svg.focusing .node rect {{ opacity: .28; }}
        svg.focusing .node.on rect {{ opacity: 1; }}
      </style>
      {band_labels}{''.join(edges)}{''.join(nodes)}
    </svg>
    <div class="tip" role="status" aria-live="polite"></div>
  </div>
  <p class="fig-note" id="graph-desc">Objects are grouped in bands by type and labelled
  with their type name, so colour is never the only cue. Hovering or focusing an object
  dims everything it does not connect to. Each object's full definition and every
  relationship are listed in the tables below.</p>
</section>

<section class="section">
  <h2>The spine</h2>
  <p>Six of the {len(CON["relationships"])} relationships carry the consulting business:
  <strong>Client</strong> is the source of an <strong>Opportunity</strong>, which converts
  to a <strong>Contract</strong>, which authorises an <strong>Engagement</strong>, which
  produces a <strong>Deliverable</strong>, which is evaluated by
  <strong>Outcome&nbsp;&amp;&nbsp;Insight</strong>.</p>
  <p>Training runs in parallel: <strong>Learner</strong> registers via an
  <strong>Enrolment</strong> held against a <strong>Course</strong>, which is sourced from
  an <strong>IP Asset</strong>, which embodies the <strong>Methodology</strong>.</p>
  <p>The two meet at Outcome&nbsp;&amp;&nbsp;Insight, which improves both IP Asset and
  Course. That is the only cycle in the model, and it is intentional.</p>
</section>

<section class="section">
  <h2>Objects by type</h2>
  {type_block("Party")}
  {type_block("Resource")}
  {type_block("Record")}
</section>

<section class="section">
  <h2>Relationships</h2>
  {table("All directed relationships. Read as: From, relationship, To.",
         ["From ID", "From", "Relationship", "To ID", "To"], rel_rows,
         f"All relationships ({len(rel_rows)} rows)")}
  <div class="note">
    <p><strong>One object has no origin in the capability map.</strong>
    {introduced_txt} The other {n_from_map} concept objects each consolidate at least
    one of the {n_src} business objects the capabilities surfaced.</p>
  </div>
  <div class="note" style="margin-top:12px">
    <p><strong>Two calls worth arguing with.</strong>
    <em>Lead</em> was folded into Opportunity as an early state rather than kept as its
    own object — defensible for a practice of this size, wrong for one with a real
    marketing funnel. <em>Practice Strategy</em> was folded into Service Offering rather
    than becoming a governance object, which makes strategy invisible in the model.</p>
  </div>
</section>
""" + foot(js)


# --------------------------------------------------------------------------- #
# Page: value streams
# --------------------------------------------------------------------------- #

def page_value_streams():
    sections = []
    for s in VS["valueStreams"]:
        cards = []
        for i, st in enumerate(s["stages"]):
            chips = "".join(
                f'<li><span class="chip" style="--c:var(--s{SLOT[CAPDOM[c]]});--on-c:var(--on-s{SLOT[CAPDOM[c]]})" '
                f'title="{e(DOMNAME[CAPDOM[c]])}">{e(CAPNAME[c])}</span></li>'
                for c in st["capabilities"]
            )
            mets = "".join(f"<li>{e(m)}</li>" for m in st["metrics"])
            roles = " · ".join(e(ROLE[r]["name"]) for r in st["roles"])
            vo = OBJ[st["valueObject"]]
            cards.append(f"""<li class="stage">
  <div class="stage-head">
    <span class="stage-num" aria-hidden="true">{i + 1}</span>
    <h3 id="{slug(s['id'] + ' ' + st['name'])}">{e(st["name"])}</h3>
  </div>
  <div class="states">
    <p class="state"><span class="k">Entry</span>{e(st["entryState"])}</p>
    <p class="state-arrow" aria-hidden="true">&darr;</p>
    <p class="state"><span class="k">Exit</span>{e(st["exitState"])}</p>
  </div>
  <p class="outcome">{e(st["outcome"])}</p>
  <p class="kv"><b>Advances</b>
    <a href="concept-model.html#{slug(vo["name"])}">{e(vo["name"])}</a>
    <span style="color:var(--ink-3)">({vo["type"]})</span></p>
  <div class="block"><b>Capabilities ({len(st["capabilities"])})</b>
    <ul class="chips">{chips}</ul></div>
  <div class="block"><b>Candidate metrics</b><ul class="m">{mets}</ul></div>
  <p class="kv"><b>Roles</b> {roles}</p>
</li>""")
        nstages = len(s["stages"])
        ncaps = sum(len(st["capabilities"]) for st in s["stages"])
        sections.append(f"""<section class="section" id="{s["id"].lower()}">
  <h2>{e(s["id"])} · {e(s["name"])}</h2>
  <dl class="facts">
    <dt>Trigger</dt><dd>{e(s["trigger"])}</dd>
    <dt>Value delivered</dt><dd>{e(s["valueProposition"])}</dd>
    <dt>Primary stakeholder</dt><dd>{e(s["stakeholder"])}</dd>
    <dt>Shape</dt><dd>{nstages} stages, {ncaps} stage-to-capability mappings</dd>
  </dl>
  <ol class="track">{''.join(cards)}</ol>
</section>""")

    stage_rows = []
    for s in VS["valueStreams"]:
        for i, st in enumerate(s["stages"]):
            stage_rows.append([
                e(s["id"]), str(i + 1),
                f'<a href="#{slug(s["id"] + " " + st["name"])}">{e(st["name"])}</a>',
                e(st["entryState"]), e(st["exitState"]),
                f'<a href="concept-model.html#{slug(OBJ[st["valueObject"]]["name"])}">'
                f'{e(OBJ[st["valueObject"]]["name"])}</a>',
                str(len(st["capabilities"])),
            ])

    unmapped = "".join(
        f'<li><span class="chip" style="--c:var(--s{SLOT[CAPDOM[c]]});--on-c:var(--on-s{SLOT[CAPDOM[c]]})">{e(CAPNAME[c])}</span> '
        f'<span class="mono">{e(c)}</span></li>'
        for c in UNUSED
    )

    return head(
        "Value streams",
        "Two value streams, 11 stages, defined by the state change at each stage.",
        "value-streams.html",
    ) + f"""
<div class="page-head">
  <p class="eyebrow">Phase 3</p>
  <h1>Value streams</h1>
  <p class="lede">How value actually reaches someone. The practice monetises through two
  distinct paths, so both are modelled. Stages are defined by the <strong>state of the
  value item</strong> when it arrives and when it leaves — not by activity, not by who
  does the work.</p>
</div>

{legend_domains()}
<p class="fig-note">Capability chips are coloured by domain and always carry their name,
so the colour is a grouping cue rather than the information itself.</p>

{''.join(sections)}

<section class="section" id="unmapped">
  <h2>Capabilities outside both streams</h2>
  <p>{len(USED)} of {len(CAPNAME)} capabilities are called on by a stage. The remaining
  {len(UNUSED)} are not, and that is worth being explicit about rather than hiding.</p>
  <ul class="chips" style="gap:8px 14px;margin-bottom:16px">{unmapped}</ul>
  <div class="note">
    <p><strong>Most of these are genuinely enabling.</strong> Vendor Selection and
    Subscription Administration support delivery without advancing anyone's value item.
    Market Positioning Definition and Service Portfolio Planning are strategic — they
    shape what the streams carry rather than running inside one.</p>
    <p><strong>Two clusters are a real gap.</strong> Manuscript Authoring, Editorial
    Review and Publishing &amp; Distribution describe a book that has shipped. Product
    Backlog Management, Software Development and Automated Testing describe a platform
    that exists. Both produce something for someone outside the practice, which is the
    test of a value stream. A third stream — <em>IP to Published Asset</em>, running from
    research through to a published, licensed asset — would absorb all six. It is not
    modelled here, and the model is weaker for it.</p>
  </div>
</section>

<section class="section">
  <h2>All stages</h2>
  {table("Every stage across both value streams, in sequence.",
         ["Stream", "#", "Stage", "Entry state", "Exit state", "Advances", "Caps"],
         stage_rows, f"Stage table ({len(stage_rows)} rows)", numeric=(1, 6))}
  <p>The metrics listed on each stage are <strong>candidates, not baselines</strong>.
  No current values exist for any of them; they are proposed measures that match the
  state change the stage is responsible for.</p>
</section>
""" + foot()


# --------------------------------------------------------------------------- #
# Page: method
# --------------------------------------------------------------------------- #

def page_method():
    el = BUNDLE["elements"]
    counts = "".join(
        f"<dt>{e(k)}</dt><dd>{len(v)}</dd>" for k, v in el.items()
    )
    role_rows = [[f'<span class="mono">{e(r["id"])}</span>', e(r["name"]), e(r["description"])]
                 for r in VS["roles"]]

    return head(
        "Method",
        "How the model was built: the phases, the checkpoints, the arguable calls, "
        "and how the output was verified.",
        "method.html",
    ) + f"""
<div class="page-head">
  <p class="eyebrow">Provenance</p>
  <h1>How this model was built</h1>
  <p class="lede">A model is only as trustworthy as the account of how it was made.
  This page records what was elicited, what was decided and by whom, which calls are
  arguable, and what was actually checked.</p>
</div>

<section class="section">
  <h2>The run</h2>
  <dl class="facts">
    <dt>Method</dt><dd>PlausibleBA skills library v1.5.0, three phases in one session</dd>
    <dt>Elicited</dt><dd>15 September 2026</dd>
    <dt>Site last updated</dt><dd>{e(BUILT)}</dd>
    <dt>Input</dt><dd>A description of the practice. No external reference model, no
    client data, no survey — the content is self-reported and should be read that way.</dd>
    <dt>Scaffold ID</dt><dd><span class="mono">{e(BUNDLE["meta"]["scaffoldId"])}</span></dd>
  </dl>
</section>

<section class="section">
  <h2>Phases and checkpoints</h2>
  <p>Each phase stopped at a confirmation checkpoint before anything downstream was
  built. Capability mapping takes two, because committing to level 3 before the level-1
  and level-2 structure is agreed wastes the decomposition.</p>
  <ol class="bullets">
    <li><strong>Checkpoint 1A</strong> — {len(DOMAINS)} domains and
    {sum(len(d["l2"]) for d in DOMAINS)} level-2 capabilities. Confirmed as drafted. The
    alternative considered and rejected was narrowing to consulting plus training, which
    would have dropped Platform &amp; Technology.</li>
    <li><strong>Checkpoint 1B</strong> — the {len(CAPNAME)} level-3 capabilities with a
    business object on each. Confirmed as drafted.</li>
    <li><strong>Checkpoint 2</strong> — {len(SRC_OBJECTS)} business objects consolidated to
    {len(CON["objects"])} concept objects, classified and related. Confirmed as drafted.
    Rejected alternatives: splitting Outcome&nbsp;&amp;&nbsp;Insight into benefit and
    insight, promoting Lead to its own object, and collapsing further to about 15.</li>
    <li><strong>Checkpoint 3</strong> — the stage draft for both streams. Confirmed with
    both streams retained, rather than consulting only, a single merged stream, or a
    split of the final stage.</li>
  </ol>
</section>

<section class="section">
  <h2>Calls that could reasonably go the other way</h2>
  <ul class="bullets">
    <li><strong>Lead folded into Opportunity.</strong> Treating unqualified interest as
    an early state of Opportunity suits a practice where enquiries are few and
    personally handled. A real marketing funnel needs Lead as its own record.</li>
    <li><strong>Practice Strategy folded into Service Offering.</strong> This makes
    strategy a property of the portfolio rather than a thing the practice manages. The
    cost is that strategic capabilities have nowhere obvious to attach.</li>
    <li><strong>Outcome &amp; Insight as one object.</strong> It carries benefits
    realised, learner feedback, research findings and usage metrics. That breadth is
    what lets it close the loop in one relationship, and it is also the reason someone
    could argue it is two objects wearing one name.</li>
    <li><strong>Assessment inside Course, Certificate inside Enrolment.</strong> Assessment
    design is a resource; a marked assessment is evidence. Splitting them across two
    objects is a judgement, not a rule.</li>
    <li><strong>No third value stream.</strong> The most consequential omission.
    <a href="value-streams.html#unmapped">Six capabilities are stranded by it.</a></li>
  </ul>
</section>

<section class="section">
  <h2>The bundle</h2>
  <p>The whole model serialises to one JSON file against the ba-skills-bundle schema
  v{e(BUNDLE["meta"]["bundleVersion"])}, for import into VCC or the PlausibleBA canvas.
  Element counts:</p>
  <dl class="facts">{counts}</dl>
  <p>Capabilities number {len(el["capabilities"])} because the bundle carries all three
  levels; {len(CAPNAME)} of them are level 3. Information objects are the
  {len(SRC_OBJECTS)} business objects from the capability map, each linked to the concept
  object that consolidates it and to the capabilities that manage it.</p>
  <p><a class="btn" href="downloads/business-analyst-services-ba-skills-bundle.json" download>Download the bundle</a></p>
</section>

<section class="section">
  <h2>Roles referenced</h2>
  <div class="tw"><table>
    <caption>Roles named by value stream stages.</caption>
    <thead><tr><th scope="col">ID</th><th scope="col">Role</th><th scope="col">Description</th></tr></thead>
    <tbody>{''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in role_rows)}</tbody>
  </table></div>
</section>

<section class="section">
  <h2>What was verified</h2>
  <p>Checks that were actually run, not an aspiration:</p>
  <ul class="bullets">
    <li><strong>Referential integrity across the bundle.</strong> Every parent, concept,
    capability, value-object, role, outcome, metric and stage reference resolves to an
    element that exists, and every map key equals its own element ID.</li>
    <li><strong>Consolidation completeness.</strong> All {len(SRC_OBJECTS)} capability-map
    business objects resolve to exactly one of the {len(CON["objects"])} concept objects.</li>
    <li><strong>Coverage.</strong> {len(USED)} of {len(CAPNAME)} capabilities map to a
    stage; the {len(UNUSED)} that do not are enumerated in the bundle metadata and match
    the computed set.</li>
    <li><strong>Workbooks.</strong> Each register opens with its four expected tabs and
    recalculates with zero formula errors under LibreOffice. Rollups reconcile: domain
    counts to {len(CAPNAME)}, percentages to 100%, relationship counts to
    {len(CON["relationships"])} outbound and {len(CON["relationships"])} inbound.</li>
    <li><strong>Accessibility.</strong> Every figure has a text alternative and a table
    view, every interactive mark is keyboard-reachable and labelled, and the colour
    palette was validated rather than eyeballed — see below.</li>
  </ul>
</section>

<section class="section">
  <h2>Colour, and why it is not the brand palette</h2>
  <p>The practice's brand hexes are navy <span class="mono">#23446E</span> and
  <span class="mono">#003E52</span>, teal <span class="mono">#5ABABA</span> and orange
  <span class="mono">#FF8300</span>. Used directly as the seven domain colours they fail
  a categorical palette check: the two navies fall outside the usable lightness band, and
  three of the four sit below the chroma floor, which means they read as grey once they
  are small.</p>
  <p>So the data colours keep the brand <em>hue angles</em> and re-step the lightness and
  chroma into the passing band, with four further hues spaced around the wheel. The
  resulting order was validated for colour-blind separation and surface contrast in both
  light and dark modes, and the dark steps were chosen for the dark surface rather than
  flipped from the light ones.</p>
  <p>Raw brand colours still do the chrome — wordmark, buttons, the accent on the current
  nav item. Every chart also labels its marks directly and ships a table view, so no
  reading of any figure depends on telling two colours apart.</p>
</section>

<section class="section">
  <h2>Honest limitations</h2>
  <ul class="bullets">
    <li>The content is <strong>self-reported in a single session</strong>. Nobody else was
    interviewed, and no client or learner was asked whether the stages match their
    experience.</li>
    <li>Metrics are <strong>proposed, never baselined</strong>. No value in the model has
    been measured.</li>
    <li>Capability <strong>maturity and ownership are not modelled</strong> at all. The map
    says what the practice can do, not how well or who is accountable.</li>
    <li>The third value stream is <strong>missing</strong>, and six capabilities are
    stranded as a result.</li>
    <li>The level-3 count, {len(CAPNAME)}, is on the <strong>large side</strong> for a
    practice this size. It is honest about the breadth of work but would be hard to
    govern as a live artefact without pruning.</li>
  </ul>
</section>

<section class="section">
  <h2>Rebuilding the site</h2>
  <p>The pages are generated from the model data, so the data is the source of truth and
  the HTML is disposable:</p>
  <pre><code>python3 build.py</code></pre>
  <p>Edit <span class="mono">data/capabilities.json</span>,
  <span class="mono">data/concepts.json</span> or
  <span class="mono">data/valuestreams.json</span> and re-run. No dependencies beyond the
  Python standard library.</p>
</section>
""" + foot()


# --------------------------------------------------------------------------- #
# Page: downloads
# --------------------------------------------------------------------------- #

DOWNLOADS = [
    ("business-analyst-services-ba-skills-bundle.json", "JSON",
     "Complete bundle",
     "The whole model in one file against ba-skills-bundle schema v1.0.0 — "
     "capabilities at all three levels, concepts, value streams, stages, outcomes, "
     "roles, metrics and information objects. This is the import file for VCC and the "
     "PlausibleBA canvas."),
    ("business_analyst_services_capability_map.xlsx", "XLSX",
     "Capability register",
     "Four tabs: the full level-3 register, a level-1 domain rollup, a level-2 rollup, "
     "and a read-me covering structure and provenance. The rollups are live formulas, "
     "so they follow any rows you add or remove."),
    ("business_analyst_services_concept_model.xlsx", "XLSX",
     "Object register",
     "Four tabs: objects with definitions and what each absorbs, all relationships, a "
     "formula-driven type summary, and a read-me. Inbound and outbound relationship "
     "counts are computed from the relationships tab."),
    ("business_analyst_services_value_stream_client_need_to_realised_benefit.xlsx", "XLSX",
     "Stage register — Client Need to Realised Benefit",
     "Four tabs: stages in sequence with entry and exit states, the stage-to-capability "
     "mapping one row per pair, candidate metrics, and a read-me."),
    ("business_analyst_services_value_stream_learner_interest_to_capability_applied.xlsx", "XLSX",
     "Stage register — Learner Interest to Capability Applied",
     "Same four-tab shape as the consulting stream register."),
]

SOURCE_DATA = [
    ("capabilities.json", "The capability map: domains, level-2 capabilities, and level-3 "
                          "capabilities with their business objects."),
    ("concepts.json", "The concept model: objects with type, definition and what each "
                      "consolidates, plus the relationship list."),
    ("valuestreams.json", "The value streams: roles, and each stream's stages with entry "
                          "and exit states, capability mappings, outcomes and metrics."),
    ("ba-skills-bundle.json", "The assembled bundle, as served to the pages."),
]


def page_downloads():
    def size(rel):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            return ""
        kb = os.path.getsize(p) / 1024
        return f"{kb:.0f} KB" if kb < 1024 else f"{kb / 1024:.1f} MB"

    items = "".join(
        f"""<li>
  <span class="fmt">{e(fmt)}</span>
  <div class="meta"><h3>{e(title)}</h3><p>{e(desc)}</p>
  <p style="color:var(--ink-3);font-size:12.5px;margin-top:6px">
  <span class="mono">{e(fn)}</span> · {e(size("downloads/" + fn))}</p></div>
  <a class="btn" href="downloads/{fn}" download>Download</a>
</li>"""
        for fn, fmt, title, desc in DOWNLOADS
    )
    data_rows = [
        [f'<a href="data/{fn}"><span class="mono">{e(fn)}</span></a>', e(desc),
         e(size("data/" + fn))]
        for fn, desc in SOURCE_DATA
    ]

    return head(
        "Downloads",
        "The model as a VCC import bundle, four spreadsheet registers, and the raw "
        "source data.",
        "downloads.html",
    ) + f"""
<div class="page-head">
  <p class="eyebrow">Take it with you</p>
  <h1>Downloads</h1>
  <p class="lede">Everything on this site is generated from the files below. The bundle
  is the import format; the workbooks are for reading and annotating; the raw JSON is for
  anyone who wants to fork the model and change it.</p>
</div>

<section class="section">
  <h2>Deliverables</h2>
  <ul class="dl">{items}</ul>
</section>

<section class="section">
  <h2>Loading the bundle</h2>
  <ul class="bullets">
    <li><strong><a href="https://www.plausibleba.com/canvas">PlausibleBA Canvas</a></strong>
    — upload the bundle JSON for the interactive visualisation.</li>
    <li><strong><a href="https://vcc.plausibleba.com">VCC</a></strong> — import the bundle
    for workshopping, enrichment and PPIT mapping.</li>
  </ul>
</section>

<section class="section">
  <h2>Source data</h2>
  <p>These three files are the model. The site is a rendering of them, and
  <span class="mono">build.py</span> is the renderer — edit the data, re-run the build,
  and every page and table follows.</p>
  <div class="tw"><table>
    <caption>Model data served alongside the site.</caption>
    <thead><tr><th scope="col">File</th><th scope="col">Contents</th>
    <th scope="col">Size</th></tr></thead>
    <tbody>{''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in data_rows)}</tbody>
  </table></div>
</section>

<section class="section">
  <h2>Reuse</h2>
  <p>The <strong>structure</strong> — seven domains, Party/Resource/Record, stages defined
  by entry and exit state — is the PlausibleBA method and is meant to be copied. The
  <strong>content</strong> describes one specific practice and will not fit yours; treat it
  as a worked example to argue with rather than a template to fill in.</p>
  <p>Model content is published under
  <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>; the build script
  is MIT. See <span class="mono">LICENSE</span> in the repository.</p>
</section>
""" + foot()


def page_404():
    return head("Page not found", "That page does not exist.", "", base=SITE_BASE) + """
<div class="page-head">
  <p class="eyebrow">404</p>
  <h1>That page does not exist</h1>
  <p class="lede">The link may be out of date, or the page may have been renamed when the
  site was rebuilt.</p>
</div>
<h2>Try one of these</h2>
<ul class="cards">
  <li class="card"><h3><a href="index.html">Overview</a></h3>
    <p>Start here — what the model is and what it argues.</p></li>
  <li class="card"><h3><a href="capability-map.html">Capability map</a></h3>
    <p>What the practice is able to do.</p></li>
  <li class="card"><h3><a href="concept-model.html">Concept model</a></h3>
    <p>What the practice manages.</p></li>
  <li class="card"><h3><a href="value-streams.html">Value streams</a></h3>
    <p>How value reaches a client and a learner.</p></li>
</ul>
""" + foot()


# --------------------------------------------------------------------------- #

def main():
    global SITE_BASE
    import argparse
    ap = argparse.ArgumentParser(description="Build the business architecture site.")
    ap.add_argument("--base", default=SITE_BASE,
                    help='Absolute site base path for 404.html, e.g. "/ba-architecture/". '
                         'Empty for a site served at the domain root.')
    SITE_BASE = ap.parse_args().base
    print(f"Building {ORG} business architecture site")
    if SITE_BASE:
        print(f"  404 base: {SITE_BASE}")
    write("index.html", page_index())
    write("capability-map.html", page_capability_map())
    write("concept-model.html", page_concept_model())
    write("value-streams.html", page_value_streams())
    write("method.html", page_method())
    write("downloads.html", page_downloads())
    write("404.html", page_404())
    print("Done.")


if __name__ == "__main__":
    main()
