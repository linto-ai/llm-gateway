"""Check schema child order of tcPr/tblPr/pPr/rPr in every XML part of a DOCX (Word is strict, LibreOffice is not)."""
import sys, zipfile, re
from lxml import etree
sys.path.insert(0, __import__("os").path.dirname(__file__))
from docx_kit import TCPR_ORDER, TBLPR_ORDER, PPR_ORDER, RPR_ORDER
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ORDERS = {"tcPr": TCPR_ORDER, "tblPr": TBLPR_ORDER, "pPr": PPR_ORDER, "rPr": RPR_ORDER}
bad = 0
with zipfile.ZipFile(sys.argv[1]) as z:
    for name in z.namelist():
        if not re.match(r"word/(document|header\d*|footer\d*|styles)\.xml$", name):
            continue
        root = etree.fromstring(z.read(name))
        for tag, order in ORDERS.items():
            rank = {W + t.split(":")[1]: i for i, t in enumerate(order)}
            for el in root.iter(W + tag):
                seq = [rank.get(c.tag, -1) for c in el if c.tag in rank]
                if seq != sorted(seq):
                    bad += 1
                    if bad <= 5:
                        print(name, tag, [c.tag.replace(W, "") for c in el])
print("order errors:", bad)
sys.exit(1 if bad else 0)
