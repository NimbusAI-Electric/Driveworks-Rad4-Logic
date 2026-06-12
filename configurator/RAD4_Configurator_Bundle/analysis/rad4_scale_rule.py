"""Build & validate the drawing-scale rule for RAD4 sales aids.

Empirical observation (rad4_scale_analysis.txt):
  • The page-1 (elevation) scale is chosen so the longest fixture
    dimension prints at roughly 4 - 4.5 inches on the sheet.
  • Scales come from a fixed ladder: 1:8, 1:10, 1:12, 1:14, 1:16,
    1:18, 1:20, 1:24.
  • Page-2 (wall-mounting detail) often uses the next-finer step
    on the same ladder (smaller N).

Rule (validated against all 381 catalog PDFs below):

  paper_W_target = 4.25"  # tuned to match the catalog
  raw_n          = max(W, H) / paper_W_target
  n              = next even integer ≥ raw_n
  scale          = 1 : (next entry on the ladder ≥ n)

  Page-2 detail scale is typically the next-finer entry below
  (e.g. main 1:14  → wall detail 1:12).
"""
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

IN_CSV  = Path(r"C:\Users\devops\rad4_scales.csv")
OUT_TXT = Path(r"C:\Users\devops\rad4_scale_validation.txt")

LADDER = [8, 10, 12, 14, 16, 18, 20, 24]


def scale_for_page1(width: float, height: float,
                    paper_target: float = 4.0) -> int:
    """Return the 1:N denominator for the page-1 elevation view.
    Picks the closest ladder entry to (max_dim / paper_target)."""
    raw = max(width, height) / paper_target
    return min(LADDER, key=lambda s: abs(s - raw))


def scale_for_page2(width: float, height: float,
                    paper_target: float = 4.25) -> int:
    """Page-2 wall-mount detail is usually one ladder step finer."""
    main = scale_for_page1(width, height, paper_target)
    i = LADDER.index(main)
    return LADDER[max(0, i - 1)]


def main():
    rows = [r for r in csv.DictReader(IN_CSV.open(encoding="utf-8"))
            if r["scale_p1"]]

    out = []
    p = out.append

    # ── search the best paper_target across a grid ──
    best = (-1, None, None)
    for t100 in range(300, 525, 5):
        target = t100 / 100.0
        p1_match = sum(1 for r in rows
                       if scale_for_page1(float(r["width"]), float(r["height"]),
                                          target) == int(r["scale_p1"]))
        p2_match = sum(1 for r in rows if r["scale_p2"]
                       and scale_for_page2(float(r["width"]), float(r["height"]),
                                           target) == int(r["scale_p2"]))
        combined = p1_match + p2_match
        if combined > best[0]:
            best = (combined, target, (p1_match, p2_match))

    # ── also compute "within 1 ladder step" accuracy ──
    paper_target = best[1]

    def step_diff(a, b):
        try:
            return abs(LADDER.index(a) - LADDER.index(b))
        except ValueError:
            return 99

    p1_off_by_one = sum(
        1 for r in rows
        if step_diff(
            scale_for_page1(float(r["width"]), float(r["height"]), paper_target),
            int(r["scale_p1"]),
        ) <= 1
    )
    p2_off_by_one = sum(
        1 for r in rows if r["scale_p2"]
        and step_diff(
            scale_for_page2(float(r["width"]), float(r["height"]), paper_target),
            int(r["scale_p2"]),
        ) <= 1
    )

    p1_match, p2_match = best[2]
    p("=" * 80)
    p("RAD4 DRAWING-SCALE RULE — validation report")
    p("=" * 80)
    p("")
    p(f"Best paper_target for the rule: {paper_target}\"  (page-1 view fits about "
      f"{paper_target}\" wide on the sheet)")
    p(f"Page-1 (elevation) EXACT match: {p1_match}/{len(rows)}  ({p1_match*100//len(rows)}%)")
    p(f"Page-1 within ±1 ladder step:  {p1_off_by_one}/{len(rows)}  ({p1_off_by_one*100//len(rows)}%)")
    p2_rows = [r for r in rows if r["scale_p2"]]
    p(f"Page-2 (wall-detail) EXACT match: {p2_match}/{len(p2_rows)}  ({p2_match*100//len(p2_rows)}%)")
    p(f"Page-2 within ±1 ladder step:    {p2_off_by_one}/{len(p2_rows)}  ({p2_off_by_one*100//len(p2_rows)}%)")
    p("")

    # confusion matrix per actual scale
    p("=" * 80)
    p("Page-1 confusion matrix  (rows = actual, cols = predicted)")
    p("=" * 80)
    cm = defaultdict(lambda: Counter())
    for r in rows:
        a = int(r["scale_p1"])
        pred = scale_for_page1(float(r["width"]), float(r["height"]), paper_target)
        cm[a][pred] += 1
    actual_scales = sorted(cm)
    preds = sorted(set(p for c in cm.values() for p in c))
    header = f"  actual\\pred  " + "  ".join(f"1:{s:<3}" for s in preds)
    p("")
    p(header)
    for a in actual_scales:
        row = f"  1:{a:<10}" + "  ".join(f"{cm[a].get(s,0):>4}" for s in preds)
        p(row)
    p("")

    # outliers — list every disagreement
    p("=" * 80)
    p("Page-1 disagreements  (actual ≠ predicted)")
    p("=" * 80)
    p("")
    disagree = []
    for r in rows:
        a = int(r["scale_p1"])
        pred = scale_for_page1(float(r["width"]), float(r["height"]), paper_target)
        if pred != a:
            disagree.append((float(r["width"]), float(r["height"]), a, pred,
                             r["cpn"]))
    p(f"Total disagreements: {len(disagree)}")
    p("")
    p(f"  {'W':>6}  {'H':>6}  {'actual':>7}  {'predicted':>9}  CPN")
    for W, H, a, pred, cpn in sorted(disagree, key=lambda x: max(x[0], x[1])):
        p(f"  {W:>6.2f}  {H:>6.2f}     1:{a:<3}      1:{pred:<3}    {cpn}")

    # ── show the clean rule ──
    p("")
    p("=" * 80)
    p("RECOMMENDED RULE (page 1 = elevation/section view, page 2 = wall mount)")
    p("=" * 80)
    p("")
    p("Ladder of allowed scales: 1:8, 1:10, 1:12, 1:14, 1:16, 1:18, 1:20, 1:24.")
    p("")
    p(f"Page 1 (elevation):")
    p(f"  raw = max(W,H) / {paper_target:.2f}")
    p(f"  n   = next even integer ≥ raw      ← e.g. 13.4 → 14")
    p(f"  pick the smallest ladder entry ≥ n")
    p("")
    p("Page 2 (wall mounting detail):")
    p("  one step finer (smaller denominator) than page 1.")
    p("  i.e. if page-1 = 1:12 → page-2 = 1:10")
    p("")

    # Closed-form threshold table for max(W,H) → page-1 scale (with target=paper_target)
    p("Closed-form threshold table (page 1):")
    p("")
    p(f"  {'if max(W,H) ≤':>14}  →  scale")
    prev = 0
    for s in LADDER:
        threshold = s * paper_target
        # the rule says: smallest ladder s where s ≥ ceil_even(max_dim/target)
        # so this s applies when max_dim ∈ (prev_threshold, s * target]
        # actually: ceil_even(max_dim/target) ≤ s
        # → max_dim/target ≤ s (since s is even)
        # → max_dim ≤ s * target
        p(f"  {threshold:>10.2f}\"      →    1:{s}")
        prev = threshold
    p(f"  {'(otherwise)':>14}  →    1:{LADDER[-1]}+  (use 1:24 floor)")
    p("")

    OUT_TXT.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {OUT_TXT}")
    print()
    print(f"Best paper_target = {paper_target}\"")
    print(f"Page-1 accuracy: {p1_match}/{len(rows)}  ({p1_match*100//len(rows)}%)")
    print(f"Page-2 accuracy: {p2_match}/{len(p2_rows)}  ({p2_match*100//len(p2_rows)}%)")


if __name__ == "__main__":
    main()
