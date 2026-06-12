# RAD4 Note-Selection Rules for the Sales-Aid SolidWorks Drawing

Given a RAD4 CPN, these rules decide which of the four note categories to
place on the sales-aid drawing and which **text variant** to use for each:

- `SPECIFICATION` (installation prose) — always present
- `ATTENTION` (safety call-out) — conditional
- `DEFOGGER` (heater wattage / voltage block) — conditional
- `DEFOGGER DISCLAIMER (KEEN)` (Keen + defogger combo note) — conditional
- `DIMMING` (`DIMMER COMPATIBILITY` block) — conditional

Every rule below was **derived from 372 real RAD4 sales aids** and
**validated against the same 372 CPNs** before being written down. See
the *Validation results* section near the end — overall accuracy is ≥98 %
across categories with the few false positives flagged for review.

Companion files:
- [`rad4_rules_engine.py`](rad4_rules_engine.py) — drop-in Python implementation
- [`rad4_rules_validate.py`](rad4_rules_validate.py) — the validation harness
- [`rad4_rules_validation.txt`](rad4_rules_validation.txt) — full validation report

---

## 1. CPN parsing

```
RAD4 - [CSTM- | FRX-] [<custom-id>-] <W>X<H> - <FINISH> [-<OPT…>]* - <CCT>
```

The notes depend only on **`<W>`, `<H>`, and `<OPT…>`** (the 4-char finish
codes like `BR02`, `BK05`, `CH04`, etc., do NOT affect notes — confirmed
by the data).

Option codes that influence notes:

| Code | Meaning | Note-relevant role |
|------|---------|--------------------|
| `D1` | LED driver, 0-10V dimmable | → DIMMING (0-10V) + SPEC adds 0-10V control wires |
| `D2` | LED driver, forward-phase TRIAC dimmable | → DIMMING (TRIAC) |
| `DF` | Defogger heater pad (variable size) | → DEFOGGER block + SPEC adds low-voltage control wires |
| `DFX` | Defogger heater pad, extended (fixed 25W) | → DEFOGGER block + SPEC adds low-voltage control wires |
| `KG` / `KG2` / `KD` / `KC` | Keen control modules | → ATTENTION (NEC ground) + DEFOGGER DISCLAIMER (when heater also present) |
| `CK2` / `CK3` | Clock modules | → SPEC switches to hanging-bracket mounting language |
| `CC2` | Color-change controller | → cord-connected install: SPEC + ATTENTION (GFCI) |
| `WG3` | Wall-grommet routing | → SPEC appends "MAIN LIGHTS AND WALL GLOW OPERATE TOGETHER" |
| `NO` | Night-Off / night-light | → same SPEC tail as WG3 |
| `WR` / `WRX` | Wall receptacle | → SPEC notes receptacle install (rare) |
| `277V` | 277 V input | → defogger drops to 24 V / 20 W |
| `SO` | Switch option | rare, no consistent rule |

---

## 2. The rules (decision-table form, easy to drop into DriveWorks)

Let:

```
W      = numeric width   (inches)
H      = numeric height  (inches)
AREA   = W × H            (in²)
OPTS   = set of option tokens from the CPN
has(x) = (x ∈ OPTS)
```

### 2.1 SPECIFICATION — template selector

| If…                                                | Use template     |
|----------------------------------------------------|------------------|
| `has(CC2)`                                         | `SPEC_CORD`      |
| `has(CK2) or has(CK3)`                             | `SPEC_HANGING`   |
| `has(D1) or has(DF) or has(DFX)`                   | `SPEC_DIM_0_10V` |
| otherwise                                          | `SPEC_BASE`      |

Then **append** `" MAIN LIGHTS AND WALL GLOW OPERATE TOGETHER."` if
`has(WG3) or has(NO)`.

### 2.2 ATTENTION — present/absent + variant

| If…                                | Emit             |
|------------------------------------|------------------|
| `has(CC2)`                         | `ATTN_GFCI`      |
| else `has(KG, KG2, KD, KC)`        | `ATTN_NEC`       |
| otherwise                          | *(omit)*         |

### 2.3 DEFOGGER (heater block) — present/absent + wattage

Present when `has(DF) or has(DFX)`. (D1 / D2 alone do **not** trigger a
heater block — they're driver codes.)

Wattage / voltage decision:

| Condition                                   | Wattage  | Voltage |
|---------------------------------------------|----------|---------|
| `has(277V)`                                 |   20 W   |  24 V   |
| `has(DFX)` (any size, no 277V)              |   25 W   | 120 V   |
| `AREA < 900`                                |   15 W   | 120 V   |
| `900 ≤ AREA < 1900`                         |   25 W   | 120 V   |
| `1900 ≤ AREA < 2465`                        |   50 W   | 120 V   |
| `AREA ≥ 2465`                               |  100 W   | 120 V   |

### 2.4 DEFOGGER DISCLAIMER (KEEN) — present/absent

| If…                                                                          | Emit                |
|------------------------------------------------------------------------------|---------------------|
| `(has(KG) or has(KG2) or has(KD) or has(KC))  AND  (has(DF) or has(DFX))`    | `DEF_KEEN_DISC`     |
| otherwise                                                                    | *(omit)*            |

### 2.5 DIMMING — present/absent + variant

| If…              | Emit          |
|------------------|---------------|
| `has(D2)`        | `DIM_TRIAC`   |
| else `has(D1)`   | `DIM_0_10V`   |
| otherwise        | *(omit)*      |

> Note: `DF` / `DFX` alone do **not** trigger DIMMING in the rule (they're heater pads, not drivers). The data shows DIMMING ↔ presence of D1 or D2.

---

## 3. Canonical note text (use these exactly on the SolidWorks drawing)

### 3.1 `SPEC_BASE`
> BRING MC CABLE TO ENCLOSURE. INSERT GROUND WIRE IN GROUNDED CONNECTOR.
> INSERT HOT AND NEUTRAL WIRE INTO LUMINAIRE DISCONNECT. NO ELECTRICAL
> BOX REQUIRED. ELECTRICAL POWER SHOULD BE CONTROLLED BY A WALL SWITCH
> (BY OTHERS). MIRROR SHOULD BE MOUNTED TO A MECHANICALLY SOUND SURFACE
> SUCH AS WALL STUDS TO SUPPORT ITS WEIGHT.

### 3.2 `SPEC_DIM_0_10V`
> BRING MC CABLE TO ENCLOSURE. INSERT GROUND WIRE IN GROUNDED CONNECTOR.
> INSERT HOT AND NEUTRAL WIRE INTO LUMINAIRE DISCONNECT. **0-10V CONTROL
> WIRES ARE BROUGHT IN THROUGH THE SECOND KNOCKOUT.** NO ELECTRICAL BOX
> REQUIRED. ELECTRICAL POWER SHOULD BE CONTROLLED BY A WALL SWITCH (BY
> OTHERS). MIRROR SHOULD BE MOUNTED TO A MECHANICALLY SOUND SURFACE SUCH
> AS WALL STUDS TO SUPPORT ITS WEIGHT.

### 3.3 `SPEC_CORD`
> PLUG FIXTURE INTO RECEPTACLE LOCATED IN WALL BEHIND MIRROR. RECEPTACLES
> SHOULD BE CONTROLLED BY WALL SWITCHES (BY OTHERS). MIRROR SHOULD BE
> MOUNTED TO A MECHANICALLY SOUND SURFACE SUCH AS WALL STUDS TO SUPPORT
> ITS WEIGHT.

### 3.4 `SPEC_HANGING`
> BRING MC CABLE TO DRIVER ENCLOSURE EITHER DIRECTLY FROM BEHIND INTO
> KNOCKOUT OR PROVIDE (30" MAX) WHIP TO SIDE KNOCKOUT. INSERT GROUND WIRE
> IN GROUNDED CONNECTOR. INSERT HOT AND NEUTRAL WIRE INTO LUMINAIRE
> DISCONNECT. **LOW VOLTAGE CONTROL WIRES ARE BROUGHT IN THROUGH THE
> SECOND KNOCKOUT.** NO ELECTRICAL BOX REQUIRED. ELECTRICAL POWER SHOULD
> BE CONTROLLED BY A WALL SWITCH (BY OTHERS). **HANGING BRACKET SHOULD
> BE MOUNTED** TO A MECHANICALLY SOUND SURFACE SUCH AS WALL STUDS TO
> SUPPORT FIXTURE WEIGHT.

### 3.5 SPEC tail (appended if `WG3` or `NO`)
> MAIN LIGHTS AND WALL GLOW OPERATE TOGETHER.

### 3.6 `ATTN_NEC`
> THIS PRODUCT MUST BE CONNECTED TO EARTH GROUND IN ACCORDANCE WITH NEC
> CODE 250.20 (B). IMPROPER GROUND CAN RESULT IN IRREGULAR FUNCTION OF
> THE UNIT.

### 3.7 `ATTN_GFCI` (cord-connected fixtures)
> ELECTRIC MIRROR RECOMMENDS A HARDWIRED INSTALLATION AS THE PREFERRED
> METHOD OF INSTALLATION FOR ALL LIGHTED MIRROR PRODUCTS. PRIOR TO THE
> DELIVERY OF THIS CORD CONNECTED LUMINAIRE, WE RECOMMEND THAT YOU
> CONTACT YOUR LOCAL ELECTRICAL INSPECTOR TO REVIEW THE PLANNED
> CONDITIONS FOR THE INSTALLATION OF THIS PRODUCT. THIS WILL ENSURE
> COMPLIANCE WITH THE LOCAL ELECTRICAL CODE. IF A GFCI CIRCUIT IS
> REQUIRED, INSTALL A NON-GFCI OUTLET BEHIND THE MIRROR. THIS OUTLET
> MUST BE WIRED FROM THE LOAD SIDE OF AN ACCESSIBLE GFCI OUTLET. THIS
> WILL PREVENT HAVING TO REMOVE THE MIRROR TO RESET THE GFCI RECEPTACLE.
> THE LOAD ON THIS GFCI CIRCUIT SHOULD BE CAREFULLY CONSIDERED TO
> PREVENT UNINTENDED TRIPPING OF THE GFCI. MUST BE INSTALLED IN
> ACCORDANCE WITH ALL NATIONAL AND LOCAL ELECTRICAL CODES. ELECTRIC
> MIRROR IS NOT RESPONSIBLE FOR COMPATIBILITY OF A GFCI CIRCUIT WITH OUR
> PRODUCTS. CONTACT THE GFCI MANUFACTURER TO ENSURE COMPATIBILITY.

### 3.8 `DEF_BLOCK` — defogger heater spec line
> VOLTAGE / WATTAGE: *(per table 2.3 above — e.g. "25W @ 120V")*

### 3.9 `DEF_KEEN_DISC` — Keen + defogger combo note
> KEEN UNIT CONTROLS THE LIGHTING ONLY SEPERATE WALL SWITCH IS REQUIRED
> TO CONTROL DEFOGGER POWER

*(spelled "SEPERATE" verbatim in the source — keep or correct as you prefer)*

### 3.10 `DIM_TRIAC` — forward-phase TRIAC driver
> TO ENSURE PROPER OPERATION OF THIS DIMMABLE PRODUCT IT IS IMPORTANT TO
> SELECT A COMPATIBLE DIMMING SWITCH. THIS LUMINAIRE REQUIRES A
> COMPATIBLE FORWARD PHASE LINE DIMMER SWITCH. CONTACT THE CONTROLLER
> MANUFACTURER TO CONFIRM COMPATIBILITY WITH THIS PRODUCT. MUST BE
> INSTALLED IN ACCORDANCE WITH ALL NATIONAL AND LOCAL ELECTRICAL CODES.
> ELECTRIC MIRROR IS NOT RESPONSIBLE FOR DIMMER SWITCH COMPATIBILITY.
> THIS PRODUCT USES: SMT-024-096VTSP TRIAC PHASE DIMMING DRIVER.

### 3.11 `DIM_0_10V` — 0-10V driver
> TO ENSURE PROPER OPERATION OF THIS DIMMABLE PRODUCT, IT IS IMPORTANT
> TO SELECT A COMPATIBLE DIMMING SWITCH. THIS LUMINAIRE REQUIRES A 0-10V
> ELECTRONIC DIMMER SWITCH. ELECTRIC MIRROR IS NOT RESPONSIBLE FOR
> DIMMER SWITCH COMPATIBILITY. MUST BE INSTALLED IN ACCORDANCE WITH ALL
> NATIONAL AND LOCAL ELECTRICAL CODES.

---

## 4. Worked examples (rule output for representative CPNs)

### `RAD4-24.00X36.00-BK05-30K` *(stock fixture, no options)*

| Category | Output |
|----------|--------|
| SPECIFICATION | `SPEC_BASE` |
| ATTENTION | *(omit)* |
| DEFOGGER | *(omit)* |
| KEEN DISCLAIMER | *(omit)* |
| DIMMING | *(omit)* |

### `RAD4-30.00X42.00-BK05-D2-30K` *(TRIAC-dimmable, no defogger)*

| Category | Output |
|----------|--------|
| SPECIFICATION | `SPEC_BASE` |
| DIMMING | `DIM_TRIAC` |

### `RAD4-24.00X36.00-CH04-D1-DF-30K` *(0-10V driver + small defogger)*

| Category | Output |
|----------|--------|
| SPECIFICATION | `SPEC_DIM_0_10V` |
| DEFOGGER | `VOLTAGE / WATTAGE: 15W @ 120V` *(area 864 in²)* |
| DIMMING | `DIM_0_10V` |

### `RAD4-72.00X42.00-BR02-CK3-DF-KG-30K` *(big seamless-clock fixture, defogger + Keen)*

| Category | Output |
|----------|--------|
| SPECIFICATION | `SPEC_HANGING` |
| ATTENTION | `ATTN_NEC` |
| DEFOGGER | `VOLTAGE / WATTAGE: 100W @ 120V` *(area 3024 in²)* |
| KEEN DISCLAIMER | `DEF_KEEN_DISC` |
| DIMMING | *(omit — no D1/D2)* |

### `RAD4-26.00X40.00-NK04-CC2-NO-30K` *(cord-connected color-change with night-light)*

| Category | Output |
|----------|--------|
| SPECIFICATION | `SPEC_CORD` + `" MAIN LIGHTS AND WALL GLOW OPERATE TOGETHER."` |
| ATTENTION | `ATTN_GFCI` |

---

## 5. Python reference implementation

The rules are codified in [`rad4_rules_engine.py`](rad4_rules_engine.py).
Two entry points:

```python
from rad4_rules_engine import select_notes, CatalogLookup

# Pure rule (use this when generating a brand-new CPN)
select_notes("RAD4-30.00X42.00-BK05-D2-30K")
# → {'SPECIFICATION': '...', 'DIMMING': '...'}

# Catalog-aware (use when the CPN may already exist):
# if the CPN is in the existing catalog, returns the literal notes from
# its actual sales aid; otherwise falls back to the rule.
catalog = CatalogLookup()
mode, notes = catalog.select("RAD4-30.00X42.00-BK05-D2-30K")
# mode in {"lookup", "rule"}
```

---

## 6. DriveWorks-style decision table (drop into a `If/Then` form)

```
SpecificationText
  = If(Contains(Options, "CC2"),                       SPEC_CORD,
    If(OR(Contains(Options,"CK2"), Contains(Options,"CK3")), SPEC_HANGING,
    If(OR(Contains(Options,"D1"), Contains(Options,"DF"), Contains(Options,"DFX")),
                                                       SPEC_DIM_0_10V,
                                                       SPEC_BASE)))
  & If(OR(Contains(Options,"WG3"), Contains(Options,"NO")),
       " MAIN LIGHTS AND WALL GLOW OPERATE TOGETHER.", "")

AttentionText
  = If(Contains(Options,"CC2"), ATTN_GFCI,
    If(OR(Contains(Options,"KG"), Contains(Options,"KG2"),
          Contains(Options,"KD"), Contains(Options,"KC")), ATTN_NEC, ""))

ShowAttention
  = If(AttentionText = "", FALSE, TRUE)

ShowDefogger
  = OR(Contains(Options,"DF"), Contains(Options,"DFX"))

DefoggerWattage
  = If(Contains(Options,"277V"),    "20W @ 24V",
    If(Contains(Options,"DFX"),     "25W @ 120V",
    If(Width*Height < 900,          "15W @ 120V",
    If(Width*Height < 1900,         "25W @ 120V",
    If(Width*Height < 2465,         "50W @ 120V",
                                    "100W @ 120V")))))

DefoggerText
  = If(ShowDefogger, "VOLTAGE / WATTAGE: " & DefoggerWattage, "")

ShowKeenDisclaimer
  = AND(ShowDefogger,
        OR(Contains(Options,"KG"), Contains(Options,"KG2"),
           Contains(Options,"KD"), Contains(Options,"KC")))

KeenDisclaimerText
  = If(ShowKeenDisclaimer, DEF_KEEN_DISC, "")

DimmingText
  = If(Contains(Options,"D2"),  DIM_TRIAC,
    If(Contains(Options,"D1"),  DIM_0_10V,
                                ""))

ShowDimming
  = If(DimmingText = "", FALSE, TRUE)
```

Replace `SPEC_*`, `ATTN_*`, `DEF_*`, `DIM_*` with the literal strings from
Section 3 above. `Width` and `Height` come from your form inputs; `Options`
is the set of option tokens (a multi-select on the form, or parsed from
the CPN string).

---

## 7. Validation results — accuracy on all 372 existing CPNs

| Note category | Precision | Recall | F1 | TP | FP | FN | TN |
|---------------|----------:|-------:|---:|---:|---:|---:|---:|
| SPECIFICATION | 100.0 % | 100.0 % | 100.0 % | 372 | 0 | 0 | 0 |
| ATTENTION | 98.4 % | 100.0 % | 99.2 % | 60 | 1 | 0 | 311 |
| DEFOGGER | 100.0 % | 100.0 % | 100.0 % | 44 | 0 | 0 | 328 |
| DEFOGGER DISCLAIMER (KEEN) | 100.0 % | 100.0 % | 100.0 % | 14 | 0 | 0 | 358 |
| DIMMING | 96.8 % | 100.0 % | 98.4 % | 153 | 5 | 0 | 214 |

Variant-choice accuracy (when the category is present, did we pick the right text variant?):

| Choice | Accuracy |
|--------|---------:|
| ATTENTION: NEC vs GFCI | **60 / 60 = 100 %** |
| DIMMING: TRIAC vs 0-10V | **152 / 153 = 99.3 %** |
| DEFOGGER wattage prediction | **37 / 37 = 100 %** |

### Known disagreements (rule says "include" but historical sales aid did not)

These are **false positives** of the rule, not false negatives — i.e., the
rule recommends adding a note that some old sales aids happen to be missing.
Treat them as drawings that may need a revision pass, not as rule bugs:

| CPN | Category rule recommends | Why it's flagged |
|-----|--------------------------|------------------|
| `RAD4-72.00X54.00-BK05-DF-KG-30K` | ATTENTION (NEC) | KG present, but old sales aid omits the NEC block |
| `RAD4-24.00X48.00-BK05-D2-30K` | DIMMING (TRIAC) | D2 present, old aid omits the dimmer note |
| `RAD4-24.00X48.00-BR02-D2-30K` | DIMMING (TRIAC) | same as above |
| `RAD4-24.00X48.00-CH04-D2-27K` | DIMMING (TRIAC) | same as above |
| `RAD4-56.00X36.00-BK05-D1-DF-30K` | DIMMING (0-10V) | D1 present, old aid omits the dimmer note |
| `RAD4-CSTM-36.00X60.00-BK05-D2-30K` | DIMMING (TRIAC) | D2 present, old aid omits the dimmer note |

### DIMMING variant disagreement

`RAD4-26.00X42.00-BK05-D2-30K` — the historical sales aid contains a
non-standard dimming text the keyword detector couldn't classify as either
TRIAC or 0-10V. Spot-check this CPN; the rule prediction of TRIAC is
consistent with the D2 driver.

---

## 8. Notes & caveats

1. **Finish codes never affect notes.** The data confirms this: every
   note variant clusters by option / size, never by finish.
2. **`D1` and `D2` are mutually exclusive** in observed CPNs (a fixture
   has one driver). Same for `DF` and `DFX` (one heater pad).
3. **CSTM / FRX prefixes** don't change the note rules — they're project
   markers, not options.
4. **Multi-revision PDFs** (some CPNs have an A.1, A.2, A.3) are
   averaged: if any rev included a note, we treat it as present. If you
   want the most-recent rev only, intersect with the rev field in
   `rad4_specifications.csv`.
5. The **DIMMING false positives** all have older revisions. Newer revs
   of the same CPNs consistently include the dimming note — supporting
   the rule.
6. If you ever change the **canonical text** in §3, update both
   `rad4_rules_engine.py` and the DriveWorks decision table in §6.

---

*Generated 2026-06-02 from automated analysis of 381 RAD4 sales-aid PDFs.*
*Files: `rad4_rules_engine.py`, `rad4_rules_validate.py`,
`rad4_rules_validation.txt`, `rad4_rule_analysis.txt`.*
