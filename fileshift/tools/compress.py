"""Tool windows: Compress, Resize, Crop, Edit, Annotate, Redact, Add BG, Metadata, Protect.

Every window opens on a fast, reduced-size preview. Saving runs on the full-resolution
image in the background (the window closes immediately; a notification reports the result)."""
from __future__ import annotations

import io
from typing import Callable

from PIL import Image
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (QPixmap)
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget)

from .. import imaging
from ..convert import open_image, open_preview
from ..glass import qimage_from_pil
from ..util import file_size, human_size

from ._shared import ToolWindow, slider, slider_row, toggle_row
Notify = Callable[..., None]



# ================================================================ COMPRESS
class CompressWindow(ToolWindow):
    tool_name = "Compress"
    SIDES = [("Original size", None), ("Max 3840 px", 3840), ("Max 2560 px", 2560),
             ("Max 1920 px", 1920), ("Max 1280 px", 1280), ("Max 800 px", 800)]
    TARGETS = [("2 MB", 2_000_000), ("1 MB", 1_000_000), ("500 KB", 500_000), ("200 KB", 200_000), ("100 KB", 100_000)]

    def __init__(self, paths, notify):
        super().__init__("Compress", paths, notify, size=(640, 580))
        self.orig_total = sum(file_size(p) for p in self.paths)
        self.pv = open_preview(self.path, 1600)
        with Image.open(self.path) as im:
            self.full_px = im.width * im.height
            self.full_long = max(im.size)

        row, self.mode = toggle_row(["Quality", "Target size"])
        self.body.addLayout(row)

        self.q_box = QWidget()
        g = QGridLayout(self.q_box)
        g.setContentsMargins(0, 0, 0, 0)
        self.q = slider(10, 95, 72)
        slider_row(g, 0, "Quality", self.q, lambda v: f"{v}")
        self.body.addWidget(self.q_box)

        self.t_box = QWidget()
        tl = QHBoxLayout(self.t_box)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.addWidget(QLabel("Make each file under"))
        self.tgrp = QButtonGroup(self)
        for i, (lbl, _) in enumerate(self.TARGETS):
            b = QPushButton(lbl)
            b.setCheckable(True)
            b.setChecked(i == 2)
            self.tgrp.addButton(b, i)
            tl.addWidget(b)
        tl.addStretch(1)
        self.t_box.setVisible(False)
        self.body.addWidget(self.t_box)

        g2 = QGridLayout()
        g2.addWidget(QLabel("Size"), 0, 0)
        self.side = QComboBox()
        for name, _ in self.SIDES:
            self.side.addItem(name)
        g2.addWidget(self.side, 0, 1)
        self.webp = QCheckBox("Convert to WebP (usually the smallest)")
        g2.addWidget(self.webp, 1, 1)
        self.body.addLayout(g2)

        # before / after at 100%
        pr = QHBoxLayout()
        self.before = QLabel()
        self.after = QLabel()
        for lab, cap in ((self.before, "Original"), (self.after, "Compressed")):
            col = QVBoxLayout()
            lab.setFixedSize(270, 170)
            lab.setAlignment(Qt.AlignCenter)
            lab.setStyleSheet("border-radius: 12px; background: rgba(0,0,0,0.25);")
            c = QLabel(cap)
            c.setObjectName("dim")
            col.addWidget(lab)
            col.addWidget(c, 0, Qt.AlignHCenter)
            pr.addLayout(col)
        self.body.addLayout(pr)

        self.est = QLabel()
        self.est.setObjectName("big")
        self.saving = QLabel()
        self.saving.setObjectName("good")
        self.body.addWidget(self.est)
        self.body.addWidget(self.saving)
        self.body.addStretch(1)
        label = "Compress" if len(self.paths) == 1 else f"Compress {len(self.paths)} files"
        self.body.addLayout(self.footer(label, self.save))

        self._timer = QTimer(self, singleShot=True, interval=60, timeout=self.estimate)
        self.q.valueChanged.connect(lambda _: self._timer.start())
        self.side.currentIndexChanged.connect(lambda _: self._timer.start())
        self.webp.toggled.connect(lambda _: self._timer.start())
        self.tgrp.idClicked.connect(lambda _: self._timer.start())
        self.mode.idClicked.connect(self._mode)
        self._set_before()
        self.estimate()

    def _mode(self, i):
        self.q_box.setVisible(i == 0)
        self.t_box.setVisible(i == 1)
        self._timer.start()

    def _detail_box(self, im: Image.Image) -> tuple[int, int, int, int]:
        """The 270×170 window with the most detail (where compression artefacts show)."""
        from PIL import ImageFilter, ImageStat
        w, h = 270, 170
        if im.width <= w or im.height <= h:
            return (0, 0, min(w, im.width), min(h, im.height))
        edges = im.convert("L").filter(ImageFilter.FIND_EDGES)
        best, box = -1.0, (0, 0, w, h)
        for gx in range(5):
            for gy in range(5):
                x = int((im.width - w) * gx / 4)
                y = int((im.height - h) * gy / 4)
                v = ImageStat.Stat(edges.crop((x, y, x + w, y + h))).mean[0]
                if v > best:
                    best, box = v, (x, y, x + w, y + h)
        return box

    def _crop_100(self, im: Image.Image) -> QPixmap:
        if not hasattr(self, "_box"):
            self._box = self._detail_box(self.pv)
        return QPixmap.fromImage(qimage_from_pil(im.crop(self._box)))

    def _set_before(self):
        self.before.setPixmap(self._crop_100(self.pv))

    def _settings(self):
        side = self.SIDES[self.side.currentIndex()][1]
        target = imaging.lossy_target(self.path, self.webp.isChecked())
        return side, target

    def estimate(self):
        side, target = self._settings()
        im = self.pv
        # scale factor from preview pixels to output pixels
        out_long = min(self.full_long, side) if side else self.full_long
        px_ratio = (out_long / max(im.size)) ** 2
        if self.mode.checkedId() == 1:
            limit = self.TARGETS[self.tgrp.checkedId()][1]
            q = self._quality_for(im, target, limit, px_ratio)
            note = f"quality ≈ {q}"
        else:
            q = self.q.value()
            note = ""
        n = int(imaging.encode_size(im, target, q) * px_ratio)
        buf = io.BytesIO()
        if target == "PNG":
            im.convert("RGBA").quantize(colors=max(16, min(256, int(q * 2.56)))).save(buf, "PNG")
        else:
            from .convert import save_image
            save_image(im, buf, target, quality=q)
        buf.seek(0)
        try:
            self.after.setPixmap(self._crop_100(Image.open(buf).convert("RGB")))
        except Exception:
            pass
        orig1 = file_size(self.path)
        if len(self.paths) > 1:
            total = int(n * self.orig_total / max(1, orig1))
            self.est.setText(f"{human_size(self.orig_total)}  →  ≈ {human_size(total)}")
            n_cmp, o_cmp = total, self.orig_total
        else:
            self.est.setText(f"{human_size(orig1)}  →  ≈ {human_size(n)}")
            n_cmp, o_cmp = n, orig1
        pct = (1 - n_cmp / max(1, o_cmp)) * 100
        fmt = target if target != "JPG" else "JPG"
        if pct >= 1:
            self.saving.setObjectName("good")
            self.saving.setText(f"≈ {pct:.0f}% smaller · {fmt}" + (f" · {note}" if note else ""))
        else:
            self.saving.setObjectName("warn")
            self.saving.setText("Already well compressed — try a smaller size or WebP")
        self.saving.style().unpolish(self.saving)
        self.saving.style().polish(self.saving)

    @staticmethod
    def _quality_for(im, target, limit, px_ratio) -> int:
        lo, hi, best = 30, 92, 30
        while lo <= hi:
            q = (lo + hi) // 2
            if imaging.encode_size(im, target, q) * px_ratio <= limit:
                best, lo = q, q + 1
            else:
                hi = q - 1
        return best

    def save(self):
        side, target = self._settings()
        paths = list(self.paths)
        if self.mode.checkedId() == 1:
            limit = self.TARGETS[self.tgrp.checkedId()][1]
            label = self.TARGETS[self.tgrp.checkedId()][0]

            def work():
                outs = []
                for p in paths:
                    im = open_image(p)
                    if side and max(im.size) > side:
                        im.thumbnail((side, side), Image.LANCZOS)
                    q, s2 = imaging.plan_target_size(im, target, limit)
                    outs.append(imaging.compress_to(p, q, min(x for x in (side, s2) if x) if (side or s2) else None, target))
                return outs
            self.run(work, "Compressing…", f"target {label}")
        else:
            q = self.q.value()
            self.run(lambda: [imaging.compress_to(p, q, side, target) for p in paths], "Compressing…", f"quality {q}")
