"""Tool windows: Compress, Resize, Crop, Edit, Annotate, Redact, Add BG, Metadata, Protect.

Every window opens on a fast, reduced-size preview. Saving runs on the full-resolution
image in the background (the window closes immediately; a notification reports the result)."""
from __future__ import annotations

from typing import Callable

from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QImage, QPainter, QPainterPath, QPen)
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QSpinBox)

from .. import imaging
from ..convert import open_image, open_preview
from ..glass import qimage_from_pil
from ..window import ImageView

from ._shared import ToolWindow, section, toggle_row, dims_text
Notify = Callable[..., None]



# ================================================================ CROP
class CropView(ImageView):
    HANDLE = 9

    def __init__(self, image: QImage, k: float):
        super().__init__(image)
        self.k = k
        self.ratio: float | None = None
        self.sel = QRectF(0, 0, image.width(), image.height())
        self._mode: str | None = None
        self._start = QPointF()
        self._orig = QRectF()

    def set_ratio(self, ratio: float | None):
        self.ratio = ratio
        if ratio:
            W, H = self.image.width(), self.image.height()
            w, h = W, W / ratio
            if h > H:
                h, w = H, H * ratio
            self.sel = QRectF((W - w) / 2, (H - h) / 2, w, h)
        self.update()
        self.changed.emit()

    def reset_sel(self):
        self.sel = QRectF(0, 0, self.image.width(), self.image.height())
        if self.ratio:
            self.set_ratio(self.ratio)
        self.update()
        self.changed.emit()

    def _hit(self, pos: QPointF) -> str | None:
        r = self.rect_to_widget(self.sel)
        h = self.HANDLE + 4
        near = lambda a, b: abs(a - b) <= h
        l, t, rt, b = near(pos.x(), r.left()), near(pos.y(), r.top()), near(pos.x(), r.right()), near(pos.y(), r.bottom())
        inside_x = r.left() - h <= pos.x() <= r.right() + h
        inside_y = r.top() - h <= pos.y() <= r.bottom() + h
        if t and l: return "tl"
        if t and rt: return "tr"
        if b and l: return "bl"
        if b and rt: return "br"
        if t and inside_x: return "t"
        if b and inside_x: return "b"
        if l and inside_y: return "l"
        if rt and inside_y: return "r"
        if r.contains(pos): return "move"
        return None

    CURSORS = {"tl": Qt.SizeFDiagCursor, "br": Qt.SizeFDiagCursor, "tr": Qt.SizeBDiagCursor,
               "bl": Qt.SizeBDiagCursor, "t": Qt.SizeVerCursor, "b": Qt.SizeVerCursor,
               "l": Qt.SizeHorCursor, "r": Qt.SizeHorCursor, "move": Qt.SizeAllCursor}

    def mousePressEvent(self, e):
        self._mode = self._hit(e.position())
        if self._mode is None and self.target_rect().contains(e.position()):
            self._mode = "new"
        self._start = self.clamp_image(self.to_image(e.position()))
        self._orig = QRectF(self.sel)

    def mouseDoubleClickEvent(self, e):
        self.reset_sel()

    def mouseMoveEvent(self, e):
        if not self._mode:
            m = self._hit(e.position())
            self.setCursor(self.CURSORS.get(m, Qt.CrossCursor))
            return
        p = self.clamp_image(self.to_image(e.position()))
        W, H = self.image.width(), self.image.height()
        r = QRectF(self._orig)
        if self._mode == "move":
            d = p - self._start
            r.translate(d)
            r.moveLeft(min(max(r.left(), 0), W - r.width()))
            r.moveTop(min(max(r.top(), 0), H - r.height()))
        elif self._mode == "new":
            r = QRectF(self._start, p).normalized()
            if self.ratio and r.height() > 0:
                r.setHeight(r.width() / self.ratio)
        else:
            if "l" in self._mode: r.setLeft(p.x())
            if "r" in self._mode: r.setRight(p.x())
            if "t" in self._mode: r.setTop(p.y())
            if "b" in self._mode: r.setBottom(p.y())
            r = r.normalized()
            if self.ratio:
                if self._mode in ("t", "b"):
                    r.setWidth(r.height() * self.ratio)
                else:
                    nh = r.width() / self.ratio
                    if "t" in self._mode:
                        r.setTop(r.bottom() - nh)
                    else:
                        r.setHeight(nh)
        r = r.intersected(QRectF(0, 0, W, H))
        if r.width() >= 4 and r.height() >= 4:
            self.sel = r
        self.update()
        self.changed.emit()

    def mouseReleaseEvent(self, e):
        self._mode = None

    def paint_overlay(self, p: QPainter, t: QRectF):
        r = self.rect_to_widget(self.sel)
        shade = QPainterPath()
        shade.addRect(t)
        hole = QPainterPath()
        hole.addRect(r)
        p.fillPath(shade.subtracted(hole), QColor(0, 0, 0, 140))
        p.setPen(QPen(QColor(255, 255, 255, 230), 1.5))
        p.drawRect(r)
        p.setPen(QPen(QColor(255, 255, 255, 70), 1))
        for i in (1, 2):  # rule of thirds
            x = r.left() + r.width() * i / 3
            y = r.top() + r.height() * i / 3
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#ff6a4d"))
        for pt in (r.topLeft(), r.topRight(), r.bottomLeft(), r.bottomRight()):
            p.drawEllipse(pt, 5.5, 5.5)
        # live output size badge
        txt = dims_text(round(self.sel.width() * self.k), round(self.sel.height() * self.k))
        f = QFont("Segoe UI", 1)
        f.setPixelSize(12)
        f.setBold(True)
        p.setFont(f)
        w = p.fontMetrics().horizontalAdvance(txt) + 18
        badge = QRectF(r.center().x() - w / 2, r.bottom() - 30, w, 22)
        if badge.top() < r.top() + 4:
            badge.moveTop(r.bottom() + 6)
        p.setBrush(QColor(20, 16, 32, 190))
        p.drawRoundedRect(badge, 11, 11)
        p.setPen(QColor(255, 255, 255))
        p.drawText(badge, Qt.AlignCenter, txt)


class CropWindow(ToolWindow):
    tool_name = "Crop"
    RATIOS = [("Free", None), ("Original", "orig"), ("1:1", 1.0), ("4:3", 4 / 3), ("3:2", 1.5),
              ("16:9", 16 / 9), ("9:16", 9 / 16), ("4:5", 0.8)]

    def __init__(self, path, notify):
        super().__init__("Crop Image", path, notify)
        pv = open_preview(path, 1400)
        with Image.open(path) as im:
            fw, fh = im.size
        with Image.open(path) as im:
            o = im.getexif().get(0x0112, 1)
        if o in (5, 6, 7, 8):
            fw, fh = fh, fw
        self.full_size = (fw, fh)
        self.rot = 0
        self.base = pv
        self.view = CropView(qimage_from_pil(pv), fw / pv.width)
        self.body.addWidget(self.view, 1)

        self.body.addWidget(section("Aspect ratio"))
        row, self.grp = toggle_row([n for n, _ in self.RATIOS])
        self.grp.idClicked.connect(self._ratio)
        for txt, d in (("⟲", -90), ("⟳", 90)):
            b = QPushButton(txt)
            b.setToolTip("Rotate 90°")
            b.clicked.connect(lambda _=False, d=d: self._rotate(d))
            row.addWidget(b)
        self.body.addLayout(row)

        dims = QHBoxLayout()
        self.w = QSpinBox()
        self.h = QSpinBox()
        for s in (self.w, self.h):
            s.setRange(1, 100000)
            s.setFixedWidth(96)
        dims.addWidget(QLabel("W"))
        dims.addWidget(self.w)
        dims.addWidget(QLabel("H"))
        dims.addWidget(self.h)
        dims.addWidget(QLabel("px"))
        dims.addStretch(1)
        tip = QLabel("Double-click the image to reset")
        tip.setObjectName("dim")
        dims.addWidget(tip)
        self.body.addLayout(dims)
        self.w.editingFinished.connect(self._from_spin)
        self.h.editingFinished.connect(self._from_spin)
        self.view.changed.connect(self._to_spin)
        self._to_spin()
        self.body.addLayout(self.footer("Apply", self.apply, self.reset))

    def _ratio(self, i):
        r = self.RATIOS[i][1]
        if r == "orig":
            r = self.view.image.width() / self.view.image.height()
        self.view.set_ratio(r)

    def _rotate(self, d):
        self.rot = (self.rot + d) % 360
        img = self.base.rotate(-self.rot, expand=True)
        k = self.view.k
        self.view.set_image(qimage_from_pil(img))
        self.view.k = k
        self.view.reset_sel()

    def _to_spin(self):
        s = self.view.sel
        k = self.view.k
        for box, v in ((self.w, s.width()), (self.h, s.height())):
            box.blockSignals(True)
            box.setValue(round(v * k))
            box.blockSignals(False)

    def _from_spin(self):
        k = self.view.k
        s = QRectF(self.view.sel)
        s.setWidth(self.w.value() / k)
        s.setHeight(self.h.value() / k)
        self.view.sel = s.intersected(QRectF(0, 0, self.view.image.width(), self.view.image.height()))
        self.view.update()
        self._to_spin()

    def reset(self):
        self.grp.button(0).setChecked(True)
        self.view.ratio = None
        if self.rot:
            self.rot = 0
            self.view.set_image(qimage_from_pil(self.base))
        self.view.reset_sel()

    def apply(self):
        s, k, rot, path = self.view.sel, self.view.k, self.rot, self.path
        fw, fh = (self.full_size[1], self.full_size[0]) if rot % 180 else self.full_size
        x0, y0 = round(s.left() * k), round(s.top() * k)
        w, h = round(s.width() * k), round(s.height() * k)
        # preview → full-size rounding: snap to the image edges when within 3 px
        if x0 <= 3:
            w, x0 = w + x0, 0
        if y0 <= 3:
            h, y0 = h + y0, 0
        snap_w = abs(x0 + w - fw) <= 3
        snap_h = abs(y0 + h - fh) <= 3
        if snap_w:
            w = fw - x0
        if snap_h:
            h = fh - y0
        if self.view.ratio:  # exact ratio (no 1600×1599)
            r = self.view.ratio
            if snap_h and not snap_w:
                w = round(h * r)
            else:
                h = round(w / r)
            if y0 + h > fh:
                h = fh - y0
                w = round(h * r)
            if x0 + w > fw:
                w = fw - x0
                h = round(w / r)
        box = (x0, y0, x0 + w, y0 + h)

        def work():
            im = open_image(path)
            if rot:
                im = im.rotate(-rot, expand=True)
            return [imaging.save_like(im.crop(box), path, "Cropped")]
        extra = f"rotated {rot}°" if rot else ""
        self.run(work, "Cropping…", extra)
