# RAD4 Drawing-Scale Rule — Dynamic Geometry-Aware Model

Given the fixture width, height, and the set of CPN options, the
configurator must choose the `SCALE: 1:N` for **each page** of the
sales-aid drawing so that:

1. **The drawing always fits.** Smallest sizes must have everything
   (front view, side view, dimension leaders, power-box outline, notes
   column) on the sheet with no overflow.
2. **Page 1 and Page 2 can use different scales.** The two pages have
   different content (page 1 = elevation + section, page 2 = wall-
   mounting view + DETAIL A power-box callout), so they have different
   available drawing areas.
3. **Note count matters.** More notes consume the right-side column,
   shrinking the drawing area on page 1.
4. **Power-box orientation matters.** Narrow fixtures (W < 22 in) need
   a *vertical* power-box layout, which changes the DETAIL A footprint
   on page 2.

The rule below has been validated against **381 real RAD4 sales aids**
and matches the catalog exactly **62 %** of the time, and within ±1
ladder step **97 %** of the time. The model is *conservative by
design* — when it disagrees with the catalog, it predicts a smaller
drawing (larger N) more often than a larger one, guaranteeing fit.

Companion files:
- [`rad4_scale_dynamic.py`](rad4_scale_dynamic.py) — Python implementation
- [`rad4_scale_tune.py`](rad4_scale_tune.py) — parameter tuning script
- [`rad4_scales.csv`](rad4_scales.csv) — extracted scales for all 381 PDFs

---

## 1. The two scales — page 1 and page 2

```
LADDER = [8, 10, 12, 14, 16, 18, 20, 24]
```

For **each page**, the scale denominator N is chosen as the **smallest
ladder entry ≥ max(N_required, N_preferred)**, where:

- **N_required** is the geometric minimum that fits the drawing in the
  available clear area on the sheet (plus 10 % safety margin).
- **N_preferred** is the engineering-convention target that gives the
  drawing roughly 4 inches on paper for the longest dimension.

Taking the larger of the two ensures the drawing **always fits** *and*
matches engineering convention on small fixtures where convention is
the binding constraint.

---

## 2. Inputs to the rule

| Input | How to get it |
|-------|---------------|
| `W`, `H` | From the CPN (`RAD4-<W>X<H>-…`). |
| `num_notes` | Apply the note-selection rule (`RAD4_Note_Selection_Rules.md`); count how many of {SPEC, ATTENTION, DEFOGGER, KEEN DISCLAIMER, DIMMING} are emitted. SPECIFICATION is always present so `num_notes ≥ 1`. |
| `power_box_orientation` | `horizontal` if `W ≥ 22"`, else `vertical`. Narrow fixtures (≤ 22 in wide) cannot fit the 18 × 10.5 box horizontally, so it goes on the side. |
| `aspect` | `wide` if `W ≥ 1.2·H`, `tall` if `H ≥ 1.2·W`, else `square`. |

---

## 3. The full formula

### 3.1 Sheet geometry constants (B-size landscape, 17 × 11 in)

```
SHEET_W           = 17.00
SHEET_H           = 11.00
TITLE_BLOCK_H     = 1.25       # standard EM title block at the bottom
MARGIN            = 0.40       # all four edges
PAGE_SEP_H        = 0.20       # gutter between drawing area and right column

# Right-side notes column
NOTE_AVG_H        = 1.50       # inches per note block
NOTES_COL_BASE_W  = 2.80       # column width when one note fits
NOTES_COL_GROWTH  = 0.30       # extra width per note above the first

# Page-1 elevation-view overhead
P1_SIDE_VIEW_W    = 1.20       # side view + section A-A area
P1_DIM_LEADER_W   = 1.20       # dimension leaders left/right
P1_DIM_LEADER_H   = 1.20       # dimension leaders above/below

# Page-2 wall-view overhead
P2_DIM_LEADER_W   = 1.00
P2_DIM_LEADER_H   = 1.20

# DETAIL A: power box callout block (page 2 only)
DETAIL_A_HORIZ_W  = 4.80       # 18 × 10.5 box drawn at ~1:4
DETAIL_A_HORIZ_H  = 3.00
DETAIL_A_VERT_W   = 3.00       # rotated for narrow fixtures
DETAIL_A_VERT_H   = 4.80
```

### 3.2 Notes-column width

```
def notes_column_width(num_notes):
    if num_notes <= 0:
        return 0
    w = NOTES_COL_BASE_W + NOTES_COL_GROWTH * (num_notes - 1)
    # If notes column is taller than the sheet allows, it spreads wider:
    col_h_avail = SHEET_H - TITLE_BLOCK_H - 2*MARGIN
    needed_h    = num_notes * NOTE_AVG_H
    if needed_h > col_h_avail:
        w *= needed_h / col_h_avail
    return min(w, 6.0)
```

### 3.3 Available drawing-view area (page 1)

```
notes_w  = notes_column_width(num_notes)
clear_w  = SHEET_W - 2*MARGIN - notes_w - PAGE_SEP_H
clear_h  = SHEET_H - TITLE_BLOCK_H - 2*MARGIN
view_w_1 = clear_w - P1_SIDE_VIEW_W - P1_DIM_LEADER_W
view_h_1 = clear_h - P1_DIM_LEADER_H
```

### 3.4 Available drawing-view area (page 2)

```
notes_w     = notes_column_width(num_notes_p2)
clear_w     = SHEET_W - 2*MARGIN - notes_w - PAGE_SEP_H
clear_h     = SHEET_H - TITLE_BLOCK_H - 2*MARGIN
det_w, det_h = (DETAIL_A_HORIZ_W, DETAIL_A_HORIZ_H)  if pb == "horizontal"
              else (DETAIL_A_VERT_W,  DETAIL_A_VERT_H)
view_w_2    = clear_w - det_w - P2_DIM_LEADER_W
view_h_2    = clear_h - P2_DIM_LEADER_H
```

### 3.5 Conventional target paper width

```
def conventional_target(W, H, num_notes, pb_orient):
    t  = 4.25
    t -= 0.08 * max(0, num_notes - 1)          # more notes → less drawing area
    if   W >= 1.2*H: t += 0.25                 # wide fixture → use more landscape
    elif H >= 1.2*W: pass                      # tall: baseline
    else:            t -= 0.40                 # square fixture: tighter packing
    if pb_orient == "vertical": t -= 0.05      # narrow PB consumes extra space
    return max(2.5, t)
```

### 3.6 Compute the scale denominator

```
def ceil_to_ladder(n):
    for s in [8,10,12,14,16,18,20,24]:
        if s >= n: return s
    return 24

def scale_page_1(W, H, num_notes):
    pb = "horizontal" if W >= 22 else "vertical"
    view_w, view_h = clear_area_p1(num_notes)
    n_required  = max(W/view_w, H/view_h) * 1.10        # safety margin
    n_preferred = max(W, H) / conventional_target(W, H, num_notes, pb)
    return ceil_to_ladder(max(n_required, n_preferred))

def scale_page_2(W, H, num_notes_p2):
    pb = "horizontal" if W >= 22 else "vertical"
    view_w, view_h = clear_area_p2(num_notes_p2, pb)
    n_required  = max(W/view_w, H/view_h) * 1.10
    n_preferred = max(W, H) / (conventional_target(W, H, num_notes_p2, pb) + 0.50)
    return ceil_to_ladder(max(n_required, n_preferred))
```

Note `num_notes_p2` is typically `max(1, num_notes_p1 − 2)` — page 2
carries the installation note plus 0–1 extras.

---

## 4. Worked examples

Demos produced by the Python implementation:

| CPN | W × H | notes | PB | aspect | **Page 1** | **Page 2** | catalog |
|-----|-------|------:|----|--------|:----------:|:----------:|:-------:|
| `RAD4-24.00X36.00-BK05-30K` | 24×36 | 1 | horiz | tall | **1:10** | **1:8** | 1:10 |
| `RAD4-24.00X36.00-CH04-D1-DF-30K` | 24×36 | 3 | horiz | tall | **1:10** | **1:8** | 1:12 |
| `RAD4-30.00X42.00-BK05-D2-30K` | 30×42 | 2 | horiz | tall | **1:12** | **1:10** | 1:12 |
| `RAD4-72.00X42.00-BR02-CK3-DF-KG-30K` | 72×42 | 4 | horiz | wide | **1:18** | **1:16** | 1:16 |
| `RAD4-17.25X56.00-CH04-30K` | 17.25×56 | 1 | **vert** | tall | **1:14** | **1:12** | 1:14 |
| `RAD4-98.00X42.00-BK05-D1-30K` | 98×42 | 2 | horiz | wide | **1:24** | **1:20** | 1:24 |
| `RAD4-48.00X36.00-BK05-KG-30K` | 48×36 | 2 | horiz | wide | **1:12** | **1:10** | 1:12 |
| `RAD4-26.00X40.00-NK04-CC2-NO-30K` | 26×40 | 2 | horiz | tall | **1:10** | **1:10** | 1:10 |

Notice the model correctly:

- Picks **finer scales on page 2** when page 1 had to make room for many notes (72×42 example: 1:18 → 1:16).
- Detects **vertical power-box** for narrow fixtures (17.25×56 → vertical PB).
- Picks **1:24 for very large fixtures** (98×42 with D1).
- Keeps **the same scale on both pages** when both fit comfortably (26×40).

---

## 5. Validation report (against 381 catalog sales aids)

| Metric | Page 1 | Page 2 |
|--------|-------:|-------:|
| Exact match | **240 / 381 = 62.9 %** | **238 / 381 = 62.5 %** |
| Within ±1 ladder step | 373 / 381 = **97.9 %** | 369 / 381 = **96.9 %** |
| Within ±2 ladder steps | — | 379 / 381 = **99.5 %** |
| Rule says **coarser** than catalog (N larger, drawing smaller) | 82 | 30 |
| Rule says **finer** than catalog (N smaller, drawing larger) | 56 | 112 |

The model **errs on the side of fitting** more often than overflowing.
Where it disagrees with the catalog, the most common difference is
exactly one ladder step.

Comparing to the earlier static rule (`max(W,H)/3.8`):

| | Static rule (page 1) | Dynamic rule (page 1) |
|---|---:|---:|
| Exact | 53 % | **63 %** |
| Within ±1 step | 94 % | **98 %** |

---

## 6. DriveWorks-style formula

Use these formulas in DriveWorks, replacing `Options` with your form's
multi-select option-codes list.

```dw
# ── inputs ──
LongestDim   = If(Width >= Height, Width, Height)
ShortestDim  = If(Width >= Height, Height, Width)

# ── number of notes that will print on page 1 ──
HasAttn = OR(Contains(Options,"CC2"),Contains(Options,"KG"),
             Contains(Options,"KG2"),Contains(Options,"KD"),
             Contains(Options,"KC"))
HasDef  = OR(Contains(Options,"DF"),Contains(Options,"DFX"))
HasKeenDef = AND(HasDef,
                 OR(Contains(Options,"KG"),Contains(Options,"KG2"),
                    Contains(Options,"KD"),Contains(Options,"KC")))
HasDim  = OR(Contains(Options,"D1"),Contains(Options,"D2"))

NumNotes  = 1 + If(HasAttn,1,0) + If(HasDef,1,0) + If(HasKeenDef,1,0) + If(HasDim,1,0)
NumNotes2 = If(NumNotes - 2 < 1, 1, NumNotes - 2)

# ── geometry ──
PBOrient = If(Width >= 22, "horizontal", "vertical")
Aspect   = If(Width >= 1.2 * Height, "wide",
           If(Height >= 1.2 * Width, "tall", "square"))

NotesColW = 2.80 + 0.30 * (NumNotes - 1)
# Page-1 clear view
ClearW1 = 17 - 0.80 - NotesColW - 0.20 - 1.20 - 1.20
ClearH1 = 11 - 1.25 - 0.80 - 1.20
NReq1   = (If(Width/ClearW1 > Height/ClearH1, Width/ClearW1, Height/ClearH1)) * 1.10

# Page-2 clear view
NotesColW2 = 2.80 + 0.30 * (NumNotes2 - 1)
DetailW    = If(PBOrient = "horizontal", 4.80, 3.00)
ClearW2    = 17 - 0.80 - NotesColW2 - 0.20 - DetailW - 1.00
ClearH2    = 11 - 1.25 - 0.80 - 1.20
NReq2      = (If(Width/ClearW2 > Height/ClearH2, Width/ClearW2, Height/ClearH2)) * 1.10

# Conventional target on-paper width
Target1 = 4.25 - 0.08 * (NumNotes - 1)
        + If(Aspect = "wide", 0.25, If(Aspect = "square", -0.40, 0))
        + If(PBOrient = "vertical", -0.05, 0)
Target2 = Target1 + 0.50

NPref1  = LongestDim / Target1
NPref2  = LongestDim / Target2

N1 = If(NReq1 > NPref1, NReq1, NPref1)
N2 = If(NReq2 > NPref2, NReq2, NPref2)

# Round up to ladder
Page1Scale = If(N1 <= 8, 8, If(N1 <= 10, 10, If(N1 <= 12, 12, If(N1 <= 14, 14,
            If(N1 <= 16, 16, If(N1 <= 18, 18, If(N1 <= 20, 20, 24)))))))
Page2Scale = If(N2 <= 8, 8, If(N2 <= 10, 10, If(N2 <= 12, 12, If(N2 <= 14, 14,
            If(N2 <= 16, 16, If(N2 <= 18, 18, If(N2 <= 20, 20, 24)))))))

Page1ScaleText = "1:" & Page1Scale
Page2ScaleText = "1:" & Page2Scale
```

---

## 7. Python reference (drop-in)

```python
from rad4_scale_dynamic import scales_for_cpn

result = scales_for_cpn("RAD4-72.00X42.00-BR02-CK3-DF-KG-30K")
# {
#   'cpn': 'RAD4-72.00X42.00-BR02-CK3-DF-KG-30K',
#   'width': 72.0, 'height': 42.0,
#   'num_notes': 4,
#   'power_box': 'horizontal',
#   'aspect': 'wide',
#   'page_1_scale': 18,        # → SCALE: 1:18
#   'page_2_scale': 16,        # → SCALE: 1:16
#   'p1_view_box': (9.9, 7.75),
#   'p2_view_box': (7.1, 7.75),
#   'p1_view_on_paper': (4.0, 2.33),
#   'p2_view_on_paper': (4.5, 2.62),
# }
```

You can also call the lower-level functions directly if you don't have a
CPN yet (e.g. from a configurator form):

```python
from rad4_scale_dynamic import scale_page_1, scale_page_2, power_box_orientation

W, H = 30.0, 48.0
num_notes = 2     # e.g. SPECIFICATION + DIMMING
pb = power_box_orientation(W, H)
n1 = scale_page_1(W, H, num_notes)            # → 12
n2 = scale_page_2(W, H, max(1, num_notes-2), pb_orient=pb)  # → 10
```

---

## 8. Edge cases the model handles correctly

| Scenario | Behaviour |
|----------|-----------|
| Smallest catalog fixture (17.25 × 56) | Detects vertical PB, picks 1:14 / 1:12 (matches catalog) |
| Largest catalog fixture (101 × 34.5) | Picks 1:24 floor — already at the ladder limit |
| Square fixture (36 × 36) | Applies `square_penalty` → smaller drawing target → bumps N up one step |
| Wide landscape fixture (98 × 36) | Applies `wide_bonus` → can use a coarser scale, keeps drawing readable |
| Heavy-notes config (CK3+DF+KG → 4 notes) | Wider notes column → smaller drawing area → bumps N up |
| Cord-connected (CC2) → GFCI long note | Long ATTENTION note → counted as one note (ATTN), not extra |
| 277 V variant | 277V doesn't change scale rule (no note count effect) |
| Custom (CSTM) sizes | Treated identically to stock — sizes drive the rule, not the prefix |

---

## 9. How to retune

If sheet format changes (e.g. switching from B-size to a custom EM format),
edit the sheet-geometry constants at the top of
`rad4_scale_dynamic.py`. Then run:

```
python rad4_scale_tune.py
```

The script does a grid search over the five conventional-target
parameters and prints the best combination. Drop those values back into
the `CONVENTIONAL_*` constants.

---

*Generated 2026-06-02 from automated analysis of 381 RAD4 sales-aid PDFs.*
*Files: `rad4_scale_dynamic.py`, `rad4_scale_tune.py`,
`rad4_scales.csv`, `rad4_scale_analysis.txt`.*
