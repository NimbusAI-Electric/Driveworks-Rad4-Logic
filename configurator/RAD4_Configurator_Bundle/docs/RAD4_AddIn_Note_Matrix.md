# RAD4 Add-In → Note Association Matrix

**Question answered:** for every add-in code that can appear in a RAD4 CPN
(e.g. `-D2`, `-DF`, `-KG`), which notes appear on the sales aids that have it?

**Coverage:** every RAD4 sales aid was read — 381 PDFs → **372 unique CPNs**, all accounted for below. Wording variance is collapsed: any variant of a note counts as that note being present (the exact texts live in `rad4_notes.json` / `RAD4_Notes_Map.md`).

**Method note on co-occurring add-ins:** when two add-ins always appear together (e.g. `DFX` is always with `KG`), a note on those sales aids could belong to either. To resolve ownership, each add-in section below shows the **solo evidence** — CPNs where that add-in is the *only* one present — which isolates what the add-in itself brings.

---

## Baseline — CPNs with NO add-ins (119 CPNs)

Example: `RAD4-36.00X36.00-CH04-30K`

| Note | CPNs with it | Share |
|------|-------------:|------:|
| SPECIFICATION | 119/119 | 100% |
| POWER BOX REFERENCE | 11/119 | 9% |

A plain RAD4 with no add-ins carries **only the SPECIFICATION (installation) note**. Every other note is brought in by an add-in. (POWER BOX REFERENCE is a generic drawing-reference block that newer-revision sheets print regardless of options — it is not tied to any add-in.)

---

## 1. The matrix — % of CPNs with each add-in that carry each note

| Add-in | #CPNs | SPEC | ATTN | DEFOG | KEEN-DISC | DIM | CLOCK | WGLOW | USES | PBREF |
|---|---|---|---|---|---|---|---|---|---|---|
| *(none)* | 119 | 100% | — | — | — | — | — | — | — | 9% |
| `D1` | 54 | **100%** | — | **40%** | — | **98%** | **12%** | — | — | — |
| `D2` | 104 | **100%** | — | **0%** | — | **96%** | — | **5%** | **6%** | **19%** |
| `DF` | 34 | **100%** | **14%** | **100%** | **17%** | **58%** | **2%** | — | — | — |
| `DFX` | 10 | **100%** | **80%** | **100%** | **80%** | **20%** | — | — | — | — |
| `KG` | 39 | **100%** | **97%** | **30%** | **30%** | — | **2%** | **2%** | — | **2%** |
| `KG2` | 3 | **100%** | **100%** | — | — | — | — | **100%** | — | **66%** |
| `KD` | 4 | **100%** | **100%** | **25%** | **25%** | — | — | — | — | — |
| `KC` | 9 | **100%** | **100%** | **11%** | **11%** | — | — | — | — | — |
| `CK2` | 11 | **100%** | — | — | — | **63%** | **100%** | — | — | — |
| `CK3` | 1 | **100%** | **100%** | **100%** | **100%** | — | **100%** | — | — | — |
| `CC2` | 9 | **100%** | **100%** | — | — | — | — | — | — | **22%** |
| `WG3` | 29 | **100%** | **17%** | — | — | **20%** | — | **72%** | — | **17%** |
| `WR` | 1 | **100%** | **100%** | — | — | — | — | — | — | — |
| `WRX` | 1 | **100%** | **100%** | — | — | — | — | — | — | **100%** |
| `SO` | 1 | **100%** | — | — | — | — | — | — | — | — |
| `NO` | 13 | **100%** | **38%** | — | — | — | — | **46%** | — | **15%** |
| `277V` | 3 | **100%** | — | **33%** | — | **33%** | — | — | — | **33%** |

Read: `D2` row, DIM column = % of all D2 CPNs whose sales aid has a dimming note.

---

## 2. Per-add-in findings (with solo evidence and every exception)

### `D1` — Defogger driver pkg D1 (0-10V dimmable driver)

Appears in **54 CPNs**; alone (no other add-in) in **25**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 54/54 (100%) | 25/25 (100%) |
| DEFOGGER | 22/54 (40%) | 0/25 (0%) |
| DIMMING | 53/54 (98%) | 25/25 (100%) |
| CLOCK | 7/54 (12%) | 0/25 (0%) |

**What `D1` itself brings:** **DIMMING** (based on solo CPNs).

**Exceptions** (CPNs with this add-in that are missing the expected note):

- `RAD4-56.00X36.00-BK05-D1-DF-30K` — has `D1` but no DIMMING note on its sales aid

---

### `D2` — Defogger driver pkg D2 (TRIAC dimmable driver)

Appears in **104 CPNs**; alone (no other add-in) in **97**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 104/104 (100%) | 97/97 (100%) |
| DEFOGGER | 1/104 (0%) | 0/97 (0%) |
| DIMMING | 100/104 (96%) | 93/97 (95%) |
| WALL GLOW | 6/104 (5%) | 0/97 (0%) |
| PRODUCT USES | 7/104 (6%) | 7/97 (7%) |
| POWER BOX REFERENCE | 20/104 (19%) | 17/97 (17%) |

**What `D2` itself brings:** **DIMMING** (based on solo CPNs).

**Exceptions** (CPNs with this add-in that are missing the expected note):

- `RAD4-24.00X48.00-BK05-D2-30K` — has `D2` but no DIMMING note on its sales aid
- `RAD4-24.00X48.00-BR02-D2-30K` — has `D2` but no DIMMING note on its sales aid
- `RAD4-24.00X48.00-CH04-D2-27K` — has `D2` but no DIMMING note on its sales aid
- `RAD4-CSTM-36.00X60.00-BK05-D2-30K` — has `D2` but no DIMMING note on its sales aid

---

### `DF` — Defogger heater pad

Appears in **34 CPNs**; alone (no other add-in) in **7**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 34/34 (100%) | 7/7 (100%) |
| ATTENTION | 5/34 (14%) | 0/7 (0%) |
| DEFOGGER | 34/34 (100%) | 7/7 (100%) |
| DEFOGGER DISCLAIMER (KEEN) | 6/34 (17%) | 0/7 (0%) |
| DIMMING | 20/34 (58%) | 0/7 (0%) |
| CLOCK | 1/34 (2%) | 0/7 (0%) |

**What `DF` itself brings:** **DEFOGGER** (based on solo CPNs).

---

### `DFX` — Defogger heater pad, extended

Appears in **10 CPNs**; alone (no other add-in) in **0**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 10/10 (100%) | n/a (never solo) |
| ATTENTION | 8/10 (80%) | n/a (never solo) |
| DEFOGGER | 10/10 (100%) | n/a (never solo) |
| DEFOGGER DISCLAIMER (KEEN) | 8/10 (80%) | n/a (never solo) |
| DIMMING | 2/10 (20%) | n/a (never solo) |

**Never appears alone** — always with: `KG` (8×), `D1` (2×). Note ownership inferred from partners' solo behaviour.

**Exceptions** (CPNs with this add-in that are missing the expected note):

- `RAD4-32.69X46.94-BK05-D1-DFX-30K` — has `DFX` but no ATTENTION note on its sales aid
- `RAD4-34.00X54.00-BR02-D1-DFX-30K` — has `DFX` but no ATTENTION note on its sales aid
- `RAD4-32.69X46.94-BK05-D1-DFX-30K` — has `DFX` but no DEFOGGER DISCLAIMER (KEEN) note on its sales aid
- `RAD4-34.00X54.00-BR02-D1-DFX-30K` — has `DFX` but no DEFOGGER DISCLAIMER (KEEN) note on its sales aid

---

### `KG` — Keen 1-Touch control

Appears in **39 CPNs**; alone (no other add-in) in **22**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 39/39 (100%) | 22/22 (100%) |
| ATTENTION | 38/39 (97%) | 22/22 (100%) |
| DEFOGGER | 12/39 (30%) | 0/22 (0%) |
| DEFOGGER DISCLAIMER (KEEN) | 12/39 (30%) | 0/22 (0%) |
| CLOCK | 1/39 (2%) | 0/22 (0%) |
| WALL GLOW | 1/39 (2%) | 0/22 (0%) |
| POWER BOX REFERENCE | 1/39 (2%) | 0/22 (0%) |

**What `KG` itself brings:** **ATTENTION** (based on solo CPNs).

**Exceptions** (CPNs with this add-in that are missing the expected note):

- `RAD4-72.00X54.00-BK05-DF-KG-30K` — has `KG` but no ATTENTION note on its sales aid

---

### `KG2` — Keen 1-Touch v2

Appears in **3 CPNs**; alone (no other add-in) in **0**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 3/3 (100%) | n/a (never solo) |
| ATTENTION | 3/3 (100%) | n/a (never solo) |
| WALL GLOW | 3/3 (100%) | n/a (never solo) |
| POWER BOX REFERENCE | 2/3 (66%) | n/a (never solo) |

**Never appears alone** — always with: `WG3` (3×). Note ownership inferred from partners' solo behaviour.

---

### `KD` — Keen Dimmer

Appears in **4 CPNs**; alone (no other add-in) in **3**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 4/4 (100%) | 3/3 (100%) |
| ATTENTION | 4/4 (100%) | 3/3 (100%) |
| DEFOGGER | 1/4 (25%) | 0/3 (0%) |
| DEFOGGER DISCLAIMER (KEEN) | 1/4 (25%) | 0/3 (0%) |

**What `KD` itself brings:** **ATTENTION** (based on solo CPNs).

---

### `KC` — Keen Clock

Appears in **9 CPNs**; alone (no other add-in) in **6**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 9/9 (100%) | 6/6 (100%) |
| ATTENTION | 9/9 (100%) | 6/6 (100%) |
| DEFOGGER | 1/9 (11%) | 0/6 (0%) |
| DEFOGGER DISCLAIMER (KEEN) | 1/9 (11%) | 0/6 (0%) |

**What `KC` itself brings:** **ATTENTION** (based on solo CPNs).

---

### `CK2` — Clock CK2

Appears in **11 CPNs**; alone (no other add-in) in **4**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 11/11 (100%) | 4/4 (100%) |
| DIMMING | 7/11 (63%) | 0/4 (0%) |
| CLOCK | 11/11 (100%) | 4/4 (100%) |

**What `CK2` itself brings:** **CLOCK** (based on solo CPNs).

---

### `CK3` — Seamless Clock CK3

Appears in **1 CPNs**; alone (no other add-in) in **0**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 1/1 (100%) | n/a (never solo) |
| ATTENTION | 1/1 (100%) | n/a (never solo) |
| DEFOGGER | 1/1 (100%) | n/a (never solo) |
| DEFOGGER DISCLAIMER (KEEN) | 1/1 (100%) | n/a (never solo) |
| CLOCK | 1/1 (100%) | n/a (never solo) |

**Never appears alone** — always with: `KG` (1×), `DF` (1×). Note ownership inferred from partners' solo behaviour.

---

### `CC2` — Color-change CC2 (cord-connected)

Appears in **9 CPNs**; alone (no other add-in) in **1**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 9/9 (100%) | 1/1 (100%) |
| ATTENTION | 9/9 (100%) | 1/1 (100%) |
| POWER BOX REFERENCE | 2/9 (22%) | 0/1 (0%) |

**What `CC2` itself brings:** no extra note beyond SPECIFICATION (solo CPNs carry only the installation note).

---

### `WG3` — Wall Glow w/ grommet routing

Appears in **29 CPNs**; alone (no other add-in) in **12**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 29/29 (100%) | 12/12 (100%) |
| ATTENTION | 5/29 (17%) | 0/12 (0%) |
| DIMMING | 6/29 (20%) | 0/12 (0%) |
| WALL GLOW | 21/29 (72%) | 5/12 (41%) |
| POWER BOX REFERENCE | 5/29 (17%) | 0/12 (0%) |

**What `WG3` itself brings:** usually **WALL GLOW** (based on solo CPNs).

---

### `WR` — Wall Receptacle

Appears in **1 CPNs**; alone (no other add-in) in **0**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 1/1 (100%) | n/a (never solo) |
| ATTENTION | 1/1 (100%) | n/a (never solo) |

**Never appears alone** — always with: `KG` (1×). Note ownership inferred from partners' solo behaviour.

---

### `WRX` — Wall Receptacle extended

Appears in **1 CPNs**; alone (no other add-in) in **0**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 1/1 (100%) | n/a (never solo) |
| ATTENTION | 1/1 (100%) | n/a (never solo) |
| POWER BOX REFERENCE | 1/1 (100%) | n/a (never solo) |

**Never appears alone** — always with: `KG` (1×). Note ownership inferred from partners' solo behaviour.

---

### `SO` — Switch Option

Appears in **1 CPNs**; alone (no other add-in) in **1**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 1/1 (100%) | 1/1 (100%) |

**What `SO` itself brings:** no extra note beyond SPECIFICATION (solo CPNs carry only the installation note).

---

### `NO` — Night-Off / night-light

Appears in **13 CPNs**; alone (no other add-in) in **2**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 13/13 (100%) | 2/2 (100%) |
| ATTENTION | 5/13 (38%) | 0/2 (0%) |
| WALL GLOW | 6/13 (46%) | 0/2 (0%) |
| POWER BOX REFERENCE | 2/13 (15%) | 0/2 (0%) |

**What `NO` itself brings:** no extra note beyond SPECIFICATION (solo CPNs carry only the installation note).

---

### `277V` — 277 V input

Appears in **3 CPNs**; alone (no other add-in) in **2**.

| Note | All CPNs with this add-in | Solo CPNs only |
|------|---------------------------|----------------|
| SPECIFICATION | 3/3 (100%) | 2/2 (100%) |
| DEFOGGER | 1/3 (33%) | 0/2 (0%) |
| DIMMING | 1/3 (33%) | 0/2 (0%) |
| POWER BOX REFERENCE | 1/3 (33%) | 1/2 (50%) |

**What `277V` itself brings:** no extra note beyond SPECIFICATION (solo CPNs carry only the installation note).

---

## 3. Reverse view — each note and the add-ins that bring it

### ATTENTION — on 60 CPNs

Add-ins present on those CPNs: `KG` 38×, `KC` 9×, `CC2` 9×, `DFX` 8×, `DF` 5×, `NO` 5×, `WG3` 5×, `KD` 4×, `KG2` 3×, `WR` 1×, `WRX` 1×, `CK3` 1×

### DEFOGGER — on 44 CPNs

Add-ins present on those CPNs: `DF` 34×, `D1` 22×, `KG` 12×, `DFX` 10×, `277V` 1×, `D2` 1×, `KC` 1×, `KD` 1×, `CK3` 1×

### DEFOGGER DISCLAIMER (KEEN) — on 14 CPNs

Add-ins present on those CPNs: `KG` 12×, `DFX` 8×, `DF` 6×, `KC` 1×, `KD` 1×, `CK3` 1×

### DIMMING — on 153 CPNs

Add-ins present on those CPNs: `D2` 100×, `D1` 53×, `DF` 20×, `CK2` 7×, `WG3` 6×, `DFX` 2×, `277V` 1×

### CLOCK — on 12 CPNs

Add-ins present on those CPNs: `CK2` 11×, `D1` 7×, `KG` 1×, `DF` 1×, `CK3` 1×

### WALL GLOW — on 21 CPNs

Add-ins present on those CPNs: `WG3` 21×, `D2` 6×, `NO` 6×, `KG2` 3×, `KG` 1×

### PRODUCT USES — on 7 CPNs

Add-ins present on those CPNs: `D2` 7×

### POWER BOX REFERENCE — on 37 CPNs

Add-ins present on those CPNs: `D2` 20×, `WG3` 5×, `NO` 2×, `CC2` 2×, `KG2` 2×, `277V` 1×, `KG` 1×, `WRX` 1×, *(no add-in)* 11×

---

## 4. Plain-English summary (the rule of thumb you asked for)

| Add-in in CPN | Notes it puts on the sales aid |
|---------------|--------------------------------|
| *(none)* | SPECIFICATION only |
| `D1` | DIMMING (0-10V) — *not* a defogger-spec note by itself |
| `D2` | DIMMING (TRIAC) — *not* a defogger-spec note by itself |
| `DF` | DEFOGGER (heater V/W block); + KEEN-DISCLAIMER when a Keen code is also present |
| `DFX` | DEFOGGER + ATTENTION + KEEN-DISCLAIMER (always rides with `KG`) |
| `KG` / `KG2` / `KD` / `KC` | ATTENTION (NEC earth-ground) |
| `CK2` / `CK3` | CLOCK power note; SPEC switches to hanging-bracket wording |
| `CC2` | SPEC switches to cord-connected; ATTENTION switches to the long GFCI text |
| `WG3` | WALL GLOW spec block; SPEC gains "MAIN LIGHTS AND WALL GLOW OPERATE TOGETHER" |
| `NO` | rides with wall-glow models; GFCI-style ATTENTION when cord-connected |
| `WR` / `WRX` / `SO` | one-off CPNs; no consistent extra note |
| `277V` | changes voltages inside existing notes; adds no new note category |

*Generated by `rad4_addin_note_matrix.py` from all 381 RAD4 sales aids. Exact note wording variants: `rad4_notes.json`. Numeric specs: `rad4_specifications.csv`.*