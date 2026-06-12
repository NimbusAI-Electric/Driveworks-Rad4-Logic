"""Produce a focused per-CPN notes document containing only the four
categories the user asked for: SPECIFICATION, ATTENTION, DEFOGGER (incl.
DEFOGGER DISCLAIMER/KEEN), and DIMMING."""
import json
from collections import defaultdict
from pathlib import Path

IN_JSON = Path(r"C:\Users\devops\rad4_notes.json")
OUT_MD  = Path(r"C:\Users\devops\RAD4_Notes_SADD_by_CPN.md")  # Spec/Attn/Defog/Dim by CPN

CATEGORIES = ["SPECIFICATION", "ATTENTION", "DEFOGGER", "DEFOGGER DISCLAIMER (KEEN)", "DIMMING"]


def main():
    data = json.loads(IN_JSON.read_text(encoding="utf-8"))

    # Build cpn -> {category: [texts]}
    cpn_notes = defaultdict(lambda: defaultdict(list))
    for cat in CATEGORIES:
        for variant in data.get(cat, []):
            for cpn in variant["cpns"]:
                cpn_notes[cpn][cat].append(variant["text"])

    md = [
        "# RAD4 Sales Aids — Specification / Attention / Defogger / Dimming Notes by CPN",
        "",
        "Per-CPN dump of the four note categories from the RAD4 sales-aid PDFs:",
        "",
        "1. **SPECIFICATION** — installation prose",
        "2. **ATTENTION** — safety call-out (earth-ground, GFCI)",
        "3. **DEFOGGER** — defogger voltage / wattage block (includes `DEFOGGER:`, `DEFOGGER SPECIFICATION:`, `DEFOGGER SPECIFICATIONS:`, `DEFOGGER POWER REQUIREMENTS:`) and the **Keen / Defogger Disclaimer** sub-note when present",
        "4. **DIMMING** — `DIMMER COMPATIBILITY:` block (TRIAC vs 0-10V vs driver-specific)",
        "",
        f"**{len(cpn_notes)} CPNs** with at least one of the four notes are listed below, sorted alphabetically.",
        "",
        "Source: 381 RAD4 sales-aid PDFs in `D:\\EM-HV-04 Backup 5-14-2026\\Sales Aids\\`.",
        "",
        "---",
        "",
    ]

    # Quick alphabetical index
    md.append("## Index of CPNs")
    md.append("")
    md.append("<details><summary>Click to expand the CPN index</summary>")
    md.append("")
    for cpn in sorted(cpn_notes):
        anchor = cpn.lower().replace(".", "").replace("-", "-")
        md.append(f"- [`{cpn}`](#{anchor})")
    md.append("")
    md.append("</details>")
    md.append("")
    md.append("---")
    md.append("")

    # Per-CPN sections
    for cpn in sorted(cpn_notes):
        md.append(f"## `{cpn}`")
        md.append("")

        for cat in CATEGORIES:
            texts = cpn_notes[cpn].get(cat)
            if not texts:
                continue
            # de-dupe in case the same variant got attached twice (e.g. multi-rev PDFs)
            for txt in dict.fromkeys(texts):
                # display header — combine DEFOGGER + KEEN disclaimer under a single "DEFOGGER" group visually
                if cat == "DEFOGGER DISCLAIMER (KEEN)":
                    label = "DEFOGGER (Keen Disclaimer)"
                else:
                    label = cat
                md.append(f"**{label}:**")
                md.append("")
                md.append(f"> {txt}")
                md.append("")

        md.append("---")
        md.append("")

    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    print(f"  CPNs covered: {len(cpn_notes)}")
    # quick per-cat coverage
    for cat in CATEGORIES:
        n = sum(1 for c in cpn_notes if cat in cpn_notes[c])
        print(f"  CPNs with {cat:30s} = {n}")


if __name__ == "__main__":
    main()
