"""Validate the rule engine against every catalog CPN.

For each CPN:
  - Run the rule engine to get predicted note categories
  - Compare against the actual note categories on its sales aid
Report per-category precision / recall and list every disagreement so the
user can decide whether the rule needs to be tightened."""
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from rad4_rules_engine import select_notes, parse_cpn, _find_data

NOTES_JSON = _find_data("rad4_notes.json")
SPECS_CSV  = _find_data("rad4_specifications.csv")
OUT_TXT    = Path(__file__).resolve().parent / "rad4_rules_validation.txt"

CATEGORIES = ["SPECIFICATION", "ATTENTION", "DEFOGGER",
              "DEFOGGER DISCLAIMER (KEEN)", "DIMMING"]


def main():
    notes = json.loads(NOTES_JSON.read_text(encoding="utf-8"))

    # actual presence per CPN
    actual_present = defaultdict(set)        # cpn -> {category}
    actual_dim_kind = {}                      # cpn -> "TRIAC"|"0-10V"|"OTHER"
    actual_attn_kind = {}                     # cpn -> "NEC"|"GFCI"|"OTHER"
    actual_def_w = {}                         # cpn -> wattage string

    for cat in CATEGORIES:
        for v in notes.get(cat, []):
            for cpn in v["cpns"]:
                actual_present[cpn].add(cat)
                t = v["text"].upper()
                if cat == "DIMMING":
                    if "FORWARD PHASE" in t:
                        actual_dim_kind[cpn] = "TRIAC"
                    elif "0-10V" in t:
                        actual_dim_kind[cpn] = "0-10V"
                    else:
                        actual_dim_kind[cpn] = "OTHER"
                elif cat == "ATTENTION":
                    if "GFCI" in t:
                        actual_attn_kind[cpn] = "GFCI"
                    elif "EARTH GROUND" in t:
                        actual_attn_kind[cpn] = "NEC"
                    else:
                        actual_attn_kind[cpn] = "OTHER"
                elif cat == "DEFOGGER":
                    m = re.search(r"WATTAGE\s*\(?W?\)?\s*:?\s*(\d+)\s*W?", v["text"])
                    if m:
                        actual_def_w[cpn] = int(m.group(1))

    # all CPNs from master CSV
    rows = list(csv.DictReader(SPECS_CSV.open(encoding="utf-8")))
    all_cpns = sorted({r["cpn"] for r in rows})

    out = []
    p = out.append

    p("=" * 80)
    p("RAD4 RULE-ENGINE VALIDATION")
    p("=" * 80)
    p(f"CPNs evaluated: {len(all_cpns)}")
    p("")

    # ── presence accuracy per category ──
    p("Per-category PRESENCE accuracy (does the rule predict the right notes appear at all?):")
    p("")
    p(f"  {'Category':30s}  {'TP':>4} {'FP':>4} {'FN':>4} {'TN':>4}  {'prec':>6} {'recall':>7} {'F1':>6}")
    cat_disagreements = defaultdict(list)

    for cat in CATEGORIES:
        tp = fp = fn = tn = 0
        for cpn in all_cpns:
            try:
                pred = select_notes(cpn)
            except ValueError:
                continue
            predicted = cat in pred
            actual    = cat in actual_present[cpn]
            if predicted and actual:    tp += 1
            elif predicted and not actual: fp += 1; cat_disagreements[cat].append((cpn, "FP"))
            elif not predicted and actual: fn += 1; cat_disagreements[cat].append((cpn, "FN"))
            else:                          tn += 1
        prec = tp / max(1, tp + fp)
        rec  = tp / max(1, tp + fn)
        f1   = 2*prec*rec / max(1e-9, prec + rec)
        p(f"  {cat:30s}  {tp:>4} {fp:>4} {fn:>4} {tn:>4}  {prec*100:>5.1f}% {rec*100:>6.1f}% {f1*100:>5.1f}%")

    p("")
    p("TP = rule says YES, sales aid has it  |  FP = rule says YES, sales aid doesn't")
    p("FN = rule says NO,  sales aid has it  |  TN = rule says NO,  sales aid doesn't")
    p("")

    # ── DIMMING variant accuracy ──
    p("=" * 80)
    p("DIMMING — variant accuracy (TRIAC vs 0-10V)")
    p("=" * 80)
    p("")

    dim_match = dim_mismatch = 0
    dim_disagree = []
    for cpn in all_cpns:
        actual_kind = actual_dim_kind.get(cpn)
        if not actual_kind:
            continue
        try:
            pred = select_notes(cpn)
        except ValueError:
            continue
        if "DIMMING" not in pred:
            continue
        pred_kind = "TRIAC" if "FORWARD PHASE" in pred["DIMMING"].upper() else "0-10V"
        if pred_kind == actual_kind:
            dim_match += 1
        else:
            dim_mismatch += 1
            dim_disagree.append((cpn, actual_kind, pred_kind))
    total = dim_match + dim_mismatch
    p(f"  Match:    {dim_match}/{total}  ({dim_match*100//max(1,total)}%)")
    p(f"  Mismatch: {dim_mismatch}/{total}")
    if dim_disagree:
        p("")
        p("  Mismatches:")
        for cpn, act, pred in dim_disagree:
            p(f"    {cpn:50s}  actual={act}  predicted={pred}")
    p("")

    # ── ATTENTION variant accuracy ──
    p("=" * 80)
    p("ATTENTION — variant accuracy (NEC vs GFCI)")
    p("=" * 80)
    p("")

    attn_match = attn_mismatch = 0
    attn_disagree = []
    for cpn in all_cpns:
        actual_kind = actual_attn_kind.get(cpn)
        if not actual_kind:
            continue
        try:
            pred = select_notes(cpn)
        except ValueError:
            continue
        if "ATTENTION" not in pred:
            continue
        pred_kind = "GFCI" if "GFCI" in pred["ATTENTION"].upper() else "NEC"
        if pred_kind == actual_kind:
            attn_match += 1
        else:
            attn_mismatch += 1
            attn_disagree.append((cpn, actual_kind, pred_kind))
    total = attn_match + attn_mismatch
    p(f"  Match:    {attn_match}/{total}  ({attn_match*100//max(1,total)}%)")
    p(f"  Mismatch: {attn_mismatch}/{total}")
    if attn_disagree:
        p("")
        p("  Mismatches:")
        for cpn, act, pred in attn_disagree:
            p(f"    {cpn:50s}  actual={act}  predicted={pred}")
    p("")

    # ── DEFOGGER wattage accuracy ──
    p("=" * 80)
    p("DEFOGGER wattage prediction accuracy")
    p("=" * 80)
    p("")
    from rad4_rules_engine import defogger_wattage
    def_match = def_mismatch = 0
    def_disagree = []
    for cpn in all_cpns:
        actual_w = actual_def_w.get(cpn)
        if actual_w is None:
            continue
        info = parse_cpn(cpn)
        pred_w_str = defogger_wattage(
            info["area"],
            "277V" in info["options"],
            has_dfx="DFX" in info["options"],
        )
        m = re.match(r"(\d+)W", pred_w_str)
        pred_w = int(m.group(1)) if m else None
        if pred_w == actual_w:
            def_match += 1
        else:
            def_mismatch += 1
            def_disagree.append((cpn, info["area"], actual_w, pred_w))
    total = def_match + def_mismatch
    p(f"  Match:    {def_match}/{total}  ({def_match*100//max(1,total)}%)")
    p(f"  Mismatch: {def_mismatch}/{total}")
    if def_disagree:
        p("")
        p("  Mismatches:")
        for cpn, area, act, pred in def_disagree:
            p(f"    {cpn:50s}  area={area:>7.0f}in²  actual={act}W  predicted={pred}W")
    p("")

    # ── presence-disagreement detail (capped) ──
    p("=" * 80)
    p("PRESENCE disagreement details")
    p("=" * 80)
    p("")
    for cat in CATEGORIES:
        disagreements = cat_disagreements[cat]
        if not disagreements:
            continue
        p(f"--- {cat}: {len(disagreements)} disagreement(s) ---")
        for cpn, kind in disagreements[:25]:
            info = parse_cpn(cpn)
            p(f"  [{kind}] {cpn:50s}   opts={sorted(info['options'])}")
        if len(disagreements) > 25:
            p(f"  …and {len(disagreements)-25} more")
        p("")

    OUT_TXT.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {OUT_TXT}")


if __name__ == "__main__":
    main()
