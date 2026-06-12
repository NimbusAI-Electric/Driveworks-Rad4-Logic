"""For each CPN option code (excluding finish codes), show the most common
note variants from the four categories the user cares about."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

NOTES_JSON  = Path(r"C:\Users\devops\rad4_notes.json")
SPECS_CSV   = Path(r"C:\Users\devops\rad4_specifications.csv")
OUT_MD      = Path(r"C:\Users\devops\RAD4_Notes_by_Option.md")

# The four note groups the user wants
CATEGORIES = ["SPECIFICATION", "ATTENTION", "DEFOGGER", "DEFOGGER DISCLAIMER (KEEN)", "DIMMING"]

OPTION_META = {
    "D1":   ("Defogger D1",              "Defogger"),
    "D2":   ("Defogger D2",              "Defogger"),
    "DF":   ("Defogger DF",              "Defogger"),
    "DFX":  ("Defogger DFX (Extended)",  "Defogger"),
    "KG":   ("Keen 1-Touch Control",     "Keen / Control"),
    "KG2":  ("Keen 1-Touch v2",          "Keen / Control"),
    "KD":   ("Keen Dimmer",              "Keen / Control"),
    "KC":   ("Keen Clock",               "Keen / Control"),
    "CK2":  ("Clock CK2",                "Clock"),
    "CK3":  ("Seamless Clock CK3",       "Clock"),
    "CC2":  ("Color-Change CC2",         "Color"),
    "WG3":  ("Wall-Grommet routing",     "Wiring / Install"),
    "WR":   ("Wall Receptacle",          "Wiring / Install"),
    "WRX":  ("Wall Receptacle Extended", "Wiring / Install"),
    "SO":   ("Switch Option",            "Misc"),
    "NO":   ("Night-Light / Night-Off",  "Misc"),
    "277V": ("277 V Input",              "Power"),
}

DISPLAY_ORDER = [
    "D1", "D2", "DF", "DFX",
    "KG", "KG2", "KD", "KC",
    "CK2", "CK3", "CC2",
    "WG3", "WR", "WRX",
    "SO", "NO", "277V",
]


def main():
    notes = json.loads(NOTES_JSON.read_text(encoding="utf-8"))

    # Build cpn -> set of options (from the master CSV)
    cpn_opts = {}
    rows = list(csv.DictReader(SPECS_CSV.open(encoding="utf-8")))
    for r in rows:
        opts = set(o for o in r["cpn_options"].split(";") if o)
        cpn_opts[r["cpn"]] = opts

    # invert notes: cpn -> {cat: [variant_index]}
    # and: variant_text lookup
    variant_text = {}        # (cat, idx) -> text
    cpn_variants = defaultdict(lambda: defaultdict(set))   # cpn -> cat -> set(variant_idx)
    for cat in CATEGORIES:
        for idx, v in enumerate(notes.get(cat, [])):
            variant_text[(cat, idx)] = v["text"]
            for cpn in v["cpns"]:
                cpn_variants[cpn][cat].add(idx)

    # All CPNs from the master CSV
    all_cpns = sorted(cpn_opts)

    # For each option: collect CPNs that have it
    opt_cpns = {opt: [c for c in all_cpns if opt in cpn_opts.get(c, set())]
                for opt in DISPLAY_ORDER}

    # === build markdown ===
    md = [
        "# RAD4 Notes Consolidated by CPN Option Code",
        "",
        "For each option suffix in the CPN (excluding the 4-character finish "
        "codes such as `BR02` or `CH04`), this document lists the most common "
        "**Specification / Attention / Defogger / Dimming** notes that appear "
        "on the sales aids whose CPN includes that option.",
        "",
        "Counts shown after each variant are the number of **CPNs with this option** "
        "that carry that particular note variant. For comparison, the parenthetical "
        "next to each option header (`N CPNs`) is the total number of CPNs that "
        "include the option.",
        "",
        "Source: 381 RAD4 sales-aid PDFs in `D:\\EM-HV-04 Backup 5-14-2026\\Sales Aids\\`.",
        "",
        "---",
        "",
        "## Quick-reference matrix",
        "",
        "| Option | Meaning | # CPNs | Dominant SPECIFICATION note |",
        "|--------|---------|-------:|-----------------------------|",
    ]

    for opt in DISPLAY_ORDER:
        cpns = opt_cpns[opt]
        if not cpns:
            continue
        # find the dominant SPEC variant for this option
        spec_counter = Counter()
        for c in cpns:
            for idx in cpn_variants[c].get("SPECIFICATION", []):
                spec_counter[idx] += 1
        top_spec_text = ""
        if spec_counter:
            top_idx, top_n = spec_counter.most_common(1)[0]
            top_spec_text = f"{top_n}/{len(cpns)}: " + variant_text[("SPECIFICATION", top_idx)][:90] + "…"
        meaning, _ = OPTION_META[opt]
        md.append(f"| `{opt}` | {meaning} | {len(cpns)} | {top_spec_text} |")

    md.append("")
    md.append("---")
    md.append("")

    # === TL;DR: dominant note per option per category ===
    md.append("## TL;DR — dominant note per option, by category")
    md.append("")
    md.append("For each option, the single most common variant in each of the four "
              "note categories. *(\"55/104\" means 55 out of the 104 CPNs that include "
              "this option carry that exact note text.)*")
    md.append("")

    for opt in DISPLAY_ORDER:
        cpns = opt_cpns[opt]
        if not cpns:
            continue
        meaning, family = OPTION_META[opt]
        md.append(f"### `{opt}` — {meaning}")
        md.append("")
        md.append(f"Observed on **{len(cpns)} CPNs**. Family: *{family}*.")
        md.append("")
        for cat in CATEGORIES:
            counter = Counter()
            for c in cpns:
                for idx in cpn_variants[c].get(cat, []):
                    counter[idx] += 1
            if not counter:
                continue
            top_idx, top_n = counter.most_common(1)[0]
            label = "DEFOGGER (Keen Disclaimer)" if cat == "DEFOGGER DISCLAIMER (KEEN)" else cat
            md.append(f"**{label}** — dominant variant ({top_n}/{len(cpns)} CPNs):")
            md.append("")
            md.append(f"> {variant_text[(cat, top_idx)]}")
            md.append("")
        md.append("---")
        md.append("")

    # === Per-option sections (FULL distribution) ===
    md.append("## Full breakdown per option")
    md.append("")
    md.append("Below: every note variant observed for each option, sorted by how many CPNs use it.")
    md.append("")

    for opt in DISPLAY_ORDER:
        cpns = opt_cpns[opt]
        meaning, family = OPTION_META[opt]
        md.append(f"### `{opt}` — {meaning} *(family: {family})*  ·  {len(cpns)} CPN{'s' if len(cpns)!=1 else ''}")
        md.append("")

        if not cpns:
            md.append("*No CPNs observed with this option.*")
            md.append("")
            md.append("---")
            md.append("")
            continue

        # Examples (first 5 CPNs alphabetically)
        examples = sorted(cpns)[:5]
        more = len(cpns) - len(examples)
        md.append("**Example CPNs:** " + ", ".join(f"`{c}`" for c in examples)
                  + (f", *…and {more} more*" if more > 0 else ""))
        md.append("")

        # For each category, list variants with their counts on this option's CPNs
        for cat in CATEGORIES:
            variant_counter = Counter()
            for c in cpns:
                for idx in cpn_variants[c].get(cat, []):
                    variant_counter[idx] += 1
            if not variant_counter:
                continue
            cat_label = "DEFOGGER (Keen Disclaimer)" if cat == "DEFOGGER DISCLAIMER (KEEN)" else cat
            md.append(f"#### {cat_label}")
            md.append("")
            for idx, n in variant_counter.most_common():
                txt = variant_text[(cat, idx)]
                pct = n * 100 // len(cpns)
                md.append(f"- **{n}/{len(cpns)} CPNs ({pct}%):**")
                md.append("")
                md.append(f"  > {txt}")
                md.append("")

        md.append("---")
        md.append("")

    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    print(f"  Options covered: {sum(1 for o in DISPLAY_ORDER if opt_cpns[o])}")
    for opt in DISPLAY_ORDER:
        if opt_cpns[opt]:
            print(f"    {opt:6s} {len(opt_cpns[opt]):>4} CPNs")


if __name__ == "__main__":
    main()
