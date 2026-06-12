# RAD4 Configurator Bundle

Everything needed to build a RAD4 sales-aid drawing configurator, derived
from automated analysis of **381 real RAD4 sales-aid PDFs** (372 unique
CPNs).

Copy this whole folder into your Antigravity environment. It is
**self-contained and portable** — the Python code locates its data files
relative to its own folder, so nothing is tied to the original machine.

---

## Quick start

1. **For a human:** read `1_START_HERE/` in order:
   1. `RAD4_Configurator_Pack.md` — the master briefing
   2. `RAD4_Note_Selection_Rules.md` — which notes go on the drawing
   3. `RAD4_Drawing_Scale_Rule.md` — what scale each page uses

2. **For an AI agent:** paste `ANTIGRAVITY_PROMPT.md` into the agent and
   attach the files it references (all included here).

3. **To run the code:**
   ```
   cd code
   python rad4_rules_engine.py      # demo: notes for sample CPNs
   python rad4_scale_dynamic.py     # demo: scales for sample CPNs
   python rad4_rules_validate.py    # validate note rules vs catalog
   python rad4_scale_dynamic.py validate   # validate scale model
   ```
   Requires Python 3.10+. No third-party packages needed to *run* the
   rule engines (only `pypdf` is needed to re-extract from PDFs, which
   you don't need to do).

---

## What's in here

```
RAD4_Configurator_Bundle/
├── README.md                  ← you are here
├── ANTIGRAVITY_PROMPT.md      ← ready-to-paste prompt for the agent
│
├── 1_START_HERE/              ← the 3 documents that matter most
│   ├── RAD4_Configurator_Pack.md      master briefing: CPN grammar, form
│   │                                  inputs, outputs, BOM, open items
│   ├── RAD4_Note_Selection_Rules.md   rules + DriveWorks formulas +
│   │                                  validation for the 5 note types
│   └── RAD4_Drawing_Scale_Rule.md     dynamic page-1/page-2 scale model
│
├── data/                      ← machine-readable ground truth
│   ├── rad4_specifications.csv        381 rows, one per sales aid,
│   │                                  all numeric specs + parsed CPN
│   ├── rad4_specifications.json       same as JSON
│   ├── rad4_notes.json                every note text variant + the
│   │                                  CPN list that uses it
│   └── rad4_scales.csv                page-1 / page-2 scale per PDF
│
├── code/                      ← runnable, portable rule engines
│   ├── rad4_rules_engine.py           select_notes(cpn) -> dict
│   ├── rad4_scale_dynamic.py          scales_for_cpn(cpn) -> dict
│   ├── rad4_rules_validate.py         note-rule accuracy report
│   └── rad4_scale_tune.py             grid-search scale parameters
│
├── docs/                      ← supporting reference documents
│   ├── RAD4_Code_Key.md               decoder for every CPN token
│   ├── RAD4_Specifications_Map.md     human-readable spec tables
│   ├── RAD4_Notes_Map.md              note variants by category
│   ├── RAD4_Notes_by_CPN.md           every note on each CPN (all cats)
│   ├── RAD4_Notes_SADD_by_CPN.md      per-CPN, 4 main note categories
│   ├── RAD4_Notes_by_Option.md        notes consolidated per option code
│   └── RAD4_AddIn_Note_Matrix.md      add-in → note association matrix
│                                      (which add-in brings which note,
│                                      with solo-CPN evidence + exceptions)
│
├── sample_pdfs/               ← 10 real sales aids, one per note pattern
│   └── README.md                      key: which PDF demonstrates what
│                                      (visual format ground truth)
│
└── analysis/                  ← provenance: how the rules were derived
    ├── rad4_extract*.py / rad4_*_report.py / rad4_*_analysis.py …
    │                                  the extraction & analysis scripts
    └── *_validation.txt / *_analysis.txt
                                       the validation & correlation reports
```

---

## Key results

### CPN structure
```
RAD4 - [CSTM-|FRX-] [<id>-] <W>X<H> - <FINISH> [-<OPT>…] - <CCT>
e.g.  RAD4-72.00X42.00-BR02-CK3-DF-KG-30K
```
Finish codes (`BK05`, `CH04`, …) do **not** affect notes or scale.
Only `W`, `H`, and the option codes (`D1 D2 DF DFX KG KG2 KD KC CK2 CK3
CC2 WG3 WR WRX SO NO 277V`) do.

### Note-selection accuracy (vs 372 catalog CPNs)
| Note | Presence | Variant choice |
|------|---------:|---------------:|
| SPECIFICATION | 100 % | always present |
| ATTENTION | 98 % | 100 % (NEC vs GFCI) |
| DEFOGGER | 100 % | 100 % wattage |
| DEFOGGER DISCLAIMER (KEEN) | 100 % | single text |
| DIMMING | 97 % | 99 % (TRIAC vs 0-10V) |

### Drawing-scale accuracy (vs 381 catalog PDFs)
| | Exact | Within ±1 step |
|---|---:|---:|
| Page 1 | 63 % | 98 % |
| Page 2 | 62 % | 97 % |
The model is conservative — when it differs it picks a *smaller* drawing
(larger N), so the layout never overflows.

---

## How the code finds its data (portability)

`code/rad4_rules_engine.py` defines `_find_data(filename)`, which searches:
1. `../data/<filename>` relative to the script  ← the bundle layout
2. the script's own directory
3. the original authoring path (fallback)

All other code imports `_find_data`, so the whole bundle works wherever
you put it. If you move `data/` elsewhere, pass explicit paths to
`CatalogLookup(notes_json=…, specs_csv=…)` or `validate(scales_csv=…)`.

---

## Open items (NOT derivable from the sales aids — need an SME)

1. SolidWorks geometry rules (which dims/equations drive W × H)
2. Title-block custom-property field names on the RAD4 template
3. Vault paths for RAD4 master assemblies / frame components
4. Pricing
5. Lead times

See `1_START_HERE/RAD4_Configurator_Pack.md` §10 for detail.

---

*Bundle generated 2026-06-04 from automated analysis of 381 RAD4
sales-aid PDFs in `D:\EM-HV-04 Backup 5-14-2026\Sales Aids\`.*
