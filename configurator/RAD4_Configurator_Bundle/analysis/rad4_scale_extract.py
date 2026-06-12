"""Extract SCALE: 1:N for each page of every RAD4 sales-aid PDF and
correlate with fixture width × height."""
import csv
import json
import re
from pathlib import Path
from collections import defaultdict
from pypdf import PdfReader

SALES_AIDS = Path(r"D:\EM-HV-04 Backup 5-14-2026\Sales Aids")
OUT_CSV    = Path(r"C:\Users\devops\rad4_scales.csv")

SCALE_RX = re.compile(r"SCALE\s*:\s*1\s*:\s*(\d+(?:\.\d+)?)", re.I)
# CPN pulled from the file body (preferred) or filename
CPN_RX   = re.compile(r"\b(RAD4-[A-Z0-9.X\-]+?-\d{2}K)\b")
SIZE_RX  = re.compile(r"(\d+\.\d+)X(\d+\.\d+)")


def cpn_for(path: Path, body_text: str) -> str:
    m = CPN_RX.search(body_text)
    if m and "XXXXX" not in m.group(1):
        return m.group(1)
    fn = path.stem.upper()
    fn = re.sub(r"-SALES-AID.*$", "", fn)
    fn = re.sub(r"-A\.\d+$", "", fn)
    fn = re.sub(r"^E-", "", fn)
    return fn


def main():
    files = sorted(p for p in SALES_AIDS.iterdir()
                   if p.is_file() and p.suffix.lower() == ".pdf"
                   and p.name.upper().startswith(("RAD4", "E-RAD4")))
    print(f"Scanning {len(files)} PDFs...")

    rows = []
    for i, p in enumerate(files, 1):
        try:
            pages = PdfReader(str(p)).pages
        except Exception as e:
            print(f"  err {p.name}: {e}")
            continue

        page_texts = [pg.extract_text() or "" for pg in pages]
        full = "\n".join(page_texts)
        cpn  = cpn_for(p, full)

        # size from CPN
        ms = SIZE_RX.search(cpn)
        if ms:
            W, H = float(ms.group(1)), float(ms.group(2))
        else:
            W, H = 0.0, 0.0

        # All scales on each page (largest N is the main-drawing scale;
        # smaller N values are section-detail scales).
        scales = []
        all_scales_per_page = []
        for txt in page_texts:
            matches = [float(m.group(1)) for m in SCALE_RX.finditer(txt)]
            all_scales_per_page.append(matches)
            scales.append(str(int(max(matches))) if matches else "")

        rows.append({
            "file":   p.name,
            "cpn":    cpn,
            "width":  W,
            "height": H,
            "area":   W * H,
            "max_dim": max(W, H),
            "min_dim": min(W, H),
            "n_pages": len(pages),
            "scale_p1": scales[0] if len(scales) > 0 else "",
            "scale_p2": scales[1] if len(scales) > 1 else "",
            "scale_p3": scales[2] if len(scales) > 2 else "",
        })

        if i % 50 == 0:
            print(f"  {i}/{len(files)}")

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {OUT_CSV}  ({len(rows)} rows)")

    # quick summary: scale distribution
    p1 = defaultdict(int)
    p2 = defaultdict(int)
    for r in rows:
        if r["scale_p1"]:
            p1[r["scale_p1"]] += 1
        if r["scale_p2"]:
            p2[r["scale_p2"]] += 1
    print()
    print("Page 1 scale distribution (1:N):")
    for s, n in sorted(p1.items(), key=lambda kv: float(kv[0])):
        print(f"  1:{s:>4}   {n} PDF(s)")
    print()
    print("Page 2 scale distribution (1:N):")
    for s, n in sorted(p2.items(), key=lambda kv: float(kv[0])):
        print(f"  1:{s:>4}   {n} PDF(s)")


if __name__ == "__main__":
    main()
