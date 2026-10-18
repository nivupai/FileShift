# FileShift macOS end-to-end — 14/16 passed

| # | Scenario | Result | Detail | Time |
|---|---|---|---|---|
| 1 | JPG → PNG | ✅ | D-Photo.png · 2400×1600 | 9.8s |
| 2 | JPG → WEBP | ✅ | D-Photo.webp · 2400×1600 | 9.4s |
| 3 | JPG → HEIC | ✅ | D-Photo.heic · 2400×1600 | 9.9s |
| 4 | JPG → PDF | ✅ | D-Photo.pdf · 1 page(s) | 9.0s |
| 5 | PNG → JPG | ✅ | D-Graphic.jpg · 800×533 | 9.3s |
| 6 | PDF → JPG (3 pages) | ✅ | 3 × .jpg | 9.4s |
| 7 | PDF → TXT | ✅ | D-Report.txt | 9.1s |
| 8 | DOCX → PDF | ✅ | D-Letter.pdf · 1 page(s) | 9.5s |
| 9 | PDF Split | ✅ | 3 PDFs | 9.5s |
| 10 | PDF Rotate | ✅ | all pages at 90° | 9.9s |
| 11 | PDF Compress | ✅ | 227 KB → 108 KB | 9.9s |
| 12 | Merge 2 PDFs | ✅ | 5 pages | 12.8s |
| 13 | Compress (window, Enter) | ❌ | AssertionError: no output file appeared | 27.0s |
| 14 | Resize 50% (window, Enter) | ✅ | 2400×1600 → 1200×800 | 12.0s |
| 15 | Add BG (window, Enter) | ❌ | AssertionError: no output file appeared | 27.1s |
| 16 | Metadata: remove all (Enter) | ✅ | 0 metadata fields left | 12.4s |