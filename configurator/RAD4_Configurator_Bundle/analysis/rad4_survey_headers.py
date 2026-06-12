"""Survey every uppercase 'HEADER:' line across the RAD4 sales aids
so we know exactly what note categories exist."""
import re
from pathlib import Path
from collections import Counter
from pypdf import PdfReader

SALES_AIDS = Path(r"D:\EM-HV-04 Backup 5-14-2026\Sales Aids")
HEADER_RX  = re.compile(r"^\s*([A-Z][A-Z0-9 /&\-]{2,40}):\s*$", re.M)

files = sorted(p for p in SALES_AIDS.iterdir()
               if p.is_file()
               and p.suffix.lower() == ".pdf"
               and p.name.upper().startswith(("RAD4", "E-RAD4")))

headers = Counter()
for p in files:
    try:
        text = "\n".join(pg.extract_text() or "" for pg in PdfReader(str(p)).pages)
    except Exception:
        continue
    for m in HEADER_RX.finditer(text):
        headers[m.group(1).strip()] += 1

print(f"{len(files)} files scanned")
print(f"{len(headers)} distinct header strings")
print()
for h, n in headers.most_common():
    print(f"  {n:>4}  {h}")
