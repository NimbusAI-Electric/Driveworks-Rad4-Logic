# RAD4 Configurator — Source-of-Truth Briefing Pack

This pack is the briefing for a coding agent (Google Antigravity or equivalent) that is **building the RAD4 product configurator** (DriveWorks project or a Python replacement of one).

Everything below was extracted by parsing **381 RAD4 sales-aid PDFs** in `D:\EM-HV-04 Backup 5-14-2026\Sales Aids\`. **Do not invent specs the data does not support** — every rule must be derivable from the data files or expressly noted below.

Companion data files (give these to the agent verbatim):

| File | What it is |
|------|------------|
| `rad4_specifications.csv` | Master lookup table — one row per CPN, all numeric specs |
| `rad4_specifications.json` | Same data as JSON (preferred for programmatic ingestion) |
| `rad4_notes.json` | Every distinct prose-note variant per category, with the CPN list using it |
| `RAD4_Code_Key.md` | Decoded meaning of every CPN token |
| `RAD4_Specifications_Map.md` | Human-readable summary tables (optional, for sanity checks) |

---

## 1. CPN structure (the only thing a configurator needs to produce)

```
RAD4 - [CSTM- | FRX-] [<custom-id>-] <WIDTH>X<HEIGHT> - <FINISH> [-<OPT1>...-<OPTN>] - <CCT>
```

| Token | Type | Examples | Notes |
|-------|------|----------|-------|
| `RAD4` | literal | — | always present |
| `CSTM` / `FRX` | optional prefix | `RAD4-CSTM-…`, `RAD4-FRX-…` | non-stock variants |
| `<custom-id>` | optional 5-digit | `85285`, `84497`, `85294` | Custom project number; rare |
| `<WIDTH>X<HEIGHT>` | required | `24.00X36.00` | inches, two-decimal places, literal `X` |
| `<FINISH>` | required, single token | `BK05`, `BR02`, `CH04`, `NK04`, `BZ24`, `BZ47`, `CH11`, `BK147` | see §3 |
| `<OPT…>` | 0..N tokens | `D1`, `D2`, `DF`, `DFX`, `KG`, `KG2`, `KD`, `KC`, `CK2`, `CK3`, `CC2`, `WG3`, `WR`, `WRX`, `SO`, `NO`, `277V` | see §4 |
| `<CCT>` | required final token | `27K`, `30K`, `35K` | 2700 / 3000 / 3500 K |

European market variant uses prefix `E-RAD4-…` and 220-240 V input. Treat it as a market flag on the same CPN.

Examples:

```
RAD4-24.00X36.00-BK05-30K               # stock, no options
RAD4-30.00X42.00-BK05-D2-30K            # + defogger D2
RAD4-72.00X42.00-BR02-CK3-DF-KG-30K     # seamless clock + defogger + Keen
RAD4-CSTM-55.00X60.00-BK05-D2-30K       # custom size
RAD4-FRX-24.00X42.00-BZ47-KC-30K        # FRX variant
```

---

## 2. Configurator inputs (form controls)

The agent should expose **exactly these inputs** — they are the only degrees of freedom observed:

1. **Width** — decimal inches, two decimals, range observed `17.25" – 98.00"`
2. **Height** — decimal inches, two decimals, range observed `20.00" – 101.00"`
3. **Frame finish** — one of the 8 finishes (§3)
4. **CCT** — `2700K` / `3000K` / `3500K`
5. **Defogger** — `None` / `D1` / `D2` / `DF` / `DFX`  *(mutually exclusive — never seen combined in any CPN)*
6. **Control package** — `None` / `KG` (Keen 1-Touch) / `KG2` (Keen v2) / `KD` (Keen Dimmer) / `KC` (Keen Clock)
7. **Clock** — `None` / `CK2` / `CK3` (Seamless)
8. **Color-change** — `None` / `CC2`
9. **Wiring/install routing** — `None` / `WG3` (Wall-Grommet) / `WR` (Wall Receptacle) / `WRX` (Receptacle Extended)
10. **Switch option** — `None` / `SO`
11. **Night-Light** — `None` / `NO`
12. **Input voltage** — `Standard (120 OR 277 V)` / `277V` (explicit) / `European 220-240 V`

Series flag: `Stock` / `CSTM (custom size)` / `FRX`.

---

## 3. Frame-finish codes (from `RAD4_Code_Key.md`)

| Code | Finish | CPN count |
|------|--------|-----------|
| `BK05` | Matte Black | 159 |
| `CH04` | Chrome / Etched Chrome | 130 |
| `BR02` | Brushed Brass | 49 |
| `NK04` | Brushed Nickel | 17 |
| `BZ47` | Bronze (BZ47) | 14 |
| `BZ24` | Bronze (BZ24) | 9 |
| `CH11` | Chrome (CH11) | 2 |
| `BK147` | Matte Black (BK147) | 1 |

---

## 4. Option codes & observed compatibility

| Code | Meaning | # CPNs |
|------|---------|-------|
| `D2` | Defogger D2 | 106 |
| `D1` | Defogger D1 | 55 |
| `DF` | Defogger (DF) | 36 |
| `DFX` | Defogger DFX (Extended) | 10 |
| `KG` | Keen 1-Touch Control | 40 |
| `KG2` | Keen 1-Touch v2 | 3 |
| `KD` | Keen Dimmer | 5 |
| `KC` | Keen Clock | 9 |
| `CK2` | Clock CK2 | 11 |
| `CK3` | Seamless Clock CK3 | 2 |
| `CC2` | Color-Change CC2 | 9 |
| `WG3` | Wall-Grommet routing | 29 |
| `WR` | Wall Receptacle | 1 |
| `WRX` | Wall Receptacle Extended | 1 |
| `SO` | Switch Option | 1 |
| `NO` | Night-Off / Night-Light | 13 |
| `277V` | 277 V Input | 3 |

**Top observed option combinations (32 distinct sets across 381 CPNs):**

```
123   (no options)
 99   D2
 25   D1
 22   KG
 20   D1 + DF
 12   WG3
  8   DFX + KG
  7   CK2 + D1
  7   DF
  6   D2 + WG3
  6   NO + WG3
  6   KC
  5   CC2 + NO
  4   KD
  4   CK2
```

**Compatibility rule the agent must enforce:** the four defogger codes `D1`, `D2`, `DF`, `DFX` are **mutually exclusive** — they never co-occur in any observed CPN.

---

## 5. Computed outputs (what the configurator produces per selection)

### 5.1 Numeric specs to compute / look up
Source rows in `rad4_specifications.csv`:

| Output field | Source column | How to derive |
|--------------|---------------|---------------|
| Total fixture wattage | `led_wattage_W` | LED watts ≈ size-driven; see §6 |
| Input voltage | `voltage_V` | Determined by voltage selection (§2 input #12) |
| Input current (A) | `current_A` | wattage ÷ voltage |
| LED length (in) | `led_length_in` | size-driven (≈ perimeter minus framing) |
| Lumens (initial) | `lumens_total` | LED length × 302 lm/ft |
| Lumens per ft | constant `302` | invariant — never configurable |
| CRI | constant `90+` | invariant |
| L70 lifespan | constant `140,000 hrs` | invariant |
| Fixture weight | `weight_lbs` | size-driven; lookup or interpolate |
| Power-box model | `powerbox` | option-driven; see §5.2 |
| Defogger V / W | `defogger_voltage`, `defogger_wattage` | only when defogger selected (§5.3) |
| Clock spec | constants | only when `CK2`/`CK3` selected (§5.4) |

### 5.2 Power-box (driver enclosure) model
The powerbox suffix mirrors the option codes selected. From `RAD4_Code_Key.md` "Power-Box Models" section:

| Powerbox | Trigger |
|----------|---------|
| `81330-96W` | base (no Keen / no clock / no color-change) |
| `81330-192W` | larger fixtures (~`WG3` plus LED length > ~134") |
| `81330-D1-96W`, `81330-D2-96W` | + corresponding defogger |
| `81330-DF-96W`, `81330-D1-DF-96W`, `81330-D1-DFX-96W`, `81330-D2-DF-96W` | + defogger combinations |
| `81330-K-96W`, `81330-K2-192W`, `81330-DF-K-96W` | + Keen (`-K` = Keen, `-K2` = KG2 v2) |
| `81330-CK2-96W`, `81330-CK2-D1-96W`, `81330-CK3-DF-K-96W` | + clock |
| `81330-CC2-96W`, `81330-CC2-K-96W` | + color-change |

**Algorithm:** concatenate the option flags in the canonical order `CK*`, `CC*`, `D*`, `DF*`, `K*`, then size suffix (`96W` baseline, `192W` for high-power). The full observed list is in `RAD4_Code_Key.md` — use that as the lookup table rather than computing from scratch.

### 5.3 Defogger spec (only when defogger selected)
From `rad4_notes.json` → category `DEFOGGER`:

| Defogger watts | When |
|----------------|------|
| `15 W @ 120 V` | small (~24"x36") `D1+DF` |
| `25 W @ 120 V` | mid (~26–48") `D1`/`D2`/`DF`/`DFX` |
| `50 W @ 120 V` | larger (~34–56") `DF` |
| `100 W @ 120 V` | largest (~42–72") `D1+DF`, `DF+KG` |

Use the actual CPN→wattage mapping in `rad4_notes.json` rather than inferring — the relationship to size is monotonic but not perfectly linear.

### 5.4 Clock spec (when `CK2` or `CK3` selected)
Always: plug-in external 5 V power supply, 120 V input, 50–60 Hz, **2.0 W**. Source: `rad4_notes.json` → category `CLOCK`.

---

## 6. Constants (the configurator must NOT make these selectable)

| Spec | Value |
|------|-------|
| LED type | Replaceable flex strip |
| Lumens per foot | 302 lm/ft |
| CRI | 90+ |
| Calculated L70 lifespan | 140,000 hrs |
| Frame depth off wall | 0.59" |
| Total fixture depth | 2.03" |
| Diffuser type | Frosted |
| Section profile (frosted / LED / mirror) | 1.44" × 0.99" × 0.53" |
| Tolerance | ±1/8" [±3 mm] |

---

## 7. Drawing-note generation (the prose blocks on the sales aid)

The sales-aid PDF carries **five categories of prose notes** that the configurator must select and place. All variants live in `rad4_notes.json`.

### 7.1 SPECIFICATION (installation prose) — **always present**
73 observed variants. Selection key (in priority order):
1. **Cable type** — `MC CABLE` vs `CABLE`
2. **Whip length** — `15"` / `18"` / `30"` / `36"` MAX (size-driven; check `rad4_notes.json` cpn list)
3. **Dimming control wires** — none / `0-10V CONTROL WIRES` / `LOW VOLTAGE CONTROL WIRES` (only when a Keen / dimmable driver is present)
4. **Mounting term** — `MIRROR` / `DRIVER ENCLOSURE` / `FIXTURE`

The configurator should fetch the matching variant by CPN from `rad4_notes.json` rather than templating it from scratch — every variant is already proven against a real CPN. Fall back to the most-common variant (102 CPNs, `BRING MC CABLE TO ENCLOSURE…`) if a new CPN is generated.

### 7.2 ATTENTION — **present on Keen / dimmable / defogger CPNs (60 CPNs)**
- Main variant (48 CPNs): NEC 250.20(B) earth-ground warning
- Cord-connected variant (12 CPNs): GFCI / electrical-inspector recommendation

Trigger: include the main variant whenever the fixture is dimmable or has a defogger / Keen package.

### 7.3 DEFOGGER block — **present when defogger option selected**
15 variants — VOLTAGE/WATTAGE callout. Look up by defogger code + size bracket. See §5.3.

### 7.4 DEFOGGER DISCLAIMER (KEEN) — **present when KG/KG2 + any defogger**
Single canonical text (14 CPNs):
> *"KEEN UNIT CONTROLS THE LIGHTING ONLY SEPARATE WALL SWITCH IS REQUIRED TO CONTROL DEFOGGER POWER"*

Trigger: `(KG or KG2) AND (D1 or D2 or DF or DFX)`.

### 7.5 DIMMING (DIMMER COMPATIBILITY) — **present on dimmable units (154 CPNs)**
Two main variants:
- **TRIAC forward-phase** (77 CPNs) — driver `SMT-024-096VTSP`
- **0-10V electronic** (29 CPNs)

The choice is **driven by the driver, not the size** — pick from `rad4_notes.json` per the powerbox model. If powerbox = `81330-…D2-…` → 0-10V. If powerbox = base `81330-96W` or `81330-K-96W` → TRIAC. Verify against `rad4_notes.json` CPN lists when in doubt.

### 7.6 Other notes encountered
| Category | When |
|----------|------|
| `CLOCK POWER REQUIREMENTS` | `CK2` / `CK3` selected (12 CPNs) |
| `WALL GLOW LED SPECIFICATION` | wall-glow variants (21 CPNs) |
| `PRODUCT USES` | specific driver call-outs (7 CPNs) |
| `POWER BOX REF` | powerbox model reference block (37 CPNs) |
| `INNER FRAME FINISH` | multi-finish frames (3 CPNs) |
| `DFX CALLOUT` | dimensional callout for DFX defogger (7 CPNs) |
| `KG2 CALLOUT` | Keen v2 control-button placement (3 CPNs) |
| `CSTM CALLOUT` | custom-size dimensional note (3 CPNs) |

Full text + per-CPN list lives in `rad4_notes.json`. See `RAD4_Notes_Map.md` for the human-readable view.

---

## 8. BOM contribution per option (inference rules)

Derivable from the powerbox suffix + option codes, not directly extracted as a BOM. The agent should generate the BOM from these rules:

| If selection includes… | Add line item |
|------------------------|---------------|
| any defogger | defogger pad (size-matched) + heater controller |
| `KG` / `KG2` | Keen control module |
| `KD` | Keen dimmer module |
| `KC` | Keen clock module |
| `CK2` / `CK3` | clock module + 5 V power supply |
| `CC2` | color-change controller |
| `WG3` | wall-grommet hardware |
| `WR` / `WRX` | wall receptacle |
| `NO` | night-light board |

The powerbox model itself (per §5.2) is also a BOM line.

---

## 9. Data files reference — schema cheat sheet

### 9.1 `rad4_specifications.csv` columns
```
file, cpn, revision,
cpn_model, cpn_custom_prefix, cpn_size, cpn_finish_code, cpn_finish_name,
cpn_cct_code, cpn_cct_K, cpn_is_custom, cpn_is_frx, cpn_options, cpn_option_meanings,
frame_finish, total_wattage_W, voltage_V, current_A,
led_type, led_length_in, led_wattage_W, l70_lifespan_hrs, cct_K,
lumens_total, lumens_per_ft, cri, weight_lbs,
has_defogger, defogger_voltage, defogger_wattage,
has_clock, clock_watts, has_keen, has_277v, has_dimmer_kd,
powerbox, mirror_assembly, powerbox_assembly,
cpn_in_pdf, cpn_from_filename
```

### 9.2 `rad4_notes.json` schema
```json
{
  "SPECIFICATION": [
    {
      "text": "BRING MC CABLE TO ENCLOSURE...",
      "alt_texts": ["..."],
      "original_header": "SPECIFICATION",
      "cpn_count": 102,
      "file_count": 102,
      "cpns": ["RAD4-21.00X36.00-BR02-D2-30K", "..."],
      "files": ["RAD4-21.00X36.00-BR02-D2-30K-SALES-AID-A.1.PDF", "..."]
    },
    …
  ],
  "ATTENTION": [...],
  "DEFOGGER": [...],
  "DEFOGGER DISCLAIMER (KEEN)": [...],
  "DIMMING": [...],
  "CLOCK": [...],
  "WALL GLOW": [...],
  "PRODUCT USES": [...],
  "POWER BOX REFERENCE": [...],
  ...
}
```

---

## 10. Open items the configurator owner must resolve (NOT in the data)

The PDFs don't reveal these — the agent must NOT guess:

1. **Geometry rules** — how size + finish + options drive the SolidWorks model dimensions / configurations. Needs the SolidWorks vault and/or `logic_engine`-style rules from a domain SME.
2. **Custom-property field names** in the title block — likely match the JS3 convention (`Number, Description, Revision, Date, Author, PowerBoxConfig`) but verify on a RAD4 template.
3. **Vault paths** for RAD4 master assemblies and frame components. The JS3 project uses `D:\EM_Vault\Products\JS3\…` — confirm the RAD4 equivalent before hardcoding.
4. **Price / cost data** — not in the sales aids.
5. **Lead times / availability** — not in the sales aids.

---

*Generated 2026-06-01 from automated analysis of 381 RAD4 sales-aid PDFs.*
