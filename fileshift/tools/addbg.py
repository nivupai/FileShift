"""Tool windows: Compress, Resize, Crop, Edit, Annotate, Redact, Add BG, Metadata, Protect.

Every window opens on a fast, reduced-size preview. Saving runs on the full-resolution
image in the background (the window closes immediately; a notification reports the result)."""
from __future__ import annotations

from typing import Callable

from PIL import Image
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import (QColor, QGuiApplication, QPixmap)
from PySide6.QtWidgets import (QButtonGroup, QColorDialog, QGridLayout, QLabel, QPushButton)

from .. import imaging
from ..convert import open_image, open_preview
from ..glass import qimage_from_pil
from ..util import sibling

from ._shared import ToolWindow, section, slider, slider_row, toggle_row, dims_text
Notify = Callable[..., None]



# ================================================================ ADD BG
PRESETS = [
    ("Sunset", ["#ffb36b", "#ff5f6d", "#a24bff"]),
    ("Prism", ["#ff6b9d", "#ffb36b", "#ffe66b", "#7dffb0", "#6bd5ff", "#8a7bff"]),
    ("Peach", ["#ffd6a5", "#ff9a8b"]),
    ("Aurora", ["#00d2ff", "#7a5cff", "#ff5fd2"]),
    ("Mint", ["#a8ffce", "#3ad6c6"]),
    ("Ocean", ["#43cbff", "#2058d6"]),
    ("Dusk", ["#2b1055", "#d53a9d"]),
    ("Lemon", ["#fff59d", "#ffb74d"]),
    ("Night", ["#0f2027", "#2c5364"]),
    ("Rose", ["#ffdde1", "#ee9ca7"]),
]
SOLIDS = ["#ffffff", "#f2f2f7", "#d1d1d6", "#8e8e93", "#1c1c1e", "#000000", "#ff3b30",
          "#ff9500", "#ffcc00", "#34c759", "#00c7be", "#007aff", "#5856d6", "#af52de"]


class AddBgWindow(ToolWindow):
    tool_name = "Add BG"
    ASPECTS = ["Auto", "1:1", "4:3", "16:9", "9:16", "4:5"]

    def __init__(self, path, notify):
        super().__init__("Add BG", path, notify, size=(880, 780))
        self.small = open_preview(path, 760)
        with Image.open(path) as im:
            self.full_w = max(im.size) if im.getexif().get(0x0112, 1) in (5, 6, 7, 8) else im.width
            self.full_size = im.size
        self.colors = PRESETS[0][1]

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(360, 300)
        self.body.addWidget(self.preview, 1)
        self.out_label = QLabel()
        self.out_label.setObjectName("dim")
        self.out_label.setAlignment(Qt.AlignCenter)
        self.body.addWidget(self.out_label)

        self.body.addWidget(section("Background"))
        sw = QGridLayout()
        sw.setSpacing(6)
        self.sw_grp = QButtonGroup(self)
        items = [("g", c) for _, c in PRESETS] + [("s", [c]) for c in SOLIDS]
        for i, (_, cols) in enumerate(items):
            b = QPushButton()
            b.setObjectName("swatch")
            b.setCheckable(True)
            b.setStyleSheet(self._swatch_css(cols))
            b.setChecked(i == 0)
            b.setToolTip(PRESETS[i][0] if i < len(PRESETS) else cols[0])
            b.clicked.connect(lambda _=False, c=cols: self._pick(c))
            self.sw_grp.addButton(b, i)
            sw.addWidget(b, i // 12, i % 12)
        custom = QPushButton("＋")
        custom.setObjectName("swatch")
        custom.setToolTip("Custom colour")
        custom.clicked.connect(self._custom)
        sw.addWidget(custom, len(items) // 12, len(items) % 12)
        self.body.addLayout(sw)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        self.pad = slider(0, 40, 12)
        self.rad = slider(0, 120, 24)
        self.sha = slider(0, 100, 50)
        self.ang = slider(0, 360, 135)
        slider_row(grid, 0, "Padding", self.pad, lambda v: f"{v}%")
        slider_row(grid, 1, "Corners", self.rad, lambda v: f"{v} px")
        slider_row(grid, 2, "Shadow", self.sha, lambda v: f"{v}%")
        slider_row(grid, 3, "Angle", self.ang, lambda v: f"{v}°")
        self.body.addLayout(grid)

        self.body.addWidget(section("Size"))
        row, self.asp = toggle_row(self.ASPECTS)
        self.body.addLayout(row)

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setToolTip("Copy the result to the clipboard")
        self.copy_btn.clicked.connect(self.copy)
        self.body.addLayout(self.footer("Save with Background", self.save, self.reset, [self.copy_btn]))

        self._timer = QTimer(self, singleShot=True, interval=16, timeout=self.render)
        for s in (self.pad, self.rad, self.sha, self.ang):
            s.valueChanged.connect(lambda _: self._timer.start())
        self.asp.idClicked.connect(lambda _: self._timer.start())
        self.render()

    @staticmethod
    def _swatch_css(cols: list[str]) -> str:
        if len(cols) == 1:
            return f"background: {cols[0]};"
        stops = ", ".join(f"stop:{i / (len(cols) - 1):.2f} {c}" for i, c in enumerate(cols))
        return f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1, {stops});"

    def _pick(self, cols):
        self.colors = cols
        self.render()

    def _custom(self):
        c = QColorDialog.getColor(QColor(self.colors[0]), self, "Background colour")
        if c.isValid():
            self.colors = [c.name()]
            self.render()

    def _params(self, scale: float) -> imaging.Background:
        return imaging.Background(colors=self.colors, angle=self.ang.value(),
                                  padding=self.pad.value() / 100,
                                  radius=int(self.rad.value() * scale),
                                  shadow=self.sha.value() / 100,
                                  aspect=self.ASPECTS[self.asp.checkedId()])

    def _full_scale(self) -> float:
        return max(1.0, max(self.full_size) / 1000)

    def render(self):
        k = max(self.small.size) / max(self.full_size)
        out = imaging.add_background(self.small, self._params(k * self._full_scale()))
        pm = QPixmap.fromImage(qimage_from_pil(out))
        self.preview.setPixmap(pm.scaled(self.preview.size() - QSize(10, 10), Qt.KeepAspectRatio,
                                         Qt.SmoothTransformation))
        fw = round(out.width / k)
        fh = round(out.height / k)
        self.out_label.setText(f"Output  {dims_text(fw, fh)} px  ·  PNG")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_timer"):
            self._timer.start()

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self.render)

    def reset(self):
        self.pad.setValue(12); self.rad.setValue(24); self.sha.setValue(50); self.ang.setValue(135)
        self.asp.button(0).setChecked(True)
        self.sw_grp.button(0).setChecked(True)
        self._pick(PRESETS[0][1])

    def _compose_full(self) -> Image.Image:
        return imaging.add_background(open_image(self.path), self._params(self._full_scale()))

    def copy(self):
        QGuiApplication.clipboard().setImage(qimage_from_pil(self._compose_full()))
        self.copy_btn.setText("Copied ✓")
        QTimer.singleShot(1400, lambda: self.copy_btn.setText("Copy"))

    def save(self):
        params, path = self._params(self._full_scale()), self.path

        def work():
            out_im = imaging.add_background(open_image(path), params)
            out = sibling(path, "With Background", ".png")
            from .convert import save_image
            save_image(out_im, out, "PNG")
            return [out]
        self.run(work, "Adding background…")
