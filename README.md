# PrintFit

Lightweight Windows app that prints PDFs on office printers **without white margins** and **without stretching** (one uniform scale factor on both axes).

## Modes
- **Trim white + fill page** (default): removes the white border from the artwork, then scales it up to cover the whole sheet.
- **Fill page (no trim)**: scales the PDF page to cover the whole sheet.
- **Fit printable area**: whole design visible, white only where proportions differ.

Pages are re-rendered at the printer's resolution, so quality is not lost.

> Note: most office printers cannot print the last ~3-5 mm at the paper edge. Content in that strip is clipped. For a true edge-to-edge result, print on A3/SRA3 and trim.

## Run from source
```
pip install -r requirements.txt
python printfit.py
```

## Build the .exe
Locally:
```
pip install pyinstaller
pyinstaller --onefile --noconsole --name PrintFit printfit.py
```
Or let GitHub build it: **Actions -> Build Windows exe -> Run workflow**, then download `PrintFit-windows` from the run's artifacts. Pushing a tag like `v1.0` also attaches `PrintFit.exe` to a release.
