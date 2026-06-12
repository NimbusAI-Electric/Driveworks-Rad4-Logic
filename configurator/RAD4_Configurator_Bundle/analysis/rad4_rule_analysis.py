"""Empirically derive note-selection rules from the data.

For each note category, look at which option sets predict which variant.
Output the analysis so we can write defensible rules."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

NOTES_JSON = Path(r"C:\Users\devops\rad4_notes.json")
SPECS_CSV  = Path(r"C:\Users\devops\rad4_specifications.csv")
OUT_TXT    = Path(r"C:\Users\devops\rad4_rule_analysis.txt")

CATEGORIES = ["SPECIFICATION", "ATTENTION", "DEFOGGER",
              "DEFOGGER DISCLAIMER (KEEN)", "DIMMING"]

# Parse CPN -> options
def cpn_opts(row):
    return set(o for o in row["cpn_options"].split(";") if o)


def main():
    notes = json.loads(NOTES_JSON.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(SPECS_CSV.open(encoding="utf-8")))

    # cpn -> opts + size + finish + cct
    cpn_meta = {}
    for r in rows:
        cpn_meta[r["cpn"]] = {
            "opts":   cpn_opts(r),
            "size":   r["cpn_size"],
            "finish": r["cpn_finish_code"],
            "cct":    r["cpn_cct_code"],
            "has_277V": "277V" in cpn_opts(r) or r["has_277v"] == "True",
        }

    # category -> cpn -> set(variant_idx)
    cpn_variant = defaultdict(lambda: defaultdict(set))
    variant_text = {}
    for cat in CATEGORIES:
        for idx, v in enumerate(notes.get(cat, [])):
            variant_text[(cat, idx)] = v["text"]
            for cpn in v["cpns"]:
                cpn_variant[cat][cpn].add(idx)

    out = []
    def p(s=""): out.append(s)

    p("=" * 80)
    p("RAD4 NOTE-SELECTION RULES — empirical analysis")
    p("=" * 80)
    p()

    all_cpns = sorted(cpn_meta)
    p(f"Total CPNs analyzed: {len(all_cpns)}")
    p()

    # ---------- Category presence rules ----------
    p("=" * 80)
    p("PART 1: WHEN IS EACH NOTE CATEGORY PRESENT?")
    p("=" * 80)
    p()

    # Define candidate "triggers" — option combinations
    def has(opts, *codes):
        return any(c in opts for c in codes)

    triggers = {
        "any_defogger":   lambda o: has(o, "D1", "D2", "DF", "DFX"),
        "any_keen":       lambda o: has(o, "KG", "KG2", "KD", "KC"),
        "any_clock":      lambda o: has(o, "CK2", "CK3"),
        "color_change":   lambda o: has(o, "CC2"),
        "wall_grommet":   lambda o: has(o, "WG3"),
        "night_light":    lambda o: has(o, "NO"),
        "cord_connected": lambda o: has(o, "CC2", "NO"),   # hypothesis
        "277V":           lambda o: has(o, "277V"),
        "no_options":     lambda o: len(o) == 0,
    }

    for cat in CATEGORIES:
        present_cpns = [c for c in all_cpns if cpn_variant[cat].get(c)]
        absent_cpns  = [c for c in all_cpns if not cpn_variant[cat].get(c)]
        p(f"--- {cat} ---")
        p(f"  Present on:  {len(present_cpns):>4} CPNs  ({len(present_cpns)*100//len(all_cpns)}%)")
        p(f"  Absent from: {len(absent_cpns):>4} CPNs")
        p()
        # For each trigger, how predictive is it?
        p(f"  Trigger correlation (precision = fraction of triggered CPNs that have the note;")
        p(f"                       recall    = fraction of CPNs with the note that match trigger):")
        for tname, fn in triggers.items():
            triggered = set(c for c in all_cpns if fn(cpn_meta[c]["opts"]))
            present   = set(present_cpns)
            tp = len(triggered & present)
            fp = len(triggered - present)
            fn_ = len(present - triggered)
            prec = tp / max(1, tp + fp)
            rec  = tp / max(1, tp + fn_)
            p(f"    {tname:18s}  precision {prec*100:5.1f}%  recall {rec*100:5.1f}%   ({tp} match / {len(triggered)} triggered / {len(present)} present)")
        p()

    # ---------- Per-category VARIANT-selection rules ----------
    p("=" * 80)
    p("PART 2: WHEN A CATEGORY IS PRESENT, WHICH VARIANT IS USED?")
    p("=" * 80)
    p()

    for cat in CATEGORIES:
        p(f"--- {cat} ---")
        # group cpns by which variant they use
        variant_to_opts = defaultdict(list)
        for cpn, idxs in cpn_variant[cat].items():
            for idx in idxs:
                variant_to_opts[idx].append(tuple(sorted(cpn_meta[cpn]["opts"])))
        # show top variants and option distribution
        # Order variants by usage count
        ranked = sorted(variant_to_opts.items(), key=lambda kv: -len(kv[1]))
        for idx, opts_list in ranked[:6]:
            text = variant_text[(cat, idx)]
            opt_counter = Counter(opts_list)
            p(f"  Variant {idx} — used {len(opts_list)} times")
            p(f"    text: {text[:140]}{'…' if len(text)>140 else ''}")
            p(f"    top option-sets that use it:")
            for opt_set, n in opt_counter.most_common(5):
                p(f"      {n:>4}x  ({', '.join(opt_set) if opt_set else '∅ no options'})")
            p()
        if len(ranked) > 6:
            p(f"  + {len(ranked)-6} more variants with smaller counts")
            p()
        p()

    # ---------- DIMMING: TRIAC vs 0-10V rule check ----------
    p("=" * 80)
    p("PART 3: DIMMING — is D2 ↔ TRIAC and D1/DF/DFX ↔ 0-10V?")
    p("=" * 80)
    p()

    triac_kw = "FORWARD PHASE"
    zero_ten_kw = "0-10V"
    dim_by_cpn = {}
    for cpn, idxs in cpn_variant["DIMMING"].items():
        kinds = set()
        for idx in idxs:
            t = variant_text[("DIMMING", idx)].upper()
            if triac_kw in t:
                kinds.add("TRIAC")
            elif zero_ten_kw in t:
                kinds.add("0-10V")
            else:
                kinds.add("OTHER")
        dim_by_cpn[cpn] = kinds

    for code in ["D1", "D2", "DF", "DFX", "KD"]:
        has_code = [c for c in dim_by_cpn if code in cpn_meta[c]["opts"]]
        no_code  = [c for c in dim_by_cpn if code not in cpn_meta[c]["opts"]]
        triac_n = sum(1 for c in has_code if "TRIAC" in dim_by_cpn[c])
        zero_n  = sum(1 for c in has_code if "0-10V" in dim_by_cpn[c])
        other_n = sum(1 for c in has_code if "OTHER" in dim_by_cpn[c])
        p(f"  CPNs with '{code}' that also have DIMMING note: {len(has_code)}")
        p(f"     TRIAC: {triac_n}   0-10V: {zero_n}   OTHER: {other_n}")
    p()

    # CPNs that have a DIMMING note but NO defogger / KD ?
    no_def_kd = [c for c in dim_by_cpn
                 if not (cpn_meta[c]["opts"] & {"D1","D2","DF","DFX","KD"})]
    p(f"  CPNs with a DIMMING note but no D1/D2/DF/DFX/KD: {len(no_def_kd)}")
    for c in no_def_kd[:10]:
        p(f"    {c}    opts={sorted(cpn_meta[c]['opts'])}")
    p()

    # ---------- DEFOGGER wattage by size ----------
    p("=" * 80)
    p("PART 4: DEFOGGER wattage vs fixture size")
    p("=" * 80)
    p()
    import re
    for cpn in sorted(cpn_variant["DEFOGGER"]):
        for idx in cpn_variant["DEFOGGER"][cpn]:
            t = variant_text[("DEFOGGER", idx)]
            m = re.search(r"WATTAGE\s*\(?W?\)?\s*:?\s*(\d+)", t)
            w = m.group(1) if m else "?"
            size = cpn_meta[cpn]["size"]
            try:
                W, H = (float(x) for x in size.split("X"))
                area = W * H
            except Exception:
                W, H, area = 0, 0, 0
            p(f"    {cpn:50s}   size={size:>14}  area={area:>7.0f} in²  → defogger {w}W")
    p()

    # ---------- ATTENTION variant ↔ option family ----------
    p("=" * 80)
    p("PART 5: ATTENTION — NEC ground variant vs GFCI variant")
    p("=" * 80)
    p()
    nec_kw  = "EARTH GROUND"
    gfci_kw = "GFCI"
    for cpn, idxs in cpn_variant["ATTENTION"].items():
        kinds = []
        for idx in idxs:
            t = variant_text[("ATTENTION", idx)].upper()
            if nec_kw in t:
                kinds.append("NEC")
            elif gfci_kw in t:
                kinds.append("GFCI")
            else:
                kinds.append("OTHER")
        opts = sorted(cpn_meta[cpn]["opts"])
        p(f"    {cpn:50s}   opts={opts}   kinds={kinds}")
    p()

    OUT_TXT.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {OUT_TXT}  ({len(out)} lines)")


if __name__ == "__main__":
    main()
