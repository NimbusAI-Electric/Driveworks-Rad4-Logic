"""RAD4 note-selection rule engine.

Given a CPN, returns the SolidWorks-drawing notes that should be placed on
the sales aid: SPECIFICATION, ATTENTION, DEFOGGER (heater spec),
DEFOGGER DISCLAIMER (KEEN), and DIMMING.

Rules are derived empirically from 372 real RAD4 sales aids
(see rad4_rule_analysis.txt).  When a CPN that already exists in the
catalog is passed in, this engine reproduces the notes that are actually
on the existing sales aid (direct lookup).  When a brand-new CPN is
passed in, it generates the notes from the rule-based decision tree.
"""
from __future__ import annotations
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional


def _find_data(filename: str) -> Path:
    """Locate a bundled data file. Searches, in order:
      1. ../data/ relative to this script  (the bundle layout)
      2. the script's own directory        (flat layout)
      3. the original authoring location   (running in place)
    Returns the first that exists, else the bundle path (so error messages
    point at the expected location)."""
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent / "data" / filename,
        here / filename,
        Path(r"C:\Users\devops") / filename,
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]

# ─── canonical note text (picked from the most-used variant in the catalog) ──

SPEC_TEXTS = {
    # Base: standard hard-wired install, line-voltage power only
    "BASE":
        "BRING MC CABLE TO ENCLOSURE. INSERT GROUND WIRE IN GROUNDED CONNECTOR. "
        "INSERT HOT AND NEUTRAL WIRE INTO LUMINAIRE DISCONNECT. "
        "NO ELECTRICAL BOX REQUIRED. ELECTRICAL POWER SHOULD BE CONTROLLED "
        "BY A WALL SWITCH (BY OTHERS). MIRROR SHOULD BE MOUNTED TO A "
        "MECHANICALLY SOUND SURFACE SUCH AS WALL STUDS TO SUPPORT ITS WEIGHT.",
    # 0-10V dimming variant: D1, DF, DFX
    "DIM_0_10V":
        "BRING MC CABLE TO ENCLOSURE. INSERT GROUND WIRE IN GROUNDED CONNECTOR. "
        "INSERT HOT AND NEUTRAL WIRE INTO LUMINAIRE DISCONNECT. "
        "0-10V CONTROL WIRES ARE BROUGHT IN THROUGH THE SECOND KNOCKOUT. "
        "NO ELECTRICAL BOX REQUIRED. ELECTRICAL POWER SHOULD BE CONTROLLED "
        "BY A WALL SWITCH (BY OTHERS). MIRROR SHOULD BE MOUNTED TO A "
        "MECHANICALLY SOUND SURFACE SUCH AS WALL STUDS TO SUPPORT ITS WEIGHT.",
    # Cord-connected (CC2) — plug-in
    "CORD":
        "PLUG FIXTURE INTO RECEPTACLE LOCATED IN WALL BEHIND MIRROR. "
        "RECEPTACLES SHOULD BE CONTROLLED BY WALL SWITCHES (BY OTHERS). "
        "MIRROR SHOULD BE MOUNTED TO A MECHANICALLY SOUND SURFACE SUCH AS "
        "WALL STUDS TO SUPPORT ITS WEIGHT.",
    # Hanging-bracket mounting (CK2 clocks)
    "HANGING":
        "BRING MC CABLE TO DRIVER ENCLOSURE EITHER DIRECTLY FROM BEHIND INTO "
        "KNOCKOUT OR PROVIDE (30\" MAX) WHIP TO SIDE KNOCKOUT. INSERT GROUND "
        "WIRE IN GROUNDED CONNECTOR. INSERT HOT AND NEUTRAL WIRE INTO "
        "LUMINAIRE DISCONNECT. LOW VOLTAGE CONTROL WIRES ARE BROUGHT IN "
        "THROUGH THE SECOND KNOCKOUT. NO ELECTRICAL BOX REQUIRED. ELECTRICAL "
        "POWER SHOULD BE CONTROLLED BY A WALL SWITCH (BY OTHERS). HANGING "
        "BRACKET SHOULD BE MOUNTED TO A MECHANICALLY SOUND SURFACE SUCH AS "
        "WALL STUDS TO SUPPORT FIXTURE WEIGHT.",
}
SPEC_WG3_TAIL = " MAIN LIGHTS AND WALL GLOW OPERATE TOGETHER."

ATTN_NEC = ("THIS PRODUCT MUST BE CONNECTED TO EARTH GROUND IN ACCORDANCE "
            "WITH NEC CODE 250.20 (B). IMPROPER GROUND CAN RESULT IN "
            "IRREGULAR FUNCTION OF THE UNIT.")

ATTN_GFCI = (
    "ELECTRIC MIRROR RECOMMENDS A HARDWIRED INSTALLATION AS THE PREFERRED "
    "METHOD OF INSTALLATION FOR ALL LIGHTED MIRROR PRODUCTS. PRIOR TO THE "
    "DELIVERY OF THIS CORD CONNECTED LUMINAIRE, WE RECOMMEND THAT YOU CONTACT "
    "YOUR LOCAL ELECTRICAL INSPECTOR TO REVIEW THE PLANNED CONDITIONS FOR THE "
    "INSTALLATION OF THIS PRODUCT. THIS WILL ENSURE COMPLIANCE WITH THE LOCAL "
    "ELECTRICAL CODE. IF A GFCI CIRCUIT IS REQUIRED, INSTALL A NON-GFCI OUTLET "
    "BEHIND THE MIRROR. THIS OUTLET MUST BE WIRED FROM THE LOAD SIDE OF AN "
    "ACCESSIBLE GFCI OUTLET. THIS WILL PREVENT HAVING TO REMOVE THE MIRROR TO "
    "RESET THE GFCI RECEPTACLE. THE LOAD ON THIS GFCI CIRCUIT SHOULD BE "
    "CAREFULLY CONSIDERED TO PREVENT UNINTENDED TRIPPING OF THE GFCI. MUST BE "
    "INSTALLED IN ACCORDANCE WITH ALL NATIONAL AND LOCAL ELECTRICAL CODES. "
    "ELECTRIC MIRROR IS NOT RESPONSIBLE FOR COMPATIBILITY OF A GFCI CIRCUIT "
    "WITH OUR PRODUCTS. CONTACT THE GFCI MANUFACTURER TO ENSURE COMPATIBILITY."
)

DIM_TRIAC = (
    "TO ENSURE PROPER OPERATION OF THIS DIMMABLE PRODUCT IT IS IMPORTANT TO "
    "SELECT A COMPATIBLE DIMMING SWITCH. THIS LUMINAIRE REQUIRES A COMPATIBLE "
    "FORWARD PHASE LINE DIMMER SWITCH. CONTACT THE CONTROLLER MANUFACTURER "
    "TO CONFIRM COMPATIBILITY WITH THIS PRODUCT. MUST BE INSTALLED IN "
    "ACCORDANCE WITH ALL NATIONAL AND LOCAL ELECTRICAL CODES. ELECTRIC "
    "MIRROR IS NOT RESPONSIBLE FOR DIMMER SWITCH COMPATIBILITY. THIS PRODUCT "
    "USES: SMT-024-096VTSP TRIAC PHASE DIMMING DRIVER."
)

DIM_0_10V = (
    "TO ENSURE PROPER OPERATION OF THIS DIMMABLE PRODUCT, IT IS IMPORTANT TO "
    "SELECT A COMPATIBLE DIMMING SWITCH. THIS LUMINAIRE REQUIRES A 0-10V "
    "ELECTRONIC DIMMER SWITCH. ELECTRIC MIRROR IS NOT RESPONSIBLE FOR DIMMER "
    "SWITCH COMPATIBILITY. MUST BE INSTALLED IN ACCORDANCE WITH ALL NATIONAL "
    "AND LOCAL ELECTRICAL CODES."
)

DEF_KEEN_DISC = ("KEEN UNIT CONTROLS THE LIGHTING ONLY SEPERATE WALL SWITCH "
                 "IS REQUIRED TO CONTROL DEFOGGER POWER")


# ─── rule helpers ─────────────────────────────────────────────────────────────

CPN_RX = re.compile(
    r"^RAD4(?:-(CSTM|FRX))?(?:-(\d{4,6}))?"
    r"-(\d+\.\d+)X(\d+\.\d+)"
    r"-([A-Z]{2}\d{2,3})"
    r"((?:-[A-Z0-9]+)*?)"
    r"-(\d{2}K)$"
)
DEFOGGER_CODES = {"D1", "D2", "DF", "DFX"}
KEEN_CODES     = {"KG", "KG2", "KD", "KC"}
CLOCK_CODES    = {"CK2", "CK3"}


def parse_cpn(cpn: str) -> dict:
    cpn = cpn.upper().strip()
    m = CPN_RX.match(cpn)
    if not m:
        raise ValueError(f"Not a parseable RAD4 CPN: {cpn!r}")
    series, custom_id, w, h, finish, opts_raw, cct = m.groups()
    opts = set(opts_raw.split("-")) - {""} if opts_raw else set()
    return {
        "cpn":      cpn,
        "series":   series or "STOCK",
        "custom":   custom_id,
        "width":    float(w),
        "height":   float(h),
        "area":     float(w) * float(h),
        "finish":   finish,
        "options":  opts,
        "cct":      cct,
    }


def defogger_wattage(area_in2: float, has_277V: bool,
                     has_dfx: bool = False) -> str:
    """Return the heater wattage string.

    Thresholds derived empirically (rad4_rule_analysis.txt PART 4):
      • 277V CPNs use a 24V/20W heater.
      • DFX is a fixed-pad heater that stays 25W regardless of fixture size.
      • Otherwise: <900 in² → 15W, <2050 → 25W, <2465 → 50W, ≥2465 → 100W.
    The DFX rule explains why fixtures up to 48"×42" (≈2016 in²) with DFX+KG
    use 25W heaters while same-area fixtures with plain DF use 50W.
    """
    if has_277V:
        return "20W @ 24V"
    if has_dfx:
        return "25W @ 120V"
    if area_in2 < 900:
        return "15W @ 120V"
    if area_in2 < 1900:
        return "25W @ 120V"
    if area_in2 < 2465:
        return "50W @ 120V"
    return "100W @ 120V"


# ─── primary rule engine ─────────────────────────────────────────────────────

def select_notes_from_options(width, height, options: set[str]) -> dict:
    """Pure-rule version. Takes parsed parts of a CPN, returns notes."""
    opts = set(options)
    area = width * height

    has_d1  = "D1"  in opts
    has_d2  = "D2"  in opts
    has_df  = "DF"  in opts
    has_dfx = "DFX" in opts
    has_any_def    = bool(opts & DEFOGGER_CODES)
    # D1 = 0-10V driver, D2 = TRIAC driver, DF/DFX = heater pads (not dimming)
    has_low_v_dim  = has_d1                                # 0-10V driver
    has_triac_dim  = has_d2                                # TRIAC driver
    has_low_v_wiring = has_d1 or has_df or has_dfx         # any low-voltage wiring tail in SPEC

    has_any_keen   = bool(opts & KEEN_CODES)
    has_any_clock  = bool(opts & CLOCK_CODES)

    has_cc2  = "CC2" in opts
    has_wg3  = "WG3" in opts
    has_no   = "NO"  in opts
    has_277V = "277V" in opts

    has_heater = has_df or has_dfx                          # explicit heater pad

    notes: dict[str, str] = {}

    # ── SPECIFICATION (always present) ──
    if has_cc2:
        spec = SPEC_TEXTS["CORD"]
    elif has_any_clock:
        spec = SPEC_TEXTS["HANGING"]
    elif has_low_v_wiring:
        spec = SPEC_TEXTS["DIM_0_10V"]
    else:
        spec = SPEC_TEXTS["BASE"]

    if has_wg3 or has_no:
        spec += SPEC_WG3_TAIL
    notes["SPECIFICATION"] = spec

    # ── ATTENTION ──
    if has_cc2:
        notes["ATTENTION"] = ATTN_GFCI
    elif has_any_keen:
        notes["ATTENTION"] = ATTN_NEC

    # ── DEFOGGER (heater spec) ──
    if has_heater:
        notes["DEFOGGER"] = f"VOLTAGE / WATTAGE: {defogger_wattage(area, has_277V, has_dfx)}"

    # ── DEFOGGER DISCLAIMER (KEEN) ──
    if has_any_keen and has_heater:
        notes["DEFOGGER DISCLAIMER (KEEN)"] = DEF_KEEN_DISC

    # ── DIMMING ──
    if has_triac_dim:
        notes["DIMMING"] = DIM_TRIAC
    elif has_low_v_dim:
        notes["DIMMING"] = DIM_0_10V

    return notes


def select_notes(cpn: str) -> dict:
    """Public entry: parse a CPN string then run the rule."""
    info = parse_cpn(cpn)
    return select_notes_from_options(info["width"], info["height"], info["options"])


# ─── catalog-aware wrapper ───────────────────────────────────────────────────

class CatalogLookup:
    """If the CPN already exists in our extracted catalog, reproduce the
    notes that are actually printed on its sales aid; otherwise fall back
    to the rule engine."""

    def __init__(self,
                 notes_json: Path = None,
                 specs_csv:  Path = None):
        notes_json = notes_json or _find_data("rad4_notes.json")
        specs_csv  = specs_csv  or _find_data("rad4_specifications.csv")
        self.notes = json.loads(Path(notes_json).read_text(encoding="utf-8"))
        self.actual: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        for cat in ["SPECIFICATION", "ATTENTION", "DEFOGGER",
                    "DEFOGGER DISCLAIMER (KEEN)", "DIMMING"]:
            for v in self.notes.get(cat, []):
                for cpn in v["cpns"]:
                    self.actual[cpn][cat].append(v["text"])

    def known(self, cpn: str) -> bool:
        return cpn in self.actual

    def lookup(self, cpn: str) -> dict[str, list[str]]:
        return dict(self.actual[cpn])

    def select(self, cpn: str) -> tuple[str, dict]:
        if self.known(cpn):
            return "lookup", self.lookup(cpn)
        return "rule", select_notes(cpn)


# ─── CLI smoke test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    samples = [
        "RAD4-24.00X36.00-BK05-30K",
        "RAD4-30.00X42.00-BK05-D2-30K",
        "RAD4-24.00X36.00-CH04-D1-DF-30K",
        "RAD4-72.00X42.00-BR02-CK3-DF-KG-30K",
        "RAD4-26.00X40.00-NK04-CC2-NO-30K",
        "RAD4-48.00X36.00-BK05-KG-30K",
    ]
    for cpn in samples:
        print("=" * 80)
        print(cpn)
        for cat, txt in select_notes(cpn).items():
            print(f"\n[{cat}]")
            print(txt)
        print()
