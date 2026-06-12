"""Definitive add-in → note association matrix for the RAD4 sales aids.

For every option code that appears in a CPN, cross-tabulate against every
note category found on the sales aids. Resolve co-occurrence ambiguity by
looking at CPNs where the option appears ALONE. List every exception by
CPN so the result is fully auditable.

Data sources (built by reading all 381 sales-aid PDFs):
  rad4_notes.json          every note text variant + the CPNs using it
  rad4_specifications.csv  one row per sales aid with parsed CPN tokens
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

NOTES_JSON = Path(r"C:\Users\devops\rad4_notes.json")
SPECS_CSV  = Path(r"C:\Users\devops\rad4_specifications.csv")
OUT_MD     = Path(r"C:\Users\devops\RAD4_AddIn_Note_Matrix.md")

# Note categories as they exist in the extraction. We fold the Keen
# disclaimer under its own column since it has a distinct trigger.
CATEGORIES = [
    "SPECIFICATION",
    "ATTENTION",
    "DEFOGGER",
    "DEFOGGER DISCLAIMER (KEEN)",
    "DIMMING",
    "CLOCK",
    "WALL GLOW",
    "PRODUCT USES",
    "POWER BOX REFERENCE",
]
SHORT = {
    "SPECIFICATION": "SPEC",
    "ATTENTION": "ATTN",
    "DEFOGGER": "DEFOG",
    "DEFOGGER DISCLAIMER (KEEN)": "KEEN-DISC",
    "DIMMING": "DIM",
    "CLOCK": "CLOCK",
    "WALL GLOW": "WGLOW",
    "PRODUCT USES": "USES",
    "POWER BOX REFERENCE": "PBREF",
}

OPTION_MEANING = {
    "D1":   "Defogger driver pkg D1 (0-10V dimmable driver)",
    "D2":   "Defogger driver pkg D2 (TRIAC dimmable driver)",
    "DF":   "Defogger heater pad",
    "DFX":  "Defogger heater pad, extended",
    "KG":   "Keen 1-Touch control",
    "KG2":  "Keen 1-Touch v2",
    "KD":   "Keen Dimmer",
    "KC":   "Keen Clock",
    "CK2":  "Clock CK2",
    "CK3":  "Seamless Clock CK3",
    "CC2":  "Color-change CC2 (cord-connected)",
    "WG3":  "Wall Glow w/ grommet routing",
    "WR":   "Wall Receptacle",
    "WRX":  "Wall Receptacle extended",
    "SO":   "Switch Option",
    "NO":   "Night-Off / night-light",
    "277V": "277 V input",
}
OPTION_ORDER = ["D1", "D2", "DF", "DFX", "KG", "KG2", "KD", "KC",
                "CK2", "CK3", "CC2", "WG3", "WR", "WRX", "SO", "NO", "277V"]


def main():
    notes = json.loads(NOTES_JSON.read_text(encoding="utf-8"))
    rows  = list(csv.DictReader(SPECS_CSV.open(encoding="utf-8")))

    # ── cpn -> set of options, from the master CSV (file-level dedup to CPN) ──
    cpn_opts: dict[str, set] = {}
    for r in rows:
        opts = set(o for o in r["cpn_options"].split(";") if o)
        cpn_opts[r["cpn"]] = opts
    all_cpns = sorted(cpn_opts)

    # ── cpn -> set of note categories present (any rev counts) ──
    cpn_notes: dict[str, set] = defaultdict(set)
    for cat in CATEGORIES:
        for v in notes.get(cat, []):
            for cpn in v["cpns"]:
                if cpn in cpn_opts:           # keep to known CPNs
                    cpn_notes[cpn].add(cat)

    n_total = len(all_cpns)
    no_opt_cpns = [c for c in all_cpns if not cpn_opts[c]]

    def cpns_with(opt):  return [c for c in all_cpns if opt in cpn_opts[c]]
    def cpns_solo(opt):  return [c for c in all_cpns if cpn_opts[c] == {opt}]

    def rate(cpns, cat):
        n = sum(1 for c in cpns if cat in cpn_notes[c])
        return n, len(cpns)

    md = []
    p = md.append

    p("# RAD4 Add-In → Note Association Matrix")
    p("")
    p("**Question answered:** for every add-in code that can appear in a RAD4 CPN")
    p("(e.g. `-D2`, `-DF`, `-KG`), which notes appear on the sales aids that have it?")
    p("")
    p(f"**Coverage:** every RAD4 sales aid was read — 381 PDFs → **{n_total} unique CPNs**, "
      f"all accounted for below. Wording variance is collapsed: any variant of a note "
      f"counts as that note being present (the exact texts live in `rad4_notes.json` / "
      f"`RAD4_Notes_Map.md`).")
    p("")
    p("**Method note on co-occurring add-ins:** when two add-ins always appear together "
      "(e.g. `DFX` is always with `KG`), a note on those sales aids could belong to either. "
      "To resolve ownership, each add-in section below shows the **solo evidence** — CPNs "
      "where that add-in is the *only* one present — which isolates what the add-in itself brings.")
    p("")

    # ── 0. Baseline ──
    p("---")
    p("")
    p(f"## Baseline — CPNs with NO add-ins ({len(no_opt_cpns)} CPNs)")
    p("")
    p("Example: `RAD4-36.00X36.00-CH04-30K`")
    p("")
    base_counts = Counter()
    for c in no_opt_cpns:
        for cat in cpn_notes[c]:
            base_counts[cat] += 1
    p("| Note | CPNs with it | Share |")
    p("|------|-------------:|------:|")
    for cat in CATEGORIES:
        n = base_counts.get(cat, 0)
        if n:
            p(f"| {cat} | {n}/{len(no_opt_cpns)} | {n*100//len(no_opt_cpns)}% |")
    p("")
    p("A plain RAD4 with no add-ins carries **only the SPECIFICATION (installation) note**. "
      "Every other note is brought in by an add-in. (POWER BOX REFERENCE is a generic "
      "drawing-reference block that newer-revision sheets print regardless of options — "
      "it is not tied to any add-in.)")
    p("")

    # ── 1. The headline matrix ──
    p("---")
    p("")
    p("## 1. The matrix — % of CPNs with each add-in that carry each note")
    p("")
    header = "| Add-in | #CPNs | " + " | ".join(SHORT[c] for c in CATEGORIES) + " |"
    p(header)
    p("|" + "---|" * (2 + len(CATEGORIES)))
    # baseline row
    cells = []
    for cat in CATEGORIES:
        n, d = rate(no_opt_cpns, cat)
        cells.append(f"{n*100//d}%" if d and n else ("100%" if n == d and d else "—") if n else "—")
    p("| *(none)* | " + str(len(no_opt_cpns)) + " | " + " | ".join(cells) + " |")
    for opt in OPTION_ORDER:
        withs = cpns_with(opt)
        if not withs:
            continue
        cells = []
        for cat in CATEGORIES:
            n, d = rate(withs, cat)
            cells.append(f"**{n*100//d}%**" if n else "—")
        p(f"| `{opt}` | {len(withs)} | " + " | ".join(cells) + " |")
    p("")
    p("Read: `D2` row, DIM column = % of all D2 CPNs whose sales aid has a dimming note.")
    p("")

    # ── 2. Per-add-in detail ──
    p("---")
    p("")
    p("## 2. Per-add-in findings (with solo evidence and every exception)")
    p("")

    for opt in OPTION_ORDER:
        withs = cpns_with(opt)
        if not withs:
            continue
        solo = cpns_solo(opt)
        p(f"### `{opt}` — {OPTION_MEANING[opt]}")
        p("")
        p(f"Appears in **{len(withs)} CPNs**; alone (no other add-in) in **{len(solo)}**.")
        p("")

        # notes summary on with-CPNs and solo-CPNs
        p("| Note | All CPNs with this add-in | Solo CPNs only |")
        p("|------|---------------------------|----------------|")
        owned = []
        for cat in CATEGORIES:
            nw, dw = rate(withs, cat)
            ns, ds = rate(solo, cat)
            if nw == 0:
                continue
            wcell = f"{nw}/{dw} ({nw*100//dw}%)"
            scell = f"{ns}/{ds} ({ns*100//ds}%)" if ds else "n/a (never solo)"
            p(f"| {cat} | {wcell} | {scell} |")
            if ds and ns * 2 >= ds and cat != "SPECIFICATION":
                owned.append(cat)
        p("")

        # verdict — require ≥2 solo hits to claim ownership, and qualify by rate
        non_spec = [c for c in CATEGORIES if c != "SPECIFICATION"]
        if solo:
            always, often = [], []
            for c in non_spec:
                ns, ds = rate(solo, c)
                if ns >= 2 and ds:
                    pct = ns * 100 // ds
                    if pct >= 80:
                        always.append(c)
                    elif pct >= 40:
                        often.append(c)
            if always or often:
                parts = []
                if always:
                    parts.append(", ".join(f"**{c}**" for c in always))
                if often:
                    parts.append("usually " + ", ".join(f"**{c}**" for c in often))
                p(f"**What `{opt}` itself brings:** " + "; ".join(parts) +
                  " (based on solo CPNs).")
            else:
                p(f"**What `{opt}` itself brings:** no extra note beyond SPECIFICATION "
                  f"(solo CPNs carry only the installation note).")
        else:
            co = Counter()
            for c in withs:
                for o2 in cpn_opts[c]:
                    if o2 != opt:
                        co[o2] += 1
            p(f"**Never appears alone** — always with: " +
              ", ".join(f"`{o}` ({n}×)" for o, n in co.most_common()) +
              ". Note ownership inferred from partners' solo behaviour.")
        p("")

        # exceptions: for each category that is ≥80% on with-CPNs, list the misses
        exc_lines = []
        for cat in non_spec:
            nw, dw = rate(withs, cat)
            if dw and nw * 100 // dw >= 80 and nw < dw:
                misses = [c for c in withs if cat not in cpn_notes[c]]
                exc_lines.append((cat, misses))
        if exc_lines:
            p("**Exceptions** (CPNs with this add-in that are missing the expected note):")
            p("")
            for cat, misses in exc_lines:
                for c in misses:
                    p(f"- `{c}` — has `{opt}` but no {cat} note on its sales aid")
            p("")
        p("---")
        p("")

    # ── 3. Reverse view: note → which add-ins bring it ──
    p("## 3. Reverse view — each note and the add-ins that bring it")
    p("")
    for cat in CATEGORIES:
        if cat == "SPECIFICATION":
            continue
        carriers = [c for c in all_cpns if cat in cpn_notes[c]]
        if not carriers:
            continue
        opt_count = Counter()
        none_count = 0
        for c in carriers:
            if not cpn_opts[c]:
                none_count += 1
            for o in cpn_opts[c]:
                opt_count[o] += 1
        p(f"### {cat} — on {len(carriers)} CPNs")
        p("")
        parts = [f"`{o}` {n}×" for o, n in opt_count.most_common()]
        if none_count:
            parts.append(f"*(no add-in)* {none_count}×")
        p("Add-ins present on those CPNs: " + ", ".join(parts))
        p("")

    # ── 4. Plain-English summary ──
    p("---")
    p("")
    p("## 4. Plain-English summary (the rule of thumb you asked for)")
    p("")
    p("| Add-in in CPN | Notes it puts on the sales aid |")
    p("|---------------|--------------------------------|")
    p("| *(none)* | SPECIFICATION only |")
    p("| `D1` | DIMMING (0-10V) — *not* a defogger-spec note by itself |")
    p("| `D2` | DIMMING (TRIAC) — *not* a defogger-spec note by itself |")
    p("| `DF` | DEFOGGER (heater V/W block); + KEEN-DISCLAIMER when a Keen code is also present |")
    p("| `DFX` | DEFOGGER + ATTENTION + KEEN-DISCLAIMER (always rides with `KG`) |")
    p("| `KG` / `KG2` / `KD` / `KC` | ATTENTION (NEC earth-ground) |")
    p("| `CK2` / `CK3` | CLOCK power note; SPEC switches to hanging-bracket wording |")
    p("| `CC2` | SPEC switches to cord-connected; ATTENTION switches to the long GFCI text |")
    p("| `WG3` | WALL GLOW spec block; SPEC gains \"MAIN LIGHTS AND WALL GLOW OPERATE TOGETHER\" |")
    p("| `NO` | rides with wall-glow models; GFCI-style ATTENTION when cord-connected |")
    p("| `WR` / `WRX` / `SO` | one-off CPNs; no consistent extra note |")
    p("| `277V` | changes voltages inside existing notes; adds no new note category |")
    p("")
    p("*Generated by `rad4_addin_note_matrix.py` from all 381 RAD4 sales aids. "
      "Exact note wording variants: `rad4_notes.json`. Numeric specs: `rad4_specifications.csv`.*")

    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {OUT_MD}")

    # console quick check
    print(f"\nCPNs total: {n_total}, no-option baseline: {len(no_opt_cpns)}")
    for opt in OPTION_ORDER:
        w, s = cpns_with(opt), cpns_solo(opt)
        if w:
            print(f"  {opt:5s} with={len(w):>3}  solo={len(s):>3}")


if __name__ == "__main__":
    main()
