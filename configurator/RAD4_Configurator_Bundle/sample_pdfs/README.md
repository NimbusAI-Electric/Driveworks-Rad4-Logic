# Sample Sales-Aid PDFs — one per note pattern

These 10 PDFs are the **visual ground truth** for note formatting: header
style (`SPECIFICATION:` bold + body text below), line wrapping, the
right-column note stack order, title block, and sheet scale per page.
The extracted text files (`data/rad4_notes.json`) carry the wording;
these PDFs carry the layout.

| PDF | Demonstrates |
|-----|--------------|
| `RAD4-24.00X36.00-BK05-30K-…A.2.pdf` | Baseline, no add-ins → SPECIFICATION note only |
| `RAD4-30.00X42.00-BK05-D2-30K-…` | `D2` → DIMMING (TRIAC forward-phase) note |
| `RAD4-24.00X36.00-CH04-D1-DF-30K-…` | `D1`+`DF` → 0-10V DIMMING + DEFOGGER block + 0-10V control-wire line in SPEC |
| `RAD4-48.00X36.00-BK05-KG-30K-…` | `KG` → ATTENTION (NEC earth-ground) |
| `RAD4-72.00X42.00-BR02-CK3-DF-KG-30K-…A.3.pdf` | Fully loaded: seamless clock + defogger + Keen + KEEN DISCLAIMER + CLOCK power note; newest rev — current drafting style |
| `RAD4-26.00X40.00-NK04-CC2-NO-30K-…` | `CC2`+`NO` → cord-connected SPEC + long GFCI ATTENTION |
| `RAD4-24.00X36.00-BK05-CK2-30K-…` | `CK2` → CLOCK power note + hanging-bracket SPEC wording |
| `RAD4-36.00X36.00-BK05-KG-WG3-30K-…` | `KG`+`WG3` → WALL GLOW spec block + "MAIN LIGHTS AND WALL GLOW OPERATE TOGETHER" |
| `RAD4-17.25X56.00-CH04-30K-…` | Narrow mirror (W < 22") → **vertical power-box** orientation on page 2 |
| `RAD4-31.50X101.00-BK05-30K-…` | Very large mirror → 1:24 sheet scale |

Page 1 = elevation + section + note stack. Page 2 = wall-mounting view +
DETAIL A power-box callout.
