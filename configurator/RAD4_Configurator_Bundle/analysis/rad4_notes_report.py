"""Render the notes JSON to a navigable markdown report and a per-CPN cross-reference."""
import json
from pathlib import Path
from collections import defaultdict

IN_JSON  = Path(r"C:\Users\devops\rad4_notes.json")
OUT_MD   = Path(r"C:\Users\devops\RAD4_Notes_Map.md")
OUT_XREF = Path(r"C:\Users\devops\RAD4_Notes_by_CPN.md")

USER_PRIMARY = ["SPECIFICATION", "ATTENTION", "DEFOGGER", "DEFOGGER DISCLAIMER (KEEN)", "DIMMING"]
OTHER_CATS   = ["CLOCK", "WALL GLOW", "PRODUCT USES", "POWER BOX REFERENCE",
                "INNER FRAME FINISH", "FRAME LED SPEC", "DFX CALLOUT",
                "KG2 CALLOUT", "CSTM CALLOUT", "LIGHTING POWER NOTE", "MISC NOTE"]


def fmt_cpns(cpns, sample=20):
    if len(cpns) <= sample:
        return "\n".join(f"- `{c}`" for c in cpns)
    head = "\n".join(f"- `{c}`" for c in cpns[:sample])
    return head + f"\n- *…and {len(cpns)-sample} more (full list in `rad4_notes.json`)*"


def write_category(md, cat, variants, intro=""):
    md.append(f"## {cat}")
    md.append("")
    if intro:
        md.append(intro)
        md.append("")
    total_cpns = sum(v["cpn_count"] for v in variants)
    md.append(f"**{len(variants)} distinct text variant(s) across {total_cpns} CPN occurrence(s).**")
    md.append("")
    for i, v in enumerate(variants, 1):
        md.append(f"### {cat} — Variant {i} (used in {v['cpn_count']} CPN{'s' if v['cpn_count']!=1 else ''})")
        md.append("")
        md.append(f"*Original header in PDF: `{v['original_header']}:`*")
        md.append("")
        md.append("> " + v["text"].replace("\n", "\n> "))
        md.append("")
        if v.get("alt_texts"):
            md.append(f"<sub>{len(v['alt_texts'])} near-duplicate text variant(s) (punctuation / typo differences) merged into this variant.</sub>")
            md.append("")
        md.append("**CPNs using this variant:**")
        md.append("")
        md.append(fmt_cpns(v["cpns"]))
        md.append("")
        md.append("---")
        md.append("")


def main():
    data = json.loads(IN_JSON.read_text(encoding="utf-8"))

    md = [
        "# RAD4 Sales-Aid Notes → CPN Mapping",
        "",
        "Each note in the RAD4 sales-aid PDFs (SPECIFICATION / ATTENTION / DEFOGGER / "
        "DIMMING / other) has been extracted, fuzzily clustered to remove punctuation- and "
        "typo-level duplicates, and mapped back to the **top-level CPN** that uses it.",
        "",
        "**Source:** `D:\\EM-HV-04 Backup 5-14-2026\\Sales Aids\\` — 381 RAD4 sales-aid PDFs",
        "",
        "**Companion files:**",
        "- [`RAD4_Specifications_Map.md`](RAD4_Specifications_Map.md) — numeric specs per CPN",
        "- [`RAD4_Code_Key.md`](RAD4_Code_Key.md) — CPN token decoder",
        "- [`RAD4_Notes_by_CPN.md`](RAD4_Notes_by_CPN.md) — reverse view: every note that appears on a given CPN",
        "- [`rad4_notes.json`](rad4_notes.json) — full machine-readable dataset (every CPN list, every variant)",
        "",
        "## Quick index",
        "",
        "| Category | Variants | Total CPN occurrences |",
        "|----------|---------:|---------------------:|",
    ]
    for cat in USER_PRIMARY + OTHER_CATS:
        if cat in data:
            n_v = len(data[cat])
            n_c = sum(v["cpn_count"] for v in data[cat])
            md.append(f"| [{cat}](#{cat.lower().replace(' ', '-').replace('/', '').replace('(', '').replace(')', '')}) | {n_v} | {n_c} |")
    md.append("")

    # === Section 1: user-requested categories ===
    md.append("# 1. Categories you asked about")
    md.append("")

    intros = {
        "SPECIFICATION": "The **SPECIFICATION** block is the installation prose on page 1 of every sales aid. "
                         "Variants differ by cable type (MC vs plain), whip length (15\" / 18\" / 30\" / 36\"), "
                         "whether 0-10V or low-voltage control wires are called out, and whether mounting is "
                         "described as \"fixture\", \"driver enclosure\", or \"mirror\".",
        "ATTENTION":     "**ATTENTION** is the safety call-out. The main variant is the NEC 250.20(B) earth-ground requirement. "
                         "A small number of CPNs use a longer cord-connected / GFCI variant.",
        "DEFOGGER":      "Defogger-related blocks come from headers `DEFOGGER:`, `DEFOGGER SPECIFICATION:`, "
                         "`DEFOGGER SPECIFICATIONS:`, and `DEFOGGER POWER REQUIREMENTS:`. They give the heater wattage / voltage.",
        "DEFOGGER DISCLAIMER (KEEN)": "Shown when a fixture has both Keen 1-Touch control and a defogger — "
                         "reminds the installer that Keen controls the lighting only and the defogger needs its own switch.",
        "DIMMING":       "The **DIMMER COMPATIBILITY** block tells the integrator which dimmer family the fixture's "
                         "driver expects (forward-phase TRIAC vs 0-10V) and disclaims compatibility responsibility.",
    }
    for cat in USER_PRIMARY:
        if cat in data:
            write_category(md, cat, data[cat], intros.get(cat, ""))

    # === Section 2: other notes ===
    md.append("# 2. Other notes found in the sales aids")
    md.append("")
    md.append("These are additional prose blocks the PDFs use besides the four categories above.")
    md.append("")
    for cat in OTHER_CATS:
        if cat in data:
            write_category(md, cat, data[cat])

    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {OUT_MD}")

    # === reverse view: per-CPN list of notes ===
    cpn_notes = defaultdict(dict)   # cpn -> {category: text}
    for cat, variants in data.items():
        for v in variants:
            for cpn in v["cpns"]:
                cpn_notes[cpn].setdefault(cat, []).append(v["text"])

    xref = ["# RAD4 — Which Notes Appear on Which CPN", "",
            "Reverse view: for each CPN, the notes its sales-aid PDF contains.",
            "Companion: [`RAD4_Notes_Map.md`](RAD4_Notes_Map.md)", ""]
    for cpn in sorted(cpn_notes):
        xref.append(f"## `{cpn}`")
        xref.append("")
        for cat in USER_PRIMARY + OTHER_CATS:
            if cat in cpn_notes[cpn]:
                for txt in cpn_notes[cpn][cat]:
                    xref.append(f"**{cat}:** {txt}")
                    xref.append("")
        xref.append("---")
        xref.append("")
    OUT_XREF.write_text("\n".join(xref), encoding="utf-8")
    print(f"Wrote {OUT_XREF}")

    # console summary
    print()
    print("Per-category variant summary:")
    for cat in USER_PRIMARY + OTHER_CATS:
        if cat in data:
            v = len(data[cat])
            c = sum(x['cpn_count'] for x in data[cat])
            print(f"  {cat:30s} {v:>2} variants / {c:>3} CPN occurrences")


if __name__ == "__main__":
    main()
