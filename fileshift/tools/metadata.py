"""Tool windows: Compress, Resize, Crop, Edit, Annotate, Redact, Add BG, Metadata, Protect.

Every window opens on a fast, reduced-size preview. Saving runs on the full-resolution
image in the background (the window closes immediately; a notification reports the result)."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import (QDesktopServices)
from PySide6.QtWidgets import (QFrame,
                               QGridLayout, QHeaderView, QLabel, QPushButton, QTableWidget, QTableWidgetItem)

from .. import imaging

from ._shared import ToolWindow
Notify = Callable[..., None]



# ================================================================ METADATA
class MetadataWindow(ToolWindow):
    tool_name = "Metadata"

    def __init__(self, path, notify, is_pdf: bool = False):
        super().__init__("Metadata", path, notify, size=(640, 380))
        self.is_pdf = is_pdf
        info = imaging.read_pdf_metadata(path) if is_pdf else imaging.read_image_metadata(path)
        summary = {} if is_pdf else imaging.metadata_summary(path)
        self.n_fields, self.has_gps = (len(info), False) if is_pdf else imaging.count_metadata(path)

        card = QFrame()
        card.setObjectName("card")
        cl = QGridLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setHorizontalSpacing(16)
        rows = summary or {k: v for k, v in info.items() if k in ("title", "author", "creator", "producer", "Pages")}
        if not rows:
            rows = {"": "No personal metadata found."}
        for i, (k, v) in enumerate(rows.items()):
            kl = QLabel(k)
            kl.setObjectName("dim")
            cl.addWidget(kl, i, 0)
            vl = QLabel(v)
            vl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            cl.addWidget(vl, i, 1)
            if k == "Location":
                vl.setObjectName("warn")
                mb = QPushButton("Open map")
                lat, lon = v.split(", ")
                mb.clicked.connect(lambda _=False, a=lat, b=lon: QDesktopServices.openUrl(
                    QUrl(f"https://www.openstreetmap.org/?mlat={a}&mlon={b}#map=15/{a}/{b}")))
                cl.addWidget(mb, i, 2)
        self.body.addWidget(card)
        if self.has_gps:
            warn = QLabel("⚠  This photo reveals where it was taken.")
            warn.setObjectName("warn")
            self.body.addWidget(warn)

        self.toggle = QPushButton(f"Show all {self.n_fields} fields")
        self.toggle.setCheckable(True)
        self.body.addWidget(self.toggle, 0, Qt.AlignLeft)
        t = QTableWidget(len(info), 2)
        t.setHorizontalHeaderLabels(["Field", "Value"])
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        t.horizontalHeader().setStretchLastSection(True)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        for r, (k, v) in enumerate(info.items()):
            t.setItem(r, 0, QTableWidgetItem(k))
            t.setItem(r, 1, QTableWidgetItem(v))
        t.setVisible(False)

        def show_all(on):
            t.setVisible(on)
            self.resize(self.width(), 640 if on else 380)
        self.toggle.toggled.connect(show_all)
        self.body.addWidget(t, 1)
        self.body.addStretch(0)

        extra = []
        if self.has_gps:
            loc = QPushButton("Remove location only")
            loc.clicked.connect(self.strip_location)
            extra.append(loc)
        self.body.addLayout(self.footer("Remove all metadata", self.strip, None, extra))

    def strip(self):
        path, is_pdf = self.path, self.is_pdf
        detail = f"removed {self.n_fields} field{'s' if self.n_fields != 1 else ''}" + (" incl. GPS location" if self.has_gps else "")

        def work():
            return [imaging.strip_pdf_metadata(path) if is_pdf else imaging.strip_image_metadata(path)]
        self.run(work, "Removing metadata…", detail)

    def strip_location(self):
        path = self.path
        self.run(lambda: [imaging.strip_location(path)], "Removing location…", "GPS removed, camera info kept")
