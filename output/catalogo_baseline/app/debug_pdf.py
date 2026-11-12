from __future__ import annotations

import pdfplumber

pdf = pdfplumber.open("temp_files/xr20516233801SR.repx.pdf")
for w in pdf.pages[0].extract_words():
    print(w)
