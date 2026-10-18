"""Tool window: Watermark."""
from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QColorDialog, QGridLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton)

from .. import imaging
from ..convert import open_image, open_preview, save_image
from ..glass import qimage_from_pil
from ..util import sibling
from .addbg import SOLIDS

from ._shared import ToolWindow, section, slider, slider_row

POSITION_LABELS = [("↖", "tl"), ("↗", "tr"), ("↙", "bl"), ("↘", "br"), ("◎", "center")]


class WatermarkWindow(ToolWindow):
    tool_name = "Watermark"

    def __init__(self, path, notify):
        super().__init__("Watermark", path, notify, size=(820, 720))
        self.small = open_preview(path, 900)
        with Image.open(path) as im:
            self.full_size = im.size
        self.color = "#ffffff"
        self.position = "br"

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(360, 300)
        self.body.addWidget(self.preview, 1)

        self.body.addWidget(section("Text"))
        self.text = QLineEdit("© Your Name")
        self.text.textChanged.connect(lambda _: self._timer.start())
        self.body.addWidget(self.text)

        self.body.addWidget(section("Position"))
        pos_row = QHBoxLayout()
        self.pos_grp = QButtonGroup(self)
        self.pos_grp.setExclusive(True)
        for i, (glyph, key) in enumerate(POSITION_LABELS):
            b = QPushButton(glyph)
            b.setCheckable(True)
            b.setChecked(key == self.position)
            b.setToolTip(key)
            self.pos_grp.addButton(b, i)
            pos_row.addWidget(b)
        self.pos_grp.idClicked.connect(self._set_position)
        self.tile = QCheckBox("Tile across image")
        self.tile.toggled.connect(lambda _: self._timer.start())
        pos_row.addStretch(1)
        pos_row.addWidget(self.tile)
        self.body.addLayout(pos_row)

        self.body.addWidget(section("Colour"))
        sw = QGridLayout()
        sw.setSpacing(6)
        self.sw_grp = QButtonGroup(self)
        for i, c in enumerate(SOLIDS):
            b = QPushButton()
            b.setObjectName("swatch")
            b.setCheckable(True)
            b.setStyleSheet(f"background: {c};")
            b.setChecked(c == self.color)
            b.setToolTip(c)
            b.clicked.connect(lambda _=False, c=c: self._pick(c))
            self.sw_grp.addButton(b, i)
            sw.addWidget(b, i // 12, i % 12)
        custom = QPushButton("＋")
        custom.setObjectName("swatch")
        custom.setToolTip("Custom colour")
        custom.clicked.connect(self._custom)
        sw.addWidget(custom, len(SOLIDS) // 12, len(SOLIDS) % 12)
        self.body.addLayout(sw)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        self.opacity = slider(5, 100, 55)
        self.size = slider(2, 20, 6)
        slider_row(grid, 0, "Opacity", self.opacity, lambda v: f"{v}%")
        slider_row(grid, 1, "Size", self.size, lambda v: f"{v}%")
        self.body.addLayout(grid)

        self.body.addLayout(self.footer("Save", self.save, self.reset))

        self._timer = QTimer(self, singleShot=True, interval=16, timeout=self.render)
        for s in (self.opacity, self.size):
            s.valueChanged.connect(lambda _: self._timer.start())
        self.render()

    def _set_position(self, i):
        self.position = POSITION_LABELS[i][1]
        self.render()

    def _pick(self, c):
        self.color = c
        self.render()

    def _custom(self):
        c = QColorDialog.getColor(QColor(self.color), self, "Watermark colour")
        if c.isValid():
            self.color = c.name()
            self.render()

    def _params(self) -> imaging.Watermark:
        return imaging.Watermark(text=self.text.text() or " ", position=self.position,
                                 opacity=self.opacity.value(), size_pct=self.size.value(),
                                 color=self.color, tile=self.tile.isChecked())

    def render(self):
        out = imaging.apply_watermark(self.small, self._params())
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
        self.text.setText("© Your Name")
        self.opacity.setValue(55)
        self.size.setValue(6)
        self.tile.setChecked(False)
        self.pos_grp.button(3).setChecked(True)
        self._set_position(3)
        self._pick("#ffffff")

    def save(self):
        params, path = self._params(), self.path

        def work():
            out_im = imaging.apply_watermark(open_image(path), params)
            out = sibling(path, "Watermarked", Path(path).suffix.lower())
            save_image(out_im, out, imaging.target_for(out))
            return [out]
        self.run(work, "Adding watermark…")
