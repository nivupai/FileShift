"""Tool windows: Compress, Resize, Crop, Edit, Annotate, Redact, Add BG, Metadata, Protect.

Every window opens on a fast, reduced-size preview. Saving runs on the full-resolution
image in the background (the window closes immediately; a notification reports the result)."""
from __future__ import annotations

from typing import Callable

from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QImage, QKeySequence,
                           QPen, QShortcut)
from PySide6.QtWidgets import (QLabel, QPushButton)

from .. import imaging
from ..convert import open_image, open_preview
from ..glass import qimage_from_pil
from ..window import ImageView

from ._shared import ToolWindow, toggle_row
Notify = Callable[..., None]



# ================================================================ REDACT
class RedactView(ImageView):
    def __init__(self, image: QImage, owner: "RedactWindow"):
        super().__init__(image)
        self.owner = owner
        self.rects: list[QRectF] = []
        self.cur: QRectF | None = None
        self._a = QPointF()
        self.setCursor(Qt.CrossCursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.target_rect().contains(e.position()):
            self._a = self.clamp_image(self.to_image(e.position()))
            self.cur = QRectF(self._a, self._a)

    def mouseMoveEvent(self, e):
        if self.cur is not None:
            self.cur = QRectF(self._a, self.clamp_image(self.to_image(e.position()))).normalized()
            self.update()

    def mouseReleaseEvent(self, e):
        if self.cur is not None and self.cur.width() > 2 and self.cur.height() > 2:
            self.rects.append(self.cur)
            self.owner.refresh()
        self.cur = None
        self.update()

    def paint_overlay(self, p, t):
        if self.cur is not None:
            p.setPen(QPen(QColor("#ff5f6d"), 1.5, Qt.DashLine))
            p.setBrush(QColor(0, 0, 0, 90))
            p.drawRect(self.rect_to_widget(self.cur))


class RedactWindow(ToolWindow):
    tool_name = "Redact"
    MODES = ["Black box", "Pixelate", "Blur"]

    def __init__(self, path, notify):
        super().__init__("Redact", path, notify)
        self.base = open_preview(path, 1400)
        with Image.open(path) as im:
            full = im.size if im.getexif().get(0x0112, 1) not in (5, 6, 7, 8) else im.size[::-1]
        self.k = full[0] / self.base.width
        self.view = RedactView(qimage_from_pil(self.base), self)
        self.body.addWidget(self.view, 1)
        self.hint = QLabel("Drag over anything you want hidden. It's burned into the pixels — it can't be undone in the copy.")
        self.hint.setObjectName("dim")
        self.body.addWidget(self.hint)
        row, self.mode = toggle_row(self.MODES)
        self.mode.idClicked.connect(lambda _: self.refresh())
        undo = QPushButton("Undo")
        undo.clicked.connect(self.undo)
        QShortcut(QKeySequence.Undo, self, activated=self.undo)
        row.addWidget(undo)
        self.body.addLayout(row)
        self.body.addLayout(self.footer("Save", self.save))

    def _mode(self):
        return ["black", "pixelate", "blur"][self.mode.checkedId()]

    def _boxes(self, k: float):
        return [tuple(round(v * k) for v in (r.left(), r.top(), r.right(), r.bottom())) for r in self.view.rects]

    def refresh(self):
        im = imaging.redact(self.base, self._boxes(1.0), self._mode())
        self.view.set_image(qimage_from_pil(im))
        n = len(self.view.rects)
        self.subtitle.setText(f"{self.path.name}  ·  {n} area{'s' if n != 1 else ''} hidden" if n else self.path.name)

    def undo(self):
        if self.view.rects:
            self.view.rects.pop()
            self.refresh()

    def save(self):
        boxes, mode, path = self._boxes(self.k), self._mode(), self.path
        if not boxes:
            self.close()
            return
        label = {"black": "black boxes", "pixelate": "pixelated", "blur": "blurred"}[mode]

        def work():
            return [imaging.save_like(imaging.redact(open_image(path), boxes, mode), path, "Redacted")]
        self.run(work, "Redacting…", f"{len(boxes)} area{'s' if len(boxes) != 1 else ''} {label}")
