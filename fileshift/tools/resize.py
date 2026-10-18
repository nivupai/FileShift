"""Tool windows: Compress, Resize, Crop, Edit, Annotate, Redact, Add BG, Metadata, Protect.

Every window opens on a fast, reduced-size preview. Saving runs on the full-resolution
image in the background (the window closes immediately; a notification reports the result)."""
from __future__ import annotations

from typing import Callable

from PIL import Image
from PySide6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QSpinBox)

from .. import imaging

from ._shared import ToolWindow, section, toggle_row, dims_text
Notify = Callable[..., None]



# ================================================================ RESIZE
class ResizeWindow(ToolWindow):
    tool_name = "Resize"
    PRESETS = [("25%", "pct", 25), ("50%", "pct", 50), ("75%", "pct", 75), ("3840", "long", 3840),
               ("2560", "long", 2560), ("1920", "long", 1920), ("1280", "long", 1280), ("800", "long", 800)]

    def __init__(self, paths, notify):
        super().__init__("Resize", paths, notify, size=(600, 380))
        with Image.open(self.path) as im:
            w, h = im.size
            if im.getexif().get(0x0112, 1) in (5, 6, 7, 8):
                w, h = h, w
        self.orig = (w, h)
        self.body.addWidget(section("Presets — percent or longest side in px"))
        row, self.grp = toggle_row([p[0] for p in self.PRESETS], 1)
        self.grp.idClicked.connect(self._preset)
        self.body.addLayout(row)
        self.body.addWidget(section("Exact size"))
        er = QHBoxLayout()
        self.w = QSpinBox()
        self.h = QSpinBox()
        for s in (self.w, self.h):
            s.setRange(1, 30000)
            s.setFixedWidth(100)
        self.lock = QCheckBox("Keep proportions")
        self.lock.setChecked(True)
        er.addWidget(QLabel("W"))
        er.addWidget(self.w)
        er.addWidget(QLabel("H"))
        er.addWidget(self.h)
        er.addWidget(QLabel("px"))
        er.addSpacing(10)
        er.addWidget(self.lock)
        er.addStretch(1)
        self.body.addLayout(er)
        self.out = QLabel()
        self.out.setObjectName("big")
        self.body.addWidget(self.out)
        self.body.addStretch(1)
        label = "Resize" if len(self.paths) == 1 else f"Resize {len(self.paths)} files"
        self.body.addLayout(self.footer(label, self.save))
        self.w.valueChanged.connect(lambda v: self._typed("w", v))
        self.h.valueChanged.connect(lambda v: self._typed("h", v))
        self._preset(1)

    def _set(self, w, h):
        for box, v in ((self.w, w), (self.h, h)):
            box.blockSignals(True)
            box.setValue(v)
            box.blockSignals(False)
        self.out.setText(f"{dims_text(*self.orig)}  →  {dims_text(w, h)}")

    def _preset(self, i):
        _, mode, val = self.PRESETS[i]
        self.mode = (mode, val)
        self._set(*imaging.resize_dims(self.orig, mode, val))

    def _typed(self, which, v):
        b = self.grp.checkedButton()
        if b:
            self.grp.setExclusive(False)
            b.setChecked(False)
            self.grp.setExclusive(True)
        if self.lock.isChecked():
            w, h = imaging.resize_dims(self.orig, which, v)
        else:
            w, h = self.w.value(), self.h.value()
        self.mode = (which, v) if self.lock.isChecked() else ("exact", (w, h))
        self._set(w, h)

    def save(self):
        mode, val = self.mode
        paths = list(self.paths)

        def dims_for(p):
            with Image.open(p) as im:
                size = im.size if im.getexif().get(0x0112, 1) not in (5, 6, 7, 8) else im.size[::-1]
            if mode == "exact":
                return val
            return imaging.resize_dims(size, mode, val)
        self.run(lambda: [imaging.resize_image(p, dims_for(p)) for p in paths], "Resizing…")
