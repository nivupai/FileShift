"""Tool windows: Compress, Resize, Crop, Edit, Annotate, Redact, Add BG, Metadata, Protect.

Every window opens on a fast, reduced-size preview. Saving runs on the full-resolution
image in the background (the window closes immediately; a notification reports the result)."""
from __future__ import annotations

import math
from typing import Callable

from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QImage, QKeySequence,
                           QPainter, QPainterPath, QPen, QPolygonF, QShortcut)
from PySide6.QtWidgets import (QButtonGroup, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton)

from .. import imaging
from ..convert import open_image, open_preview
from ..glass import pil_from_qimage, qimage_from_pil
from ..window import ImageView

from ._shared import ToolWindow, slider, toggle_row
Notify = Callable[..., None]



# ================================================================ ANNOTATE
class Shape:
    def __init__(self, kind, color, width, pts=None, text=""):
        self.kind, self.color, self.width = kind, QColor(color), width
        self.pts: list[QPointF] = pts or []
        self.text = text


def draw_shape(p: QPainter, s: Shape, map_pt, scale: float):
    pts = [map_pt(q) for q in s.pts]
    w = max(1.0, s.width * scale)
    col = QColor(s.color)
    if s.kind == "Highlight":
        col.setAlpha(110)
        w *= 4
    pen = QPen(col, w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    if s.kind in ("Pen", "Highlight") and len(pts) > 1:
        path = QPainterPath(pts[0])
        for q in pts[1:]:
            path.lineTo(q)
        p.drawPath(path)
    elif s.kind == "Arrow" and len(pts) == 2:
        a, b = pts
        ang = math.atan2(b.y() - a.y(), b.x() - a.x())
        head = max(12.0, w * 4.2)
        base = QPointF(b.x() - head * 0.8 * math.cos(ang), b.y() - head * 0.8 * math.sin(ang))
        p.drawLine(a, base)
        left = QPointF(b.x() - head * math.cos(ang - 0.42), b.y() - head * math.sin(ang - 0.42))
        right = QPointF(b.x() - head * math.cos(ang + 0.42), b.y() - head * math.sin(ang + 0.42))
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        p.drawPolygon(QPolygonF([b, left, right]))
    elif s.kind == "Rect" and len(pts) == 2:
        p.drawRoundedRect(QRectF(pts[0], pts[1]).normalized(), w, w)
    elif s.kind == "Ellipse" and len(pts) == 2:
        p.drawEllipse(QRectF(pts[0], pts[1]).normalized())
    elif s.kind == "Text" and pts:
        f = QFont("Segoe UI", 1)
        f.setPixelSize(max(8, int(s.width * 5 * scale)))
        f.setBold(True)
        p.setFont(f)
        # outline for legibility on any background
        outline = QPainterPath()
        outline.addText(pts[0], f, s.text)
        lum = col.red() * 0.3 + col.green() * 0.59 + col.blue() * 0.11
        p.setPen(QPen(QColor(0, 0, 0, 160) if lum > 128 else QColor(255, 255, 255, 190), max(2.0, w * 0.6)))
        p.drawPath(outline)
        p.fillPath(outline, col)
    elif s.kind == "Step" and pts:
        r = max(10.0, s.width * 3.2 * scale)
        c = pts[0]
        p.setPen(QPen(QColor(255, 255, 255), max(1.5, r * 0.12)))
        p.setBrush(col)
        p.drawEllipse(c, r, r)
        f = QFont("Segoe UI", 1)
        f.setPixelSize(int(r * 1.15))
        f.setBold(True)
        p.setFont(f)
        lum = col.red() * 0.3 + col.green() * 0.59 + col.blue() * 0.11
        p.setPen(QColor(20, 20, 20) if lum > 170 else QColor(255, 255, 255))
        p.drawText(QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r), Qt.AlignCenter, s.text)


class AnnotateView(ImageView):
    def __init__(self, image: QImage, owner: "AnnotateWindow"):
        super().__init__(image)
        self.owner = owner
        self.shapes: list[Shape] = []
        self.redo_stack: list[Shape] = []
        self.cur: Shape | None = None
        self.editor: QLineEdit | None = None
        self.setCursor(Qt.CrossCursor)

    def next_step(self) -> int:
        return sum(1 for s in self.shapes if s.kind == "Step") + 1

    def _commit_text(self):
        ed = self.editor
        if ed is None:
            return
        self.editor = None
        text = ed.text().strip()
        if text:
            self.add(Shape("Text", ed.property("color"), ed.property("w"), [ed.property("pt")], text))
        ed.deleteLater()

    def add(self, s: Shape):
        self.shapes.append(s)
        self.redo_stack.clear()
        self.update()

    def mousePressEvent(self, e):
        self._commit_text()
        if e.button() != Qt.LeftButton or not self.target_rect().contains(e.position()):
            return
        o = self.owner
        p = self.to_image(e.position())
        width = o.stroke.value() / self.scale()  # keep on-screen thickness consistent
        if o.tool == "Text":
            ed = QLineEdit(self)
            ed.setPlaceholderText("Type, then Enter")
            ed.setProperty("pt", p)
            ed.setProperty("color", o.color)
            ed.setProperty("w", width)
            ed.move(int(e.position().x()), int(e.position().y()) - 16)
            ed.resize(220, 30)
            ed.show()
            ed.setFocus()
            ed.returnPressed.connect(self._commit_text)
            self.editor = ed
            return
        if o.tool == "Step":
            self.add(Shape("Step", o.color, width, [p], str(self.next_step())))
            return
        self.cur = Shape(o.tool, o.color, width, [p, p] if o.tool not in ("Pen", "Highlight") else [p])

    def mouseMoveEvent(self, e):
        if not self.cur:
            return
        p = self.clamp_image(self.to_image(e.position()))
        if self.cur.kind in ("Pen", "Highlight"):
            self.cur.pts.append(p)
        else:
            self.cur.pts[1] = p
        self.update()

    def mouseReleaseEvent(self, e):
        if self.cur:
            self.add(self.cur)
            self.cur = None

    def paint_overlay(self, p, t):
        s = self.scale()
        for sh in self.shapes + ([self.cur] if self.cur else []):
            draw_shape(p, sh, self.to_widget, s)


class AnnotateWindow(ToolWindow):
    tool_name = "Annotate"
    TOOLS = ["Arrow", "Rect", "Ellipse", "Pen", "Highlight", "Text", "Step"]
    COLORS = ["#ff3b30", "#ff9500", "#ffcc00", "#34c759", "#007aff", "#af52de", "#ffffff", "#000000"]

    def __init__(self, path, notify):
        super().__init__("Annotate", path, notify, size=(900, 720))
        pv = open_preview(path, 1600)
        with Image.open(path) as im:
            full = im.size if im.getexif().get(0x0112, 1) not in (5, 6, 7, 8) else im.size[::-1]
        self.k = full[0] / pv.width
        self.tool, self.color = "Arrow", self.COLORS[0]
        self.view = AnnotateView(qimage_from_pil(pv), self)
        self.body.addWidget(self.view, 1)

        row, grp = toggle_row(["➜ Arrow", "▢ Box", "◯ Circle", "✎ Pen", "▬ Marker", "T Text", "① Step"])
        grp.idClicked.connect(lambda i: setattr(self, "tool", self.TOOLS[i]))
        undo = QPushButton("Undo")
        undo.clicked.connect(self.undo)
        redo = QPushButton("Redo")
        redo.clicked.connect(self.redo)
        QShortcut(QKeySequence.Undo, self, activated=self.undo)
        QShortcut(QKeySequence.Redo, self, activated=self.redo)
        QShortcut(QKeySequence("Ctrl+Y"), self, activated=self.redo)
        row.addWidget(undo)
        row.addWidget(redo)
        self.body.addLayout(row)

        crow = QHBoxLayout()
        cgrp = QButtonGroup(self)
        for i, c in enumerate(self.COLORS):
            b = QPushButton()
            b.setObjectName("swatch")
            b.setCheckable(True)
            b.setChecked(i == 0)
            b.setStyleSheet(f"background: {c};")
            b.clicked.connect(lambda _=False, c=c: setattr(self, "color", c))
            cgrp.addButton(b)
            crow.addWidget(b)
        crow.addSpacing(16)
        crow.addWidget(QLabel("Size"))
        self.stroke = slider(1, 20, 4)
        self.stroke.setFixedWidth(160)
        crow.addWidget(self.stroke)
        crow.addStretch(1)
        self.body.addLayout(crow)
        self.body.addLayout(self.footer("Save", self.save))

    def undo(self):
        if self.view.shapes:
            self.view.redo_stack.append(self.view.shapes.pop())
            self.view.update()

    def redo(self):
        if self.view.redo_stack:
            self.view.shapes.append(self.view.redo_stack.pop())
            self.view.update()

    def save(self):
        self.view._commit_text()
        shapes = list(self.view.shapes)
        if not shapes:
            self.close()
            return
        k, path = self.k, self.path
        counts: dict[str, int] = {}
        for s in shapes:
            counts[s.kind] = counts.get(s.kind, 0) + 1
        names = {"Arrow": "arrow", "Rect": "box", "Ellipse": "circle", "Pen": "stroke", "Highlight": "highlight",
                 "Text": "label", "Step": "step"}
        extra = ", ".join(f"{n} {names[t]}{'s' if n > 1 else ''}" for t, n in counts.items())

        def work():
            img = qimage_from_pil(open_image(path).convert("RGBA"))
            p = QPainter(img)
            p.setRenderHint(QPainter.Antialiasing)
            p.setRenderHint(QPainter.TextAntialiasing)
            for sh in shapes:
                draw_shape(p, sh, lambda q: QPointF(q.x() * k, q.y() * k), k)
            p.end()
            return [imaging.save_like(pil_from_qimage(img), path, "Annotated")]
        self.run(work, "Saving annotations…", extra)
