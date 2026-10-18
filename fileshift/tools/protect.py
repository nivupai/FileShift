"""Tool windows: Compress, Resize, Crop, Edit, Annotate, Redact, Add BG, Metadata, Protect.

Every window opens on a fast, reduced-size preview. Saving runs on the full-resolution
image in the background (the window closes immediately; a notification reports the result)."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QCheckBox, QGridLayout, QLabel, QLineEdit)

from .. import imaging

from ._shared import ToolWindow
Notify = Callable[..., None]



# ================================================================ PROTECT (PDF)
class ProtectWindow(ToolWindow):
    tool_name = "Protect"

    def __init__(self, path, notify):
        super().__init__("Password-protect PDF", path, notify, size=(520, 330))
        g = QGridLayout()
        self.pw = QLineEdit()
        self.pw2 = QLineEdit()
        for e in (self.pw, self.pw2):
            e.setEchoMode(QLineEdit.Password)
        g.addWidget(QLabel("Password"), 0, 0)
        g.addWidget(self.pw, 0, 1)
        g.addWidget(QLabel("Confirm"), 1, 0)
        g.addWidget(self.pw2, 1, 1)
        show = QCheckBox("Show")
        show.toggled.connect(lambda on: [e.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)
                                         for e in (self.pw, self.pw2)])
        g.addWidget(show, 0, 2)
        self.body.addLayout(g)
        self.msg = QLabel("AES-256 encryption. Anyone opening the PDF will need this password.")
        self.msg.setObjectName("dim")
        self.msg.setWordWrap(True)
        self.body.addWidget(self.msg)
        self.body.addStretch(1)
        self.body.addLayout(self.footer("Protect", self.save))
        self.pw.textChanged.connect(self._check)
        self.pw2.textChanged.connect(self._check)
        self._check()
        QTimer.singleShot(0, self.pw.setFocus)

    def _check(self):
        a, b = self.pw.text(), self.pw2.text()
        ok = len(a) >= 4 and a == b
        self.primary_btn.setEnabled(ok)
        if a and len(a) < 4:
            self.msg.setText("Use at least 4 characters.")
        elif b and a != b:
            self.msg.setText("Passwords don't match yet.")
        elif ok:
            strength = "strong" if len(a) >= 12 else "okay" if len(a) >= 8 else "weak"
            self.msg.setText(f"Looks good · {strength} password")
        else:
            self.msg.setText("AES-256 encryption. Anyone opening the PDF will need this password.")

    def save(self):
        pw, path = self.pw.text(), self.path
        self.run(lambda: [imaging.protect_pdf(path, pw)], "Encrypting…")
