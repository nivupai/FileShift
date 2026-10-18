"""Tool windows: Compress, Resize, Crop, Edit, Annotate, Redact, Add BG, Metadata, Protect.

Every window opens on a fast, reduced-size preview. Saving runs on the full-resolution
image in the background (the window closes immediately; a notification reports the result)."""
from __future__ import annotations

from typing import Callable

from PIL import Image
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import (QPixmap)
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QPushButton)

from .. import imaging
from ..convert import open_image, open_preview
from ..glass import qimage_from_pil

from ._shared import ToolWindow, slider, slider_row
Notify = Callable[..., None]



# ================================================================ EDIT
class EditWindow(ToolWindow):
    tool_name = "Edit"

    def __init__(self, path, notify):
        super().__init__("Edit", path, notify, size=(880, 780))
        self.small = open_preview(path, 900)
        with Image.open(path) as im:
            self.full_size = im.size if im.getexif().get(0x0112, 1) not in (5, 6, 7, 8) else im.size[::-1]
        self.adj = imaging.Adjust()
        self.comparing = False

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(360, 300)
        self.body.addWidget(self.preview, 1)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        self.sl = {
            "brightness": slider(-100, 100, 0), "contrast": slider(-100, 100, 0),
            "saturation": slider(-100, 100, 0), "warmth": slider(-100, 100, 0),
            "sharpness": slider(-100, 100, 0),
        }
        for i, (k, s) in enumerate(self.sl.items()):
            slider_row(grid, i, k.capitalize(), s, lambda v: f"{v:+d}")
            s.valueChanged.connect(lambda _: self._timer.start())
        self.size_sl = slider(5, 100, 100)
        slider_row(grid, len(self.sl), "Size", self.size_sl, lambda v: f"{v}%")
        self.size_sl.valueChanged.connect(self._size_label)
        self.dim_label = QLabel()
        self.dim_label.setObjectName("dim")
        grid.addWidget(self.dim_label, len(self.sl) + 1, 1)
        self.body.addLayout(grid)

        row = QHBoxLayout()
        auto = QPushButton("✦ Auto")
        auto.setToolTip("Automatic light and colour")
        auto.clicked.connect(self.auto)
        row.addWidget(auto)
        for text, fn in (("⟲", lambda: self._rot(-90)), ("⟳", lambda: self._rot(90)),
                         ("⇋ Flip", lambda: self._flip("h")), ("⇵ Flip", lambda: self._flip("v"))):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        self.gray = QPushButton("B&&W")
        self.gray.setCheckable(True)
        self.gray.toggled.connect(lambda _: self._timer.start())
        row.addWidget(self.gray)
        row.addStretch(1)
        cmp_btn = QPushButton("Hold to compare")
        cmp_btn.pressed.connect(lambda: self._compare(True))
        cmp_btn.released.connect(lambda: self._compare(False))
        row.addWidget(cmp_btn)
        self.body.addLayout(row)
        self.body.addLayout(self.footer("Save", self.save, self.reset))

        self._timer = QTimer(self, singleShot=True, interval=16, timeout=self.render)
        self._size_label()
        self.render()

    def _compare(self, on: bool):
        self.comparing = on
        self.render()

    def auto(self):
        a = imaging.auto_enhance(self.small)
        vals = {"brightness": a.brightness - 1, "contrast": a.contrast - 1, "saturation": a.saturation - 1,
                "sharpness": (a.sharpness - 1) / 2}
        for k, v in vals.items():
            self.sl[k].setValue(int(round(v * 100)))

    def _size_label(self):
        p = self.size_sl.value() / 100
        w, h = self.full_size
        if self.adj.rotate % 180:
            w, h = h, w
        self.dim_label.setText(f"{round(w * p)} × {round(h * p)} px")

    def _rot(self, d):
        self.adj.rotate = (self.adj.rotate + d) % 360
        self._size_label()
        self.render()

    def _flip(self, axis):
        if axis == "h":
            self.adj.flip_h = not self.adj.flip_h
        else:
            self.adj.flip_v = not self.adj.flip_v
        self.render()

    def _collect(self, resize: bool) -> imaging.Adjust:
        f = lambda k: 1 + self.sl[k].value() / 100
        a = self.adj
        a.brightness, a.contrast, a.saturation = f("brightness"), f("contrast"), f("saturation")
        a.sharpness = 1 + self.sl["sharpness"].value() / 50
        a.warmth = self.sl["warmth"].value() / 100
        a.grayscale = self.gray.isChecked()
        a.resize_pct = self.size_sl.value() if resize else 100
        return a

    def render(self):
        out = self.small if self.comparing else imaging.apply_adjust(self.small, self._collect(False))
        pm = QPixmap.fromImage(qimage_from_pil(out))
        self.preview.setPixmap(pm.scaled(self.preview.size() - QSize(10, 10), Qt.KeepAspectRatio,
                                         Qt.SmoothTransformation))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_timer"):
            self._timer.start()

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self.render)

    def reset(self):
        for s in self.sl.values():
            s.setValue(0)
        self.size_sl.setValue(100)
        self.gray.setChecked(False)
        self.adj = imaging.Adjust()
        self._size_label()
        self.render()

    def _summary(self) -> str:
        bits = [f"{k} {s.value():+d}" for k, s in self.sl.items() if s.value()]
        if self.adj.rotate:
            bits.append(f"rotated {self.adj.rotate}°")
        if self.adj.flip_h or self.adj.flip_v:
            bits.append("flipped")
        if self.gray.isChecked():
            bits.append("B&W")
        return ", ".join(bits[:4])

    def save(self):
        adj = imaging.Adjust(**vars(self._collect(True)))
        path = self.path

        def work():
            return [imaging.save_like(imaging.apply_adjust(open_image(path), adj), path, "Edited")]
        self.run(work, "Applying edits…", self._summary())
