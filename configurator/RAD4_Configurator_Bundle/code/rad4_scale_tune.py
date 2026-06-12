"""Grid-search the hybrid model's parameters for best catalog match."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import rad4_scale_dynamic as M
from rad4_rules_engine import select_notes, _find_data

rows = list(csv.DictReader(open(_find_data("rad4_scales.csv"), encoding="utf-8")))

samples = []
for r in rows:
    if not r["scale_p1"]:
        continue
    try:
        W, H = float(r["width"]), float(r["height"])
        sc1 = int(r["scale_p1"])
        sc2 = int(r["scale_p2"]) if r["scale_p2"] else None
        nn  = len(select_notes(r["cpn"]))
    except Exception:
        continue
    samples.append((W, H, sc1, sc2, nn))

print(f"Tuning against {len(samples)} sales aids...")

best_p1 = (-1, None)
for base100 in range(380, 440, 5):
    for nd in (0.08, 0.10, 0.13, 0.15, 0.18):
        for wb in (0.10, 0.15, 0.20, 0.25):
            for sp in (0.30, 0.40, 0.50):
                for vp in (0.05, 0.10, 0.15, 0.20):
                    M.CONVENTIONAL_TARGET_BASE = base100 / 100
                    M.CONVENTIONAL_NOTES_DROP  = nd
                    M.CONVENTIONAL_WIDE_BONUS  = wb
                    M.CONVENTIONAL_SQUARE_DROP = sp
                    M.CONVENTIONAL_VERTICAL_PB = vp
                    correct = within = 0
                    for W, H, sc1, sc2, nn in samples:
                        p = M.scale_page_1(W, H, nn)
                        if p == sc1: correct += 1
                        try:
                            d = M.LADDER.index(p) - M.LADDER.index(sc1)
                            if abs(d) <= 1: within += 1
                        except ValueError: pass
                    if correct > best_p1[0]:
                        best_p1 = (correct, (base100/100, nd, wb, sp, vp, within))

print(f"Best page-1: exact={best_p1[0]}/{len(samples)} ({best_p1[0]*100//len(samples)}%)  "
      f"within-1={best_p1[1][5]}/{len(samples)} ({best_p1[1][5]*100//len(samples)}%)")
print(f"  base={best_p1[1][0]}  notes_drop={best_p1[1][1]}  wide_bonus={best_p1[1][2]}  "
      f"square_drop={best_p1[1][3]}  vert_pb={best_p1[1][4]}")
print()

# Now tune page 2 with page-1 params fixed
M.CONVENTIONAL_TARGET_BASE, M.CONVENTIONAL_NOTES_DROP, M.CONVENTIONAL_WIDE_BONUS, \
    M.CONVENTIONAL_SQUARE_DROP, M.CONVENTIONAL_VERTICAL_PB = best_p1[1][:5]

best_p2 = (-1, None)
p2_total = sum(1 for s in samples if s[3])
for p2_bonus_int in range(-30, 80, 10):
    p2_bonus = p2_bonus_int / 100.0
    M_p2_bonus = p2_bonus
    # patch scale_page_2 dynamically using closure
    orig = M.scale_page_2
    def patched(width, height, num_notes_p2, pb_orient=None, _b=p2_bonus):
        if pb_orient is None: pb_orient = M.power_box_orientation(width, height)
        view_w, view_h = M._clear_area_p2(num_notes_p2, pb_orient)
        n_req = max(width/max(0.5,view_w), height/max(0.5,view_h)) * M.GEOMETRY_SAFETY
        target = M._conventional_target(width, height, num_notes_p2, pb_orient) + _b
        n_pref = max(width, height) / target
        return M._ceil_to_ladder(max(n_req, n_pref))
    M.scale_page_2 = patched
    correct = within = 0
    for W, H, sc1, sc2, nn in samples:
        if not sc2: continue
        p = M.scale_page_2(W, H, max(1, nn-2))
        if p == sc2: correct += 1
        try:
            d = M.LADDER.index(p) - M.LADDER.index(sc2)
            if abs(d) <= 1: within += 1
        except ValueError: pass
    if correct > best_p2[0]:
        best_p2 = (correct, (p2_bonus, within))
    M.scale_page_2 = orig

print(f"Best page-2 bonus: {best_p2[1][0]}  exact={best_p2[0]}/{p2_total} ({best_p2[0]*100//p2_total}%)  "
      f"within-1={best_p2[1][1]}/{p2_total} ({best_p2[1][1]*100//p2_total}%)")
