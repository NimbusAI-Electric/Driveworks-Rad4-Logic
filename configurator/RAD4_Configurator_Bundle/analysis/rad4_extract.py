"""Extract specifications from all RAD4 sales aid PDFs and map to part numbers."""
import os
import re
import csv
import json
from pathlib import Path
from pypdf import PdfReader

SALES_AIDS = Path(r"D:\EM-HV-04 Backup 5-14-2026\Sales Aids")
OUT_CSV    = Path(r"C:\Users\devops\rad4_specifications.csv")
OUT_JSON   = Path(r"C:\Users\devops\rad4_specifications.json")
OUT_TEXT   = Path(r"C:\Users\devops\rad4_raw_text.txt")

# --- field regexes (applied to combined text of page 1 + page 2) ---
RX = {
    "frame_finish":       re.compile(r"FRAME\s*FINISH:\s*\n?\s*([A-Z0-9 \-/]+?)(?=\n[A-Z]{2,}|\n\s*\n|$)", re.I),
    "total_wattage":      re.compile(r"TOTAL\s+FIXTURE\s+WATTAGE:\s*([0-9.]+)\s*W", re.I),
    # Voltage / amps variants, all anchored on "POWER REQUIREMENTS:"
    # Accepts VOLTS, VOLT, VAC, "V," and separators OR / - / TO / /
    "voltage":            re.compile(
        r"(\d{2,3}V?(?:\s*(?:OR|-|TO|/)\s*\d{2,3}V?)?)"
        r"\s*(?:VOLTS?|VAC|V)\s*,?\s*"
        r"([\d.]+(?:\s*(?:OR|-|TO|/)\s*[\d.]+)?)\s*AMPS?", re.I),
    "led_type":           re.compile(r"LED\s+TYPE:\s*([A-Z 0-9\-]+)", re.I),
    "led_length":         re.compile(r"LENGTH\s*\(IN\):\s*([0-9.]+)", re.I),
    "led_wattage":        re.compile(r"WATTAGE(?:\s*\(W\))?:\s*([0-9.]+)", re.I),
    "l70":                re.compile(r"L70\s+LIFESPAN\s*\(HRS\):\s*([0-9,]+)", re.I),
    "cct":                re.compile(r"CCT\(K\):\s*([0-9,]+)", re.I),
    # "TOTAL INITIAL LUMENS PER FIXTURE: 2945 @ 302 LM/FT", or
    # "TOTAL INITIAL LUMENS: 2,920 @ 302 LM/FT", or
    # "TOTAL INITIAL FIXTURE LUMENS: ..."
    "lumens":             re.compile(
        r"TOTAL\s+INITIAL\s+(?:FIXTURE\s+|LUMENS\s+PER\s+FIXTURE|LUMENS)\s*:?\s*"
        r"([0-9,]+)\s*@\s*([0-9.]+)\s*LM/FT", re.I),
    "cri":                re.compile(r"CRI:\s*([0-9+]+)", re.I),
    "weight":             re.compile(r"WEIGHT:\s*([0-9.]+)\s*LBS", re.I),
    "defogger_voltage":   re.compile(r"DEFOGGER:?\s*\n?\s*VOLTAGE:\s*([\dV]+)", re.I),
    "defogger_wattage":   re.compile(r"DEFOGGER:?[^:]*?VOLTAGE:[^\n]*\n\s*WATTAGE:\s*([\dW]+)", re.I),
    # Clock watts: look for an EXTERNAL N power supply section then the watts.
    "clock_watts":        re.compile(r"EXTERNAL\s+\d+V\s+POWER\s+SUPPLY[\s\S]{0,200}?([0-9.]+)\s*WATTS?", re.I),
    "powerbox":           re.compile(r"POWER\s*BOX[^\n]*\n\s*(81330[-A-Z0-9]+)", re.I),
    "powerbox_alt":       re.compile(r"(81330[-A-Z0-9]+W)", re.I),
    "mirror_asm":         re.compile(r"MIRROR\s+ASSEMBLY:\s*(RAD4-[A-Z0-9.\-]+)", re.I),
    "powerbox_asm":       re.compile(r"POWERBOX\s+ASSEMBLY:\s*(81330-[A-Z0-9\-]+)", re.I),
    "rev":                re.compile(r"REV\.\s*([A-Z]\.\d+)", re.I),
    "cpn":                re.compile(r"\b(RAD4-[A-Z0-9.X\-]+?-\d{2}K)\b"),
}

# --- option / finish code decoder (built from observation of the PDFs themselves) ---
FINISH_CODES = {
    "BK05":  "MATTE BLACK",
    "BR02":  "BRUSHED BRASS",
    "CH04":  "CHROME",
    "NK04":  "BRUSHED NICKEL",
    "BZ24":  "BRONZE (BZ24)",
    "BZ47":  "BRONZE (BZ47)",
    "CH11":  "CHROME (CH11)",
    "BK147": "MATTE BLACK (BK147)",
}

OPTION_CODES = {
    "D1":    "Defogger D1",
    "D2":    "Defogger D2",
    "DF":    "Defogger (DF)",
    "DFX":   "Defogger DFX",
    "KG":    "Keen 1-Touch (KG)",
    "KG2":   "Keen 1-Touch v2",
    "KD":    "Keen Dimmer",
    "KC":    "Keen Clock",
    "CK2":   "Clock CK2",
    "CK3":   "Clock CK3 (Seamless)",
    "CC2":   "Color-Change CC2",
    "WG3":   "Wall-Grommet/Power Routing (WG3)",
    "WR":    "Wall Receptacle",
    "WRX":   "Wall Receptacle Extended",
    "SO":    "Switch Option",
    "NO":    "Night-Off / Night-Light",
    "277V":  "277V Input",
    "FRX":   "FRX Variant",
    "CSTM":  "Custom",
}

CCT_CODES = {"27K": "2700K", "30K": "3000K", "35K": "3500K"}


def parse_cpn(cpn: str) -> dict:
    """Parse CPN tokens such as RAD4-24.00X36.00-BK05-D1-DF-30K."""
    parts = cpn.split("-")
    info = {
        "model":        parts[0] if parts else "",
        "is_custom":    "CSTM" in parts or "FRX" in parts,
        "is_frx":       "FRX" in parts,
        "size":         "",
        "finish_code":  "",
        "finish_name":  "",
        "options":      [],
        "cct_code":     "",
        "cct_K":        "",
        "custom_prefix": "",
    }
    rest = parts[1:]
    # CSTM / FRX prefix
    if rest and rest[0] in ("CSTM", "FRX"):
        info["custom_prefix"] = rest.pop(0)
    # optional 5-digit numeric custom suffix (e.g. 85285, 84497)
    if rest and re.fullmatch(r"\d{4,6}", rest[0]):
        info["custom_id"] = rest.pop(0)
    # size like 24.00X36.00
    if rest and re.fullmatch(r"\d+\.\d+X\d+\.\d+", rest[0]):
        info["size"] = rest.pop(0)
    # finish code
    if rest:
        info["finish_code"] = rest[0]
        info["finish_name"] = FINISH_CODES.get(rest[0], rest[0])
        rest = rest[1:]
    # everything else is options (last token is CCT)
    for tok in rest:
        if tok in CCT_CODES:
            info["cct_code"] = tok
            info["cct_K"]   = CCT_CODES[tok]
        else:
            info["options"].append(tok)
    info["option_meanings"] = [OPTION_CODES.get(o, o) for o in info["options"]]
    return info


def extract_pdf(path: Path) -> dict:
    """Read all pages and pull structured fields."""
    try:
        reader = PdfReader(str(path))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception as e:
        return {"file": path.name, "error": str(e)}

    rec = {"file": path.name, "filename_stem": path.stem}

    # CPN from filename (strip -SALES-AID-rev)
    fn = path.stem.upper()
    fn = re.sub(r"-SALES-AID.*$", "", fn)
    fn = re.sub(r"-A\.\d+$", "", fn)
    rec["cpn_from_filename"] = fn

    # CPN from PDF body (more authoritative), but fall back to filename if
    # the PDF uses the literal "XXXXX" placeholder (FRX template PDFs do this).
    cpn_match = RX["cpn"].search(text)
    rec["cpn_in_pdf"] = cpn_match.group(1) if cpn_match else ""
    if rec["cpn_in_pdf"] and "XXXXX" not in rec["cpn_in_pdf"]:
        rec["cpn"] = rec["cpn_in_pdf"]
    else:
        rec["cpn"] = rec["cpn_from_filename"]
        # strip leading E- if present so cpn_model stays "RAD4"
        rec["cpn"] = re.sub(r"^E-", "", rec["cpn"])

    parsed = parse_cpn(rec["cpn"])
    rec.update({f"cpn_{k}": v for k, v in parsed.items()})

    # field-by-field regex scan
    def find(key, group=1, default=""):
        m = RX[key].search(text)
        return m.group(group).strip() if m else default

    rec["frame_finish"]      = find("frame_finish").rstrip()
    rec["total_wattage_W"]   = find("total_wattage")
    # newer PDFs (A.3 onward) omit "TOTAL FIXTURE WATTAGE" and rely on LED WATTAGE
    if not rec["total_wattage_W"]:
        rec["total_wattage_W"] = ""
    vm = RX["voltage"].search(text)
    rec["voltage_V"]         = vm.group(1) if vm else ""
    rec["current_A"]         = vm.group(2) if vm else ""
    rec["led_type"]          = find("led_type").strip()
    rec["led_length_in"]     = find("led_length")
    rec["led_wattage_W"]     = find("led_wattage")
    rec["l70_lifespan_hrs"]  = find("l70")
    rec["cct_K"]             = find("cct")
    lm = RX["lumens"].search(text)
    rec["lumens_total"]      = lm.group(1) if lm else ""
    rec["lumens_per_ft"]     = lm.group(2) if lm else ""
    rec["cri"]               = find("cri")
    rec["weight_lbs"]        = find("weight")
    rec["defogger_voltage"]  = find("defogger_voltage")
    rec["defogger_wattage"]  = find("defogger_wattage")
    rec["clock_watts"]       = find("clock_watts")

    pb = RX["powerbox"].search(text) or RX["powerbox_alt"].search(text)
    rec["powerbox"]          = pb.group(1) if pb else ""
    rec["mirror_assembly"]   = find("mirror_asm")
    rec["powerbox_assembly"] = find("powerbox_asm")
    rec["revision"]          = find("rev")

    # presence flags for big-ticket options
    rec["has_defogger"]      = bool(rec["defogger_voltage"] or "DEFOGGER" in text.upper())
    rec["has_clock"]         = "CLOCK" in text.upper()
    rec["has_keen"]          = "KEEN" in text.upper()
    rec["has_277v"]          = "277V" in fn or "277" in (rec["voltage_V"] or "")
    rec["has_dimmer_kd"]     = "KD" in parsed["options"]

    return rec


def main():
    files = sorted([p for p in SALES_AIDS.glob("*.pdf") if p.name.upper().startswith(("RAD4", "E-RAD4"))]
                   + [p for p in SALES_AIDS.glob("*.PDF") if p.name.upper().startswith(("RAD4", "E-RAD4"))])
    files = list({p.name: p for p in files}.values())   # de-dupe (glob is case-insensitive on Windows)
    print(f"Found {len(files)} RAD4 sales-aid PDFs")

    records, errors = [], []
    for i, p in enumerate(files, 1):
        rec = extract_pdf(p)
        if rec.get("error"):
            errors.append(rec)
        records.append(rec)
        if i % 25 == 0:
            print(f"  processed {i}/{len(files)}")
    print(f"Done. Errors: {len(errors)}")

    # write CSV
    fieldnames = [
        "file", "cpn", "revision",
        "cpn_model", "cpn_custom_prefix", "cpn_size", "cpn_finish_code", "cpn_finish_name",
        "cpn_cct_code", "cpn_cct_K", "cpn_is_custom", "cpn_is_frx",
        "cpn_options", "cpn_option_meanings",
        "frame_finish",
        "total_wattage_W", "voltage_V", "current_A",
        "led_type", "led_length_in", "led_wattage_W",
        "l70_lifespan_hrs", "cct_K",
        "lumens_total", "lumens_per_ft", "cri",
        "weight_lbs",
        "has_defogger", "defogger_voltage", "defogger_wattage",
        "has_clock", "clock_watts",
        "has_keen", "has_277v", "has_dimmer_kd",
        "powerbox", "mirror_assembly", "powerbox_assembly",
        "cpn_in_pdf", "cpn_from_filename",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in records:
            row = dict(r)
            row["cpn_options"]         = ";".join(r.get("cpn_options", []) or [])
            row["cpn_option_meanings"] = ";".join(r.get("cpn_option_meanings", []) or [])
            w.writerow(row)
    print(f"Wrote {OUT_CSV}")

    OUT_JSON.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
