"""Find the rule that maps fixture (W, H) to drawing scale."""
import csv
import statistics
from collections import defaultdict
from pathlib import Path

IN_CSV = Path(r"C:\Users\devops\rad4_scales.csv")
OUT    = Path(r"C:\Users\devops\rad4_scale_analysis.txt")


def main():
    rows = [r for r in csv.DictReader(IN_CSV.open(encoding="utf-8"))
            if r["scale_p1"]]
    out = []
    p = out.append

    p("=" * 80)
    p("RAD4 DRAWING-SCALE RULE — empirical analysis")
    p("=" * 80)
    p(f"PDFs with a page-1 scale extracted: {len(rows)}")
    p("")

    # ── Hypothesis 1: max(W, H) drives the page-1 scale ──
    p("=" * 80)
    p("HYPOTHESIS 1:  page-1 scale is determined by  max(W, H)")
    p("=" * 80)
    p("")
    p(f"  {'Scale':>8}  {'count':>5}  {'max_dim min':>11}  {'max_dim med':>11}  {'max_dim max':>11}")
    by_p1 = defaultdict(list)
    for r in rows:
        by_p1[int(r["scale_p1"])].append(float(r["max_dim"]))
    for s in sorted(by_p1):
        vals = by_p1[s]
        p(f"  1:{s:>4}  {len(vals):>5}  {min(vals):>11.2f}  {statistics.median(vals):>11.2f}  {max(vals):>11.2f}")
    p("")

    # ── show the long sequence of (max_dim → scale) to spot thresholds ──
    p("=" * 80)
    p("Every CPN, sorted by max(W,H), with its scale:")
    p("=" * 80)
    p("")
    p(f"  {'max(W,H)':>9}  {'W':>6}  {'H':>6}  {'p1':>3}  {'p2':>3}  CPN")
    for r in sorted(rows, key=lambda r: float(r["max_dim"])):
        if float(r["max_dim"]) == 0:
            continue
        p(f"  {float(r['max_dim']):>9.2f}  {float(r['width']):>6.2f}  {float(r['height']):>6.2f}  "
          f"{r['scale_p1']:>3}  {r['scale_p2']:>3}  {r['cpn']}")
    p("")

    # ── try to derive thresholds: smallest max_dim that uses each scale ──
    p("=" * 80)
    p("Threshold candidates (each scale's min max-dim, sorted):")
    p("=" * 80)
    p("")
    for s in sorted(by_p1):
        vals = sorted(by_p1[s])
        p(f"  Scale 1:{s:>2}  →  range max(W,H) ∈ [{vals[0]:.2f}, {vals[-1]:.2f}]   "
          f"(p25={vals[len(vals)//4]:.2f}, median={vals[len(vals)//2]:.2f}, p75={vals[3*len(vals)//4]:.2f})")
    p("")

    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {OUT}  ({len(out)} lines)")


if __name__ == "__main__":
    main()
