"""Build the final spec-to-CPN mapping outputs from the extracted CSV."""
import csv
import json
from pathlib import Path
from collections import defaultdict, Counter

IN_CSV   = Path(r"C:\Users\devops\rad4_specifications.csv")
OUT_MD   = Path(r"C:\Users\devops\RAD4_Specifications_Map.md")
OUT_KEY  = Path(r"C:\Users\devops\RAD4_Code_Key.md")

# Re-use the same decoder tables as the extractor
FINISH_CODES = {
    "BK05":  "MATTE BLACK",
    "BR02":  "BRUSHED BRASS",
    "CH04":  "CHROME / ETCHED CHROME",
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
    "DFX":   "Defogger DFX (Extended)",
    "KG":    "Keen 1-Touch Control (KG)",
    "KG2":   "Keen 1-Touch v2 (KG2)",
    "KD":    "Keen Dimmer",
    "KC":    "Keen Clock",
    "CK2":   "Clock CK2",
    "CK3":   "Seamless Clock (CK3)",
    "CC2":   "Color-Change CC2",
    "WG3":   "Wall-Grommet / Power Routing (WG3)",
    "WR":    "Wall Receptacle (WR)",
    "WRX":   "Wall Receptacle Extended (WRX)",
    "SO":    "Switch Option",
    "NO":    "Night-Off / Night-Light",
    "277V":  "277V Input",
    "FRX":   "FRX Variant",
    "CSTM":  "Custom Size / Custom Project",
}

CCT = {"27K": "2700K", "30K": "3000K", "35K": "3500K"}


def main():
    rows = list(csv.DictReader(IN_CSV.open(encoding="utf-8")))
    rows.sort(key=lambda r: r["cpn"])

    # === code key markdown ===
    code_md = ["# RAD4 Sales-Aid Code Key", "",
               "Decoded from observed values across all 381 RAD4 sales aids.",
               "",
               "## CPN structure",
               "",
               "```",
               "RAD4-[CSTM-|FRX-][<custom-id>-]<WIDTH>X<HEIGHT>-<finish>[-<opt1>...-<optN>]-<CCT>",
               "```",
               "",
               "Example: `RAD4-72.00X42.00-BR02-CK3-DF-KG-30K`",
               "→ 72.00\" × 42.00\" Brushed Brass with Seamless Clock + Defogger + Keen, 3000K.",
               "",
               "## Frame Finish Codes", "",
               "| Code | Finish |", "|------|--------|"]
    for c, n in FINISH_CODES.items():
        code_md.append(f"| `{c}` | {n} |")

    code_md += ["", "## Option Codes", "",
                "| Code | Meaning |", "|------|---------|"]
    for c, n in OPTION_CODES.items():
        code_md.append(f"| `{c}` | {n} |")

    code_md += ["", "## Color-Temperature Codes", "",
                "| Code | CCT |", "|------|-----|"]
    for c, n in CCT.items():
        code_md.append(f"| `{c}` | {n} |")

    code_md += ["", "## Prefix Codes", "",
                "| Code | Meaning |", "|------|---------|",
                "| `E-RAD4-` | European/240V market variant (input 220-240 V) |",
                "| `RAD4-CSTM-` | Custom-sized RAD4 (non-stock size) |",
                "| `RAD4-FRX-` | FRX RAD4 series variant |",
                "", "## Power-Box Models", "",
                "| Model | Used in |", "|-------|---------|"]
    pb_counter = Counter(r["powerbox"] for r in rows if r["powerbox"])
    for pb, n in pb_counter.most_common():
        code_md.append(f"| `{pb}` | {n} sales aid(s) |")

    OUT_KEY.write_text("\n".join(code_md), encoding="utf-8")
    print(f"Wrote {OUT_KEY}")

    # === main mapping markdown ===
    md = ["# RAD4 Sales-Aid Specifications → Part-Number Mapping",
          "",
          f"**Source:** `D:\\EM-HV-04 Backup 5-14-2026\\Sales Aids\\` — {len(rows)} RAD4 sales-aid PDFs",
          "",
          "**Companion file:** [RAD4 Code Key](RAD4_Code_Key.md)",
          "",
          "Each row represents one **top-level CPN** (the Sales-Aid drawing title). Columns are the engineering specifications drawn from that PDF's spec block.",
          ""]

    md += ["## 1. Summary by spec category", ""]

    md += ["### 1.1 Frame finishes", ""]
    fin_counts = Counter(r["cpn_finish_code"] for r in rows)
    md += ["| Finish code | Decoded | # CPNs |",
           "|-------------|---------|--------|"]
    for f, n in fin_counts.most_common():
        md.append(f"| `{f}` | {FINISH_CODES.get(f, '(unknown)')} | {n} |")
    md.append("")

    md += ["### 1.2 Color temperatures", ""]
    cct_counts = Counter(r["cpn_cct_code"] for r in rows)
    md += ["| CCT code | Kelvin | # CPNs |",
           "|----------|--------|--------|"]
    for c, n in cct_counts.most_common():
        md.append(f"| `{c}` | {CCT.get(c, '?')} | {n} |")
    md.append("")

    md += ["### 1.3 Voltage / input variants", ""]
    v_counts = Counter(r["voltage_V"] for r in rows if r["voltage_V"])
    md += ["| Input voltage spec | # CPNs |",
           "|--------------------|--------|"]
    for v, n in v_counts.most_common():
        md.append(f"| `{v} V` | {n} |")
    md.append("")

    md += ["### 1.4 Option-code frequency", ""]
    opt_counts = Counter()
    for r in rows:
        for o in (r["cpn_options"] or "").split(";"):
            if o:
                opt_counts[o] += 1
    md += ["| Option | Meaning | # CPNs |",
           "|--------|---------|--------|"]
    for o, n in opt_counts.most_common():
        md.append(f"| `{o}` | {OPTION_CODES.get(o, '(unknown)')} | {n} |")
    md.append("")

    md += ["### 1.5 LED platform (all variants observed)", ""]
    led_t = Counter(r["led_type"] for r in rows if r["led_type"])
    md += ["| LED type | # CPNs |", "|----------|--------|"]
    for t, n in led_t.most_common():
        md.append(f"| {t} | {n} |")
    md.append("")
    md += ["Every RAD4 unit uses a replaceable LED flex strip at **302 lm/ft**, CRI 90+, "
           "with a calculated **L70 lifespan of 140,000 hours**. Tested CCT options are 2700 K, "
           "3000 K, and 3500 K. These four specs are constant across the entire line.", ""]

    md += ["## 2. Full CPN → Specifications table", "",
           "Sorted by CPN. Sizes are inches (W × H). Options are dash-separated suffixes "
           "carried in the CPN itself.", "",
           "| CPN (Top-Level Part Number) | Size W×H | Finish | Options | CCT | "
           "Input V | Current (A) | LED W | LED Length (in) | Lumens | LM/FT | CRI | "
           "Weight (lb) | L70 (hrs) | Power Box | Rev | Source PDF |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        opts = r["cpn_options"] or "—"
        finish = f"`{r['cpn_finish_code']}` {FINISH_CODES.get(r['cpn_finish_code'], '')}".strip()
        md.append(
            f"| `{r['cpn']}` "
            f"| {r['cpn_size']} "
            f"| {finish} "
            f"| {opts} "
            f"| {r['cpn_cct_code']} ({r['cpn_cct_K']}) "
            f"| {r['voltage_V']} "
            f"| {r['current_A']} "
            f"| {r['led_wattage_W']} "
            f"| {r['led_length_in']} "
            f"| {r['lumens_total'] or '—'} "
            f"| {r['lumens_per_ft'] or '—'} "
            f"| {r['cri']} "
            f"| {r['weight_lbs']} "
            f"| {r['l70_lifespan_hrs']} "
            f"| {r['powerbox'] or '—'} "
            f"| {r['revision']} "
            f"| {r['file']} |"
        )
    md.append("")

    # === Section 3: CPNs grouped by option ===
    md += ["## 3. CPNs grouped by option / feature", "",
           "Each option below lists every CPN where it appears. Helpful for "
           "answering \"which CPNs include the Keen 1-Touch?\" type questions.", ""]
    by_opt = defaultdict(list)
    for r in rows:
        if r["cpn_options"]:
            for o in r["cpn_options"].split(";"):
                if o:
                    by_opt[o].append(r["cpn"])
    for opt in sorted(by_opt, key=lambda o: (-len(by_opt[o]), o)):
        meaning = OPTION_CODES.get(opt, "(unknown)")
        md.append(f"### `{opt}` — {meaning}  ({len(by_opt[opt])} CPNs)")
        md.append("")
        for cpn in sorted(set(by_opt[opt])):
            md.append(f"- `{cpn}`")
        md.append("")

    # === Section 4: CPNs grouped by finish ===
    md += ["## 4. CPNs grouped by frame finish", ""]
    by_fin = defaultdict(list)
    for r in rows:
        by_fin[r["cpn_finish_code"]].append(r["cpn"])
    for f in sorted(by_fin, key=lambda x: (-len(by_fin[x]), x)):
        md.append(f"### `{f}` — {FINISH_CODES.get(f, '?')}  ({len(by_fin[f])} CPNs)")
        md.append("")
        for cpn in sorted(set(by_fin[f])):
            md.append(f"- `{cpn}`")
        md.append("")

    # === Section 5: invariant specs ===
    md += ["## 5. Constants across the RAD4 line",
           "",
           "These specifications are **the same on every RAD4 sales aid** observed:",
           "",
           "| Spec | Value |",
           "|------|-------|",
           "| LED type | Replaceable flex strip |",
           "| Lumens per foot | 302 lm/ft |",
           "| CRI | 90+ |",
           "| Calculated L70 lifespan | 140,000 hrs |",
           "| Frame depth off wall | 0.59\" |",
           "| Total fixture depth | 2.03\" |",
           "| Diffuser type | Frosted |",
           "| Section profile (frosted/LED/mirror) | 1.44\" × 0.99\" × 0.53\" |",
           "| Powerbox family (standard) | `81330-96W` (variants for clock / Keen / defogger) |",
           "| Tolerance | ±1/8\" [±3 mm] |",
           "| Approval | Field-verified dimensions required |",
           ""]

    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    print(f"  {len(rows)} CPNs documented")
    print(f"  {len(by_opt)} distinct options")
    print(f"  {len(by_fin)} distinct finishes")


if __name__ == "__main__":
    main()
