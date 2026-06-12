# Ready-to-paste prompt for Antigravity (or any coding agent)

Paste everything in the box below into the agent. Edit the two bracketed
sections (`PICK ONE` near the top, and `WHAT I'D LIKE FROM YOU` at the
bottom) to say what you want done. The agent has access to this whole
folder, so it can open any file referenced.

---

```
I'm building a configurator for the RAD4 LED-mirror product line that
auto-generates the sales-aid SolidWorks drawings. A prior analysis pass
reverse-engineered the rules from 381 existing sales-aid PDFs (372 unique
CPNs). All of that is in this folder. Treat the files here as GROUND
TRUTH — do not invent specs, options, notes, or scale rules that the data
doesn't support. I'd like you to [PICK ONE: audit the rules / continue
building the configurator / wire the rules into SolidWorks+DriveWorks /
answer my questions about the data].

START BY READING (in this order):
  1_START_HERE/RAD4_Configurator_Pack.md      — master briefing
  1_START_HERE/RAD4_Note_Selection_Rules.md   — which notes go on a drawing
  1_START_HERE/RAD4_Drawing_Scale_Rule.md     — page-1/page-2 scale model

GROUND-TRUTH DATA:
  data/rad4_specifications.csv   — 381 rows, one per sales aid, all specs
  data/rad4_notes.json           — every note text variant + CPN list
  data/rad4_scales.csv           — page-1/page-2 scale per PDF
  docs/RAD4_Code_Key.md          — decoder for every CPN token

WORKING CODE (portable — finds data in ../data/ automatically):
  code/rad4_rules_engine.py      — select_notes(cpn) -> {category: text}
  code/rad4_scale_dynamic.py     — scales_for_cpn(cpn) -> {page_1, page_2,…}
  code/rad4_rules_validate.py    — reproduces the accuracy report
  code/rad4_scale_tune.py        — re-tunes scale params if sheet changes

SUMMARY OF THE RULES (full detail + canonical text is in 1_START_HERE/):

CPN grammar:
  RAD4 - [CSTM-|FRX-] [<id>-] <W>X<H> - <FINISH> [-<OPT>…] - <CCT>
  Finish codes (BK05, CH04, …) do NOT affect notes or scale.
  Options that DO: D1 D2 DF DFX KG KG2 KD KC CK2 CK3 CC2 WG3 WR WRX SO NO 277V
  Mutually exclusive: {D1,D2} one driver, {DF,DFX} one heater.

Note selection (validated 97-100% across 372 CPNs):
  SPECIFICATION (always): CC2→cord text; CK2/CK3→hanging-bracket text;
     D1/DF/DFX→adds 0-10V control-wire line; else base. Append
     " MAIN LIGHTS AND WALL GLOW OPERATE TOGETHER." if WG3 or NO.
  ATTENTION: CC2→GFCI/cord warning; elif KG/KG2/KD/KC→NEC ground; else none.
  DEFOGGER (only if DF or DFX): wattage = 277V?20W@24V : DFX?25W@120V :
     area<900?15W : area<1900?25W : area<2465?50W : 100W (all @120V).
  DEFOGGER DISCLAIMER (KEEN): only if (KG/KG2/KD/KC) AND (DF/DFX).
  DIMMING: D2→TRIAC (SMT-024-096VTSP); elif D1→0-10V; else none.

Drawing scale (validated 97-98% within ±1 ladder step):
  LADDER = [8,10,12,14,16,18,20,24]
  Per page: scale_N = ceil_to_ladder(max(N_required, N_preferred))
    N_required  = max(W/clear_w, H/clear_h) * 1.10   (must-fit + 10% safety)
    N_preferred = max(W,H) / conventional_target
  conventional_target = 4.25 - 0.08*(num_notes-1)
     + 0.25 if wide(W≥1.2H)  - 0.40 if square  - 0.05 if vertical-PB(W<22")
  page-2 target = +0.50 (fewer notes on page 2 → bigger drawing)
  power_box_orientation = horizontal if W≥22" else vertical
  clear_w/clear_h shrink with note count (right-column width) and, on
  page 2, with the DETAIL A power-box block (horiz 4.8×3.0 / vert 3.0×4.8).
  Page 1 and Page 2 can therefore land on different scales.

Constants on EVERY RAD4 (never make selectable): LED replaceable flex
strip, 302 lm/ft, CRI 90+, L70 140,000 hrs, 0.59" off-wall, 2.03" depth,
frosted diffuser, ±1/8" tolerance, base powerbox 81330-96W.

OPEN ITEMS the sales aids cannot answer (flag as TODO, do not guess):
  1. SolidWorks geometry rules (which dims/equations drive W×H)
  2. Title-block custom-property field names on the RAD4 template
  3. Vault paths for RAD4 master assemblies / frame components
  4. Pricing   5. Lead times

WHAT I'D LIKE FROM YOU:
  [Replace with your specific ask, e.g.:
   - Generate the DriveWorks rule expressions + property links that wire
     Width/Height/Options form inputs to the note text and both page scales.
   - Write the Python pipeline that, given a CPN, opens a SolidWorks
     drawing template, sets both page scales, fills the notes, and exports
     a PDF.
   - Spot-check the rules against 20 random CPNs from
     data/rad4_specifications.csv and report any disagreements.
   - Audit the rules for engineering plausibility and flag anything off.]
```
