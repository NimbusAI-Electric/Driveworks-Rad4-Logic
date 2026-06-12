"""Extract every note-style section from each RAD4 sales aid and
cluster identical note text so we can map each note variant to its CPNs."""
import json
import re
from collections import defaultdict
from pathlib import Path
from pypdf import PdfReader

SALES_AIDS = Path(r"D:\EM-HV-04 Backup 5-14-2026\Sales Aids")
OUT_JSON   = Path(r"C:\Users\devops\rad4_notes.json")

# Every distinct uppercase header observed in the survey, mapped to the
# logical category we want in the final report.
HEADER_CATEGORY = {
    # SPECIFICATION = installation prose
    "SPECIFICATION":                  "SPECIFICATION",
    # ATTENTION = warnings (ground bonding etc.)
    "ATTENTION":                      "ATTENTION",
    # Defogger family
    "DEFOGGER":                       "DEFOGGER",
    "DEFOGGER SPECIFICATION":         "DEFOGGER",
    "DEFOGGER SPECIFICATIONS":        "DEFOGGER",
    "DEFOGGER POWER REQUIREMENTS":    "DEFOGGER",
    "KEEN / DEFOGGER DISCLAIMER":     "DEFOGGER DISCLAIMER (KEEN)",
    # Dimming family (handles the two typos)
    "DIMMER COMPATIBILITY":           "DIMMING",
    "DIMMNER COMPATIBILITY":          "DIMMING",
    "DIMMER COMPATABILITY":           "DIMMING",
    # Everything else the user said they want listed under "Other notes"
    "CLOCK POWER REQUIREMENTS":       "CLOCK",
    "CLOCK  POWER REQUIREMENTS":      "CLOCK",
    "WALL GLOW LED SPECIFICATION":    "WALL GLOW",
    "WALL GLOW REQUIREMENTS":         "WALL GLOW",
    "WALL GLOW SPECIFICATION":        "WALL GLOW",
    "PRODUCT USES":                   "PRODUCT USES",
    "USES":                           "PRODUCT USES",
    "THIS PRODUCT USES":              "PRODUCT USES",
    "POWER BOX REF":                  "POWER BOX REFERENCE",
    "POWER BOX":                      "POWER BOX REFERENCE",
    "NOTE":                           "MISC NOTE",
    "DFX":                            "DFX CALLOUT",
    "KG2":                            "KG2 CALLOUT",
    "CSTM":                           "CSTM CALLOUT",
    "INNER FRAME FINISH":             "INNER FRAME FINISH",
    "FRAME LED SPECIFICATION":        "FRAME LED SPEC",
    "LIGHTING POWER REQUIREMENTS":    "LIGHTING POWER NOTE",
    # These exist as headers but are pure spec data — we skip them so the
    # prose-note report stays focused.  (We already pulled them in the first pass.)
    # "PROPRIETARY AND CONFIDENTIAL", "LED SPECIFICATION", "POWER REQUIREMENTS",
    # "FIXTURE SPECIFICATION", "FRAME FINISH", "TOTAL INITIAL LUMENS PER FIXTURE"
}

ALL_HEADERS = set(HEADER_CATEGORY) | {
    "PROPRIETARY AND CONFIDENTIAL",
    "LED SPECIFICATION", "POWER REQUIREMENTS", "FIXTURE SPECIFICATION",
    "FRAME FINISH", "TOTAL INITIAL LUMENS PER FIXTURE",
}

# Line-anchored: header must sit on its own line.
HEADER_PATTERN = re.compile(
    r"(?m)^\s*("
    + "|".join(re.escape(h) for h in sorted(ALL_HEADERS, key=len, reverse=True))
    + r")\s*:\s*$"
)

# Some PDFs concatenate columns so a header lands inline, e.g.
# "...OF THE UNIT. DEFOGGER: VOLTAGE..." — recognise just these few.
INLINE_HEADERS = ["DEFOGGER", "DEFOGGER SPECIFICATION", "DEFOGGER SPECIFICATIONS",
                  "KEEN / DEFOGGER DISCLAIMER", "CLOCK POWER REQUIREMENTS"]
INLINE_PATTERN = re.compile(
    r"(?<=[.!?])\s+("
    + "|".join(re.escape(h) for h in sorted(INLINE_HEADERS, key=len, reverse=True))
    + r")\s*:\s*"
)

# Strip the page-footer / drawing-stamp boilerplate that bleeds into prose blocks
NOISE_RX = [
    re.compile(r"PROPRIETARY AND CONFIDENTIAL.*?ELECTRIC MIRROR", re.S | re.I),
    re.compile(r"CONTACT US:.*?T\+?1\.?425\.?776\.?4946", re.S | re.I),
    re.compile(r"REV\.\s*[A-Z]\.\d+", re.I),
    re.compile(r"SCALE:\s*\d+:\d+", re.I),
    re.compile(r"DIMS IN INCHES\s*\[mm\]", re.I),
    re.compile(r"TOLERANCE:\s*[^\n]+", re.I),
    re.compile(r"PG\.\s*\d+\s*OF\s*\d+", re.I),
    re.compile(r"\*BY APPROVING.*?FIELD VERIFIED\.", re.S | re.I),
    re.compile(r"APPROVED BY:\s*DATE:", re.I),
    re.compile(r"REVISION REQUESTED", re.I),
    re.compile(r"NOTE:\s*MIRROR CAN ONLY BE HUNG.*?INTERCHANGEABLE\.?", re.S | re.I),
    re.compile(r"SALES\s*AID\s*[-–]?\s*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", re.I),
    re.compile(r"©\s*\d{4}\s*ELECTRIC MIRROR", re.I),
    re.compile(r"ELECTRIC MIRROR\s*\d{4}", re.I),
    re.compile(r"\bRAD4-[A-Z0-9.\-X]+(?:-\d{2}K)\b"),    # CPN repeats in stamp
    # revision-history table (newer revs): header row + tabular rows like
    # "A.2 CHANGE CLOCK LOCATION N/A EP SDG 2/9/2026"
    re.compile(r"REV\.\s*DESCRIPTION\s*ECR#\s*REVISED\s*APPROVED\s*DATE.*$", re.S | re.I),
    re.compile(r"\bA\.\d+\s+[A-Z][^.\n]{5,80}?\s+N/A\s+\w+\s+\w+\s+\d{1,2}/\d{1,2}/\d{2,4}", re.I),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),     # any date
    re.compile(r"(?<![A-Z])A\.\d+\b"),              # stray revision token "A.2", "A.3"
]


def normalize(s: str) -> str:
    """Squash whitespace runs, drop stamp boilerplate, return clean prose."""
    for rx in NOISE_RX:
        s = rx.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fuzzy_key(s: str) -> str:
    """Cluster key that ignores punctuation, case, and one-letter typos.
    Two notes that mean the same thing collapse to the same key."""
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)          # drop punctuation
    s = re.sub(r"\s+", " ", s).strip()
    return s


CPN_RX = re.compile(r"\b(RAD4-[A-Z0-9.X\-]+?-\d{2}K)\b")


def cpn_for(path: Path, text: str) -> str:
    m = CPN_RX.search(text)
    if m and "XXXXX" not in m.group(1):
        return m.group(1)
    # fall back to filename
    fn = path.stem.upper()
    fn = re.sub(r"-SALES-AID.*$", "", fn)
    fn = re.sub(r"-A\.\d+$", "", fn)
    fn = re.sub(r"^E-", "", fn)
    return fn


def split_inline(header: str, body: str):
    """Some bodies contain another known header inline. Split them apart so the
    second one is yielded as its own section (e.g. ATTENTION text containing
    'DEFOGGER: VOLTAGE: 120V WATTAGE: 100W')."""
    m = INLINE_PATTERN.search(body)
    if not m:
        yield header, body
        return
    yield header, body[:m.start()]
    nested_header = m.group(1).strip()
    yield nested_header, body[m.end():]


def split_sections(text: str):
    """Yield (header, body_text) for each header found in `text`."""
    hits = list(HEADER_PATTERN.finditer(text))
    for i, m in enumerate(hits):
        header = m.group(1).strip()
        body_start = m.end()
        body_end   = hits[i+1].start() if i+1 < len(hits) else len(text)
        body = text[body_start:body_end]
        yield from split_inline(header, body)


def main():
    files = sorted(p for p in SALES_AIDS.iterdir()
                   if p.is_file() and p.suffix.lower() == ".pdf"
                   and p.name.upper().startswith(("RAD4", "E-RAD4")))
    print(f"Scanning {len(files)} PDFs...")

    # data[category][fuzzy_key] -> bucket; bucket["originals"] counts variants of the displayed text
    data = defaultdict(lambda: defaultdict(lambda: {
        "original_header": "",
        "originals": defaultdict(int),   # exact-text -> count
        "cpns": set(),
        "files": set(),
    }))

    for idx, p in enumerate(files, 1):
        try:
            pages = PdfReader(str(p)).pages
            full_text = "\n".join((pg.extract_text() or "") for pg in pages)
        except Exception as e:
            print(f"  ERR {p.name}: {e}")
            continue

        cpn = cpn_for(p, full_text)

        for header, body in split_sections(full_text):
            cat = HEADER_CATEGORY.get(header)
            if not cat:
                continue   # skip pure-data sections
            norm = normalize(body)
            if not norm or len(norm) < 5:
                continue
            key = fuzzy_key(norm)
            slot = data[cat][key]
            slot["original_header"] = header
            slot["originals"][norm] += 1
            slot["cpns"].add(cpn)
            slot["files"].add(p.name)

        if idx % 50 == 0:
            print(f"  {idx}/{len(files)}")

    # serialize (sets -> sorted lists); pick most-common original as display text
    out = {}
    for cat, variants in data.items():
        out[cat] = []
        for key, slot in sorted(variants.items(), key=lambda kv: -len(kv[1]["cpns"])):
            display = max(slot["originals"].items(), key=lambda kv: kv[1])[0]
            out[cat].append({
                "text":            display,
                "alt_texts":       [t for t, _ in sorted(slot["originals"].items(), key=lambda kv: -kv[1])][1:],
                "original_header": slot["original_header"],
                "cpn_count":       len(slot["cpns"]),
                "file_count":      len(slot["files"]),
                "cpns":            sorted(slot["cpns"]),
                "files":           sorted(slot["files"]),
            })

    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print()
    print(f"Wrote {OUT_JSON}")
    print()
    print("Summary by category:")
    for cat in sorted(out, key=lambda c: -sum(v["cpn_count"] for v in out[c])):
        n_variants = len(out[cat])
        n_total = sum(v["cpn_count"] for v in out[cat])
        print(f"  {cat:30s} {n_variants:>3} variant(s), {n_total} CPN occurrences")


if __name__ == "__main__":
    main()
