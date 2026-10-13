# Business Analyst Services — Business Architecture

The business architecture of a business analysis practice, modelled with its own
method and published whole.

**Live site:** https://business-analyst-services.github.io/ba-architecture/

Three artefacts, produced in one PlausibleBA session on 15 September 2026:

| Artefact | Shape |
| --- | --- |
| Capability map | 7 domains, 30 level-2, **81 level-3** capabilities |
| Concept model | **22 objects** (6 Party, 6 Resource, 10 Record), 35 relationships |
| Value streams | **2 streams, 11 stages**, 67 of 81 capabilities mapped |

## What it argues

Both value streams terminate in the same object. Consulting delivery ends at
*Realise & Reinvest*; a training cohort ends at *Sustain & Improve*. Each exits
into **Outcome & Insight**, which feeds back into **IP Asset** and **Course** —
the two resources the next engagement and the next cohort are built from.

That loop is the difference between a practice that sells hours and one that
compounds, and the model makes it explicit so it can be measured.

## What is incomplete

14 of the 81 capabilities sit outside both value streams. Most are genuinely
enabling, but two clusters are not: **manuscript authoring, editorial review and
publishing**, and **product backlog management, software development and
automated testing**. A third stream — *IP to Published Asset* — would likely
absorb all six. It is not modelled here.

Other limitations are listed on the [method page](method.html): the content is
self-reported from a single session, the metrics are proposed rather than
baselined, and capability maturity and ownership are not modelled at all.

## Repository layout

```
.
├── build.py                 the site generator — no dependencies
├── data/                    the model; this is the source of truth
│   ├── site.json            repo name, base path, last-updated date
│   ├── capabilities.json    domains, L2, L3 with business objects
│   ├── concepts.json        objects with type and definition, relationships
│   ├── valuestreams.json    roles, streams, stages, metrics
│   └── ba-skills-bundle.json  the assembled VCC bundle
├── downloads/               bundle JSON + four 4-tab XLSX registers
├── assets/css/site.css      design system, light and dark
├── assets/js/site.js        theme toggle and figure tooltips
├── *.html                   generated — do not hand-edit
└── .github/workflows/pages.yml   deploys on push to main
```

## Building

```bash
python3 build.py
```

Python standard library only — no `pip install`, no Node, no bundler. The HTML
is generated and disposable: to change the model, edit the JSON in `data/` and
re-run.

`data/site.json` holds the site's own settings: the repo name, the base path
`404.html` needs to resolve assets from any depth, and `updated` — the date
shown in the footer. That date is a committed value rather than the clock on
purpose: the Pages workflow rebuilds and fails if the generated HTML differs
from what is committed, so a `date.today()` footer would break the check the
day after any commit. Bump `updated` by hand when the model changes.

Override the base for a one-off build with `--base /some-path/`.

## Accessibility

Built to WCAG 2.1 AA and verified, not assumed:

- Every figure has a text description and an equivalent table view.
- Every interactive mark in the SVG figures is keyboard-focusable with its own
  accessible label; focus is always visible.
- No reading of any figure depends on distinguishing two colours — marks carry
  direct labels, legends are always present, and objects are grouped in labelled
  bands by type.
- The categorical palette was validated by script for colour-blind separation
  and surface contrast in both light and dark modes. The raw brand hexes fail
  that check and are used for chrome only; see the method page for the note.
- Dark mode is a selected palette stepped for the dark surface, not an inversion.
- `prefers-reduced-motion`, `forced-colors` and print are all handled.

## Licence

Model content — the capability map, concept model and value streams — is
published under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
`build.py`, `site.css` and `site.js` are MIT. See [LICENSE](LICENSE).

The method is the [PlausibleBA](https://www.plausibleba.com) skills library.

---

[Business Analyst Services](https://business-analyst.services) is a business
analysis consulting, training and advisory practice in Sydney, Australia.
