# FileShift

A reproduction of DragShift — renamed FileShift — that extends the original app.
Convert and edit files on **Windows and Mac** with a liquid-glass radial menu. Start dragging any file, press **Shift**, and drop it on a slice.

**What's different from the original DragShift:**
- **New tool: Watermark** — add a text watermark (any colour, opacity, size, corner/centre
  placement, or tiled across the whole image) to any image. See
  [`fileshift/imaging.py`](fileshift/imaging.py)'s `apply_watermark`/`Watermark` and
  [`fileshift/tools/watermark.py`](fileshift/tools/watermark.py).
- **Refactored `tools.py`** (was 1,426 lines in one file) into
  [`fileshift/tools/`](fileshift/tools), one module per tool (`crop.py`, `addbg.py`,
  `annotate.py`, `redact.py`, `edit.py`, `metadata.py`, `compress.py`, `resize.py`,
  `protect.py`, `watermark.py`), with shared widgets/base class in `_shared.py`. The public
  API (`fileshift.tools.CropWindow`, etc.) is unchanged.
- **Packaging**: added [`pyproject.toml`](pyproject.toml) (installable package, `fileshift`
  console entry point, `ruff` lint config) alongside the existing `requirements.txt` and
  PyInstaller spec.
- **More tests**: `tests/test_watermark.py` covers the new tool's pure-logic functions.

![FileShift radial menu and Add BG editor](docs/preview.png)

## Download

From the [latest release](../../releases/latest):

- **FileShift-Setup.exe** (recommended): installs for your user only, so no admin rights are needed. It adds a Start menu entry, an option to start with Windows, a right-click **FileShift…** entry and a **Send to → FileShift** entry. It uninstalls cleanly from Settings → Apps.
- **FileShift.exe**: a portable version you can run from anywhere.

- **FileShift-mac-apple-silicon.dmg**: for Macs with M1, M2, M3 or M4 chips (macOS 11 or later).
- **FileShift-mac-intel.dmg**: for Intel Macs.

On Mac, open the .dmg and drag **FileShift** into Applications. FileShift lives in the menu bar and has no Dock icon. You can also right-click any file → **Open With → FileShift**.

> **First launch on Windows:** SmartScreen may warn because the app isn't code-signed yet. Click **More info → Run anyway**.
>
> **First launch on Mac (until FileShift is notarized by Apple):** macOS says *"Apple could not verify 'FileShift' is free of malware."* This happens with any app that hasn't paid for Apple's notarization; FileShift's code is all public in this repo. To open it:
> 1. Open FileShift once and click **Done** on the warning.
> 2. Go to  → **System Settings → Privacy & Security**, scroll down to *"FileShift was blocked…"* and click **Open Anyway**. Enter your password and confirm.
> 3. That's it. macOS remembers the choice.
>
> Or, in Terminal: `xattr -dr com.apple.quarantine /Applications/FileShift.app`
> (On macOS 15 and later, the old right-click → Open shortcut no longer skips this warning.)
>
> **Mac, optional:** allow **Screen Recording** when FileShift asks, so the glass can refract the windows behind it. Without it, the glass shows your wallpaper. Nothing is ever saved or sent.

## How to use

1. Start dragging a file in File Explorer or on the desktop.
2. Press **Shift**. The menu opens under your cursor.
3. Drop the file on a slice. The result is saved **next to the original**, and the original is never changed.
4. To switch between **Convert** and **Tools**, tap **Shift** again.

Each action ends with a notification that shows what changed, for example *"2.4 MB → 610 KB · 75% smaller"* or *"2400×1600 → 1200×800"*, with **Open**, **Show in folder** and **Undo**. Undo moves the new file to the Recycle Bin.

You can also right-click a file → **FileShift…**, use **Send to → FileShift**, or double-click the tray icon to pick a file.

## What it does

| File | Convert to | Tools |
|---|---|---|
| Images (JPG, PNG, WEBP, HEIC, AVIF, TIFF, BMP, GIF, ICO) | Any of those, or PDF. Several images become one combined PDF | **Compress** (by quality or to a target size such as "under 500 KB", with a before/after preview, several files at once) · **Resize** · **Crop** (ratios, live pixel size, rotate) · **Edit** (Auto, light/colour, rotate, flip, B&W, hold to compare) · **Annotate** (arrows, boxes, numbered steps, text, marker) · **Redact** · **Add BG** · **Watermark** (text, colour, opacity, position or tiled) · **Metadata** (camera, date, GPS location with a map link; remove location only or remove everything) |
| PDF | JPG or PNG (one per page), DOCX, TXT | Compress · Split · Rotate · Merge (drop several) · **Protect** (AES-256 password) · **Extract images** · Metadata |
| Word (.docx) | PDF (uses Microsoft Word if it's installed, otherwise a built-in renderer), TXT | — |
| Text (.txt, .md, .csv…) | PDF, DOCX | — |

**Settings** (tray menu): trigger key (Shift, Ctrl or Alt), where results go (next to the original or a `FileShift` subfolder), JPG/WebP quality, PDF → image resolution, and start with Windows.

## The look

The menu, notifications and windows use real **liquid-glass** rendering. FileShift captures the screen behind each surface and refracts it through the shape. A curved edge bends light, R, G and B bend by slightly different amounts (which gives the rainbow fringe), a highlight runs along the rim facing the light, and the tint adapts to what's behind it so text stays readable. The menu renders on a background thread while it pops in, so it still opens instantly.

## Tested on real Windows

Every push runs these jobs on GitHub's Windows and Mac machines:

- **Build:** unit tests, the portable exe and installer builds, a self-test of each build, and a silent install → run → uninstall check.
- **End-to-end:** a script moves the real mouse to drag files from File Explorer *and* the Desktop, presses Shift, drops on every conversion and tool, drives each tool window, and checks every output file (format, dimensions, page counts, encryption, metadata removed). The results table and a screen recording are saved to the `e2e-output` branch.
- **Mac end-to-end:** real Finder drags with Shift (Quartz mouse and keyboard events) through conversions, PDF tools, merging and the tool windows. Every output is checked, and the run is recorded to the `e2e-mac-output` branch.
- **Mac builds:** `FileShift.app` and the .dmg for Apple Silicon and Intel, each self-tested inside the app bundle.
- **Demo video:** pushing to the `demo` branch records a showcase video.

## Support

FileShift is free. If it saves you time, you can leave a tip on Cash App: [**$AtikaKadesha**](https://cash.app/$AtikaKadesha). Thank you!

<img src="docs/tip-cashapp.png" alt="Cash App QR code for $AtikaKadesha" width="220">

## Run from source

```bash
pip install -r requirements.txt
python -m fileshift
```

Tests: `python -m pytest -q`. Logs are written to `%LOCALAPPDATA%\FileShift\log.txt` on Windows and `~/Library/Logs/FileShift/log.txt` on Mac.
