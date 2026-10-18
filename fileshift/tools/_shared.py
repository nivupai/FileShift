"""Tool windows: Compress, Resize, Crop, Edit, Annotate, Redact, Add BG, Metadata, Protect.

Every window opens on a fast, reduced-size preview. Saving runs on the full-resolution
image in the background (the window closes immediately; a notification reports the result)."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import (QKeySequence,
                           QShortcut)
from PySide6.QtWidgets import (QButtonGroup, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QSlider)

from ..util import file_size, human_size
from ..window import GlassWindow, ImageView

Notify = Callable[..., None]



# ---------------------------------------------------------------- small widgets
def section(text: str) -> QLabel:
    l = QLabel(text.upper())
    l.setObjectName("section")
    return l


def slider(lo: int, hi: int, val: int) -> QSlider:
    s = QSlider(Qt.Horizontal)
    s.setRange(lo, hi)
    s.setValue(val)
    return s


def toggle_row(labels: list[str], checked: int = 0) -> tuple[QHBoxLayout, QButtonGroup]:
    row = QHBoxLayout()
    row.setSpacing(6)
    grp = QButtonGroup(row)
    grp.setExclusive(True)
    for i, t in enumerate(labels):
        b = QPushButton(t)
        b.setCheckable(True)
        b.setChecked(i == checked)
        grp.addButton(b, i)
        row.addWidget(b)
    row.addStretch(1)
    return row, grp


def slider_row(grid: QGridLayout, r: int, label: str, s: QSlider, fmt: Callable[[int], str]) -> QLabel:
    grid.addWidget(QLabel(label), r, 0)
    grid.addWidget(s, r, 1)
    val = QLabel(fmt(s.value()))
    val.setObjectName("dim")
    val.setMinimumWidth(56)
    val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    s.valueChanged.connect(lambda v: val.setText(fmt(v)))
    grid.addWidget(val, r, 2)
    return val


def dims_text(w: int, h: int) -> str:
    return f"{w} × {h}"


class ToolWindow(GlassWindow):
    tool_name = ""

    def __init__(self, title: str, paths, notify: Notify, size=(820, 680)):
        super().__init__(title, size=size)
        self.paths = [Path(p) for p in (paths if isinstance(paths, (list, tuple)) else [paths])]
        self.path = self.paths[0]
        self.notify = notify
        self.submit = None   # set by the app: run work in the background with a spinner
        if len(self.paths) == 1:
            sub = f"{self.path.name}  ·  {human_size(file_size(self.path))}"
        else:
            total = sum(file_size(p) for p in self.paths)
            sub = f"{len(self.paths)} files  ·  {human_size(total)}"
        self.subtitle = QLabel(sub)
        self.subtitle.setObjectName("dim")
        self.body.addWidget(self.subtitle)
        QShortcut(QKeySequence(Qt.Key_Return), self, activated=self._enter)
        QShortcut(QKeySequence(Qt.Key_Enter), self, activated=self._enter)
        self.primary_btn: QPushButton | None = None

    def _enter(self):
        from PySide6.QtWidgets import QApplication
        fw = QApplication.focusWidget()
        if isinstance(fw, QLineEdit) and isinstance(fw.parent(), ImageView):
            fw.returnPressed.emit()   # Enter in an on-canvas text box finishes the text
            return
        if self.primary_btn is not None and self.primary_btn.isEnabled():
            self.primary_btn.click()

    def footer(self, primary_text: str, on_primary, on_reset=None, extra_buttons=()) -> QHBoxLayout:
        row = QHBoxLayout()
        if on_reset:
            reset = QPushButton("Reset")
            reset.clicked.connect(on_reset)
            row.addWidget(reset)
        for b in extra_buttons:
            row.addWidget(b)
        row.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.close)
        row.addWidget(cancel)
        ok = QPushButton(primary_text)
        ok.setObjectName("primary")
        ok.clicked.connect(on_primary)
        row.addWidget(ok)
        self.primary_btn = ok
        return row

    def run(self, fn: Callable[[], list], working: str, extra: str = ""):
        """Save in the background (window closes now) or, without the app, synchronously."""
        action = f"tool:{self.tool_name}"
        if self.submit is not None:
            self.submit(action, [str(p) for p in self.paths], fn, working, extra)
            self.close()
        else:
            outs = fn()
            self.notify(action, [str(p) for p in self.paths], outs, extra)
            self.close()
