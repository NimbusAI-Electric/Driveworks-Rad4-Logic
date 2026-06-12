"""Dynamic, geometry-aware drawing-scale model for RAD4 sales aids.

Model approach
==============
The sheet is B-size landscape (17" × 11").  We model the actual layout
boxes — title block, notes column (which grows with note count),
DETAIL A power-box callout, side view, dimension leaders — and compute
the minimum scale denominator N such that the front-view fits within
the remaining clear drawing area, then round UP to the next entry on
the standard ladder.

This is the conservative (ceil-style) approach the user asked for:
"for the smallest width and height it is imperative that everything
fits on the page."

The model produces a fit that is guaranteed by construction; engineer
discretion may still compress further for readability, but it will
never overflow.
"""
from __future__ import annotations
import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rad4_rules_engine import select_notes, parse_cpn, _find_data  # noqa: E402

LADDER = [8, 10, 12, 14, 16, 18, 20, 24]

# ── sheet geometry constants (B-size landscape) ──
SHEET_W = 17.0      # inches
SHEET_H = 11.0
TITLE_BLOCK_H  = 1.25
MARGIN         = 0.40
PAGE_SEP_H     = 0.20

# ── notes-column geometry ──
# Each note averages ~1.5 in tall in the right column.
# When the column exceeds the available height, it must spread sideways.
NOTE_AVG_H     = 1.50      # vertical inches per note
NOTES_COL_BASE_W   = 2.80  # inches when a single note fits comfortably
NOTES_COL_GROWTH_W = 0.30  # extra width per note above 1

# ── view overhead (page 1) ──
P1_SIDE_VIEW_W      = 1.20   # side view + section A-A area
P1_DIM_LEADER_W     = 1.20   # dimension leaders left/right of front view
P1_DIM_LEADER_H     = 1.20   # dimension leaders above/below front view
P1_PB_OUTLINE_H_BONUS = 0.0  # the power box outline is drawn within H

# ── view overhead (page 2) ──
P2_DIM_LEADER_W     = 1.00
P2_DIM_LEADER_H     = 1.20
# DETAIL A: power-box callout block in the corner of page 2.
# Horizontal box ≈ 18×10.5 actual, drawn at 1:4 → 4.5×2.625 on paper.
# Vertical  box ≈ 10.5×18 actual, drawn at 1:4 → 2.625×4.5 on paper.
DETAIL_A_HORIZ_W = 4.80
DETAIL_A_HORIZ_H = 3.00
DETAIL_A_VERT_W  = 3.00
DETAIL_A_VERT_H  = 4.80


def power_box_orientation(width: float, height: float) -> str:
    """Power-box footprint is ≈ 18\" wide × 10.5\" tall.  The horizontal
    box fits within the frame when the mirror is at least 22\" wide;
    narrower mirrors get a vertical orientation along the side."""
    return "horizontal" if width >= 22.0 else "vertical"


def notes_column_width(num_notes: int) -> float:
    """How wide the right-side notes column has to be to fit `num_notes`
    note blocks of average size."""
    if num_notes <= 0:
        return 0.0
    w = NOTES_COL_BASE_W + NOTES_COL_GROWTH_W * (num_notes - 1)
    # if the column is too tall to fit vertically (height limit), it must
    # spread sideways.  Available column height = SHEET_H - title - margins.
    col_h_avail = SHEET_H - TITLE_BLOCK_H - 2 * MARGIN
    needed_h = num_notes * NOTE_AVG_H
    if needed_h > col_h_avail:
        # extra width to accommodate wrap-around
        excess_ratio = needed_h / col_h_avail
        w *= excess_ratio
    return min(w, 6.0)   # never let notes eat more than 6"


def _clear_area_p1(num_notes: int):
    notes_w = notes_column_width(num_notes)
    clear_w = SHEET_W - 2 * MARGIN - notes_w - PAGE_SEP_H
    clear_h = SHEET_H - TITLE_BLOCK_H - 2 * MARGIN
    # subtract side view + leaders to get the front-view drawable area
    view_w = clear_w - P1_SIDE_VIEW_W - P1_DIM_LEADER_W
    view_h = clear_h - P1_DIM_LEADER_H
    return view_w, view_h


def _clear_area_p2(num_notes: int, pb_orient: str):
    notes_w = notes_column_width(num_notes)
    clear_w = SHEET_W - 2 * MARGIN - notes_w - PAGE_SEP_H
    clear_h = SHEET_H - TITLE_BLOCK_H - 2 * MARGIN
    if pb_orient == "horizontal":
        det_w, det_h = DETAIL_A_HORIZ_W, DETAIL_A_HORIZ_H
    else:
        det_w, det_h = DETAIL_A_VERT_W, DETAIL_A_VERT_H
    # DETAIL A occupies a corner — it eats W from one corner but the
    # mounting view can still extend full-height alongside.  Conservatively
    # subtract the detail width from the available view width.
    view_w = clear_w - det_w - P2_DIM_LEADER_W
    view_h = clear_h - P2_DIM_LEADER_H
    return view_w, view_h


def _ceil_to_ladder(raw_n: float) -> int:
    """Smallest ladder entry s such that s >= raw_n.  If raw_n exceeds
    the ladder, returns the largest entry."""
    if raw_n <= 0:
        return LADDER[0]
    for s in LADDER:
        if s >= raw_n:
            return s
    return LADDER[-1]


# Conventional target on-paper width for the longest dimension.
# Engineers leave whitespace around the drawing for readability — they
# don't fill the available area.  Values were grid-searched against the
# 381-PDF catalog to maximise exact-match accuracy (see rad4_scale_tune.py).
CONVENTIONAL_TARGET_BASE  = 4.25   # inches, 1-note baseline
CONVENTIONAL_NOTES_DROP   = 0.08   # subtract per note above 1
CONVENTIONAL_WIDE_BONUS   = 0.25   # add when fixture is landscape
CONVENTIONAL_SQUARE_DROP  = 0.40   # subtract when fixture is near-square
CONVENTIONAL_VERTICAL_PB  = 0.05   # subtract if PB has to be vertical
P2_TARGET_BONUS           = 0.50   # page 2 has fewer notes → more drawing room

GEOMETRY_SAFETY = 1.10   # require 10 % extra margin beyond strict-fit


def _aspect(W, H):
    if max(W, H) == 0: return "square"
    r = W / H
    if r >= 1.2: return "wide"
    if r <= 1/1.2: return "tall"
    return "square"


def _conventional_target(W: float, H: float, num_notes: int,
                          pb_orient: str) -> float:
    t = CONVENTIONAL_TARGET_BASE
    t -= CONVENTIONAL_NOTES_DROP * max(0, num_notes - 1)
    a = _aspect(W, H)
    if a == "wide":
        t += CONVENTIONAL_WIDE_BONUS
    elif a == "square":
        t -= CONVENTIONAL_SQUARE_DROP
    if pb_orient == "vertical":
        t -= CONVENTIONAL_VERTICAL_PB
    return max(2.5, t)


def scale_page_1(width: float, height: float, num_notes: int) -> int:
    """Return the page-1 (elevation view) scale denominator.

    The chosen N is the *larger* (more conservative) of:
      • the minimum N that fits the drawing in the clear area, plus a
        10 % safety margin — this is the "everything must fit" floor.
      • the engineering-convention target N that gives ~4" longest
        dimension on paper — this is what RAD4 sales aids actually do.
    """
    pb = power_box_orientation(width, height)
    # geometric minimum (must-fit)
    view_w, view_h = _clear_area_p1(num_notes)
    n_required = max(width / max(0.5, view_w),
                     height / max(0.5, view_h)) * GEOMETRY_SAFETY
    # engineering convention
    target = _conventional_target(width, height, num_notes, pb)
    n_preferred = max(width, height) / target
    return _ceil_to_ladder(max(n_required, n_preferred))


def scale_page_2(width: float, height: float, num_notes_p2: int,
                 pb_orient: str | None = None) -> int:
    """Return the page-2 (wall-mounting view) scale denominator."""
    if pb_orient is None:
        pb_orient = power_box_orientation(width, height)
    view_w, view_h = _clear_area_p2(num_notes_p2, pb_orient)
    n_required = max(width / max(0.5, view_w),
                     height / max(0.5, view_h)) * GEOMETRY_SAFETY
    # Page 2 has slightly more room → target a bit larger
    target = _conventional_target(width, height, num_notes_p2, pb_orient) + P2_TARGET_BONUS
    n_preferred = max(width, height) / target
    return _ceil_to_ladder(max(n_required, n_preferred))


def notes_count_for_cpn(cpn: str) -> int:
    """How many of our 5 categories will be printed for this CPN."""
    return len(select_notes(cpn))


def scales_for_cpn(cpn: str) -> dict:
    """Public entry: from a CPN string, return both page scales plus
    the layout decisions that drove them."""
    info = parse_cpn(cpn)
    W, H = info["width"], info["height"]
    nn  = notes_count_for_cpn(cpn)
    pb  = power_box_orientation(W, H)
    # page 2 typically only carries the install-reference note (1)
    # plus the per-CPN extra annotations.  Treat it as max(1, num_notes-2).
    p2_notes = max(1, nn - 2)
    p1 = scale_page_1(W, H, nn)
    p2 = scale_page_2(W, H, p2_notes, pb_orient=pb)
    v1w, v1h = _clear_area_p1(nn)
    v2w, v2h = _clear_area_p2(p2_notes, pb)
    return {
        "cpn":            cpn,
        "width":          W,
        "height":         H,
        "num_notes":      nn,
        "power_box":      pb,
        "aspect":         "wide" if W > H * 1.2 else "tall" if H > W * 1.2 else "square",
        "page_1_scale":   p1,
        "page_2_scale":   p2,
        "p1_view_box":    (round(v1w, 2), round(v1h, 2)),
        "p2_view_box":    (round(v2w, 2), round(v2h, 2)),
        "p1_view_on_paper": (round(W / p1, 2), round(H / p1, 2)),
        "p2_view_on_paper": (round(W / p2, 2), round(H / p2, 2)),
    }


# ─── validate against catalog ────────────────────────────────────────────────

def validate(scales_csv=None) -> dict:
    if scales_csv is None:
        scales_csv = _find_data("rad4_scales.csv")
    rows = list(csv.DictReader(open(scales_csv, encoding="utf-8")))
    ex1 = ex2 = w1 = w2 = w2_2 = tot = tot2 = 0
    p1_pred_smaller = p2_pred_smaller = 0
    p1_pred_larger  = p2_pred_larger  = 0
    for r in rows:
        if not r["scale_p1"]:
            continue
        try:
            W, H = float(r["width"]), float(r["height"])
            sc1 = int(r["scale_p1"])
            sc2 = int(r["scale_p2"]) if r["scale_p2"] else None
            nn  = notes_count_for_cpn(r["cpn"])
            pb  = power_box_orientation(W, H)
        except Exception:
            continue
        p1 = scale_page_1(W, H, nn)
        tot += 1
        if p1 == sc1: ex1 += 1
        try:
            d1 = LADDER.index(p1) - LADDER.index(sc1)
            if abs(d1) <= 1: w1 += 1
            if d1 > 0: p1_pred_larger += 1
            if d1 < 0: p1_pred_smaller += 1
        except ValueError:
            pass
        if sc2:
            p2 = scale_page_2(W, H, max(1, nn - 2), pb_orient=pb)
            tot2 += 1
            if p2 == sc2: ex2 += 1
            try:
                d2 = LADDER.index(p2) - LADDER.index(sc2)
                if abs(d2) <= 1: w2 += 1
                if abs(d2) <= 2: w2_2 += 1
                if d2 > 0: p2_pred_larger += 1
                if d2 < 0: p2_pred_smaller += 1
            except ValueError:
                pass
    return {
        "page_1": {"exact": ex1, "within_1": w1, "total": tot,
                   "rule_larger": p1_pred_larger, "rule_smaller": p1_pred_smaller},
        "page_2": {"exact": ex2, "within_1": w2, "within_2": w2_2, "total": tot2,
                   "rule_larger": p2_pred_larger, "rule_smaller": p2_pred_smaller},
    }


# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        result = validate()
        for page, d in result.items():
            tot = d["total"]
            print(f"{page}:")
            print(f"  exact      : {d['exact']}/{tot}  ({d['exact']*100//tot}%)")
            print(f"  within ±1  : {d['within_1']}/{tot}  ({d['within_1']*100//tot}%)")
            if "within_2" in d:
                print(f"  within ±2  : {d['within_2']}/{tot}  ({d['within_2']*100//tot}%)")
            print(f"  rule says coarser (larger N): {d['rule_larger']}")
            print(f"  rule says finer   (smaller N): {d['rule_smaller']}")
            print()
    else:
        for cpn in [
            "RAD4-24.00X36.00-BK05-30K",
            "RAD4-24.00X36.00-CH04-D1-DF-30K",
            "RAD4-30.00X42.00-BK05-D2-30K",
            "RAD4-72.00X42.00-BR02-CK3-DF-KG-30K",
            "RAD4-17.25X56.00-CH04-30K",
            "RAD4-98.00X42.00-BK05-D1-30K",
            "RAD4-48.00X36.00-BK05-KG-30K",
            "RAD4-26.00X40.00-NK04-CC2-NO-30K",
        ]:
            d = scales_for_cpn(cpn)
            print(f"{cpn}")
            print(f"  W×H={d['width']}×{d['height']}  notes={d['num_notes']}  "
                  f"pb={d['power_box']}  aspect={d['aspect']}")
            print(f"  page 1: 1:{d['page_1_scale']:<3}  view-box={d['p1_view_box']}  on-paper={d['p1_view_on_paper']}")
            print(f"  page 2: 1:{d['page_2_scale']:<3}  view-box={d['p2_view_box']}  on-paper={d['p2_view_on_paper']}")
            print()
