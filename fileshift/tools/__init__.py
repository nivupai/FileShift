"""Tool windows: Compress, Resize, Crop, Edit, Annotate, Redact, Add BG, Metadata, Protect,
Watermark.

Every window opens on a fast, reduced-size preview. Saving runs on the full-resolution
image in the background (the window closes immediately; a notification reports the result).

Split into one module per tool; this package re-exports the window classes so
`from fileshift import tools; tools.CropWindow(...)` keeps working unchanged.
"""
from __future__ import annotations

from .compress import CompressWindow
from .crop import CropWindow
from .addbg import AddBgWindow
from .annotate import AnnotateWindow
from .redact import RedactWindow
from .edit import EditWindow
from .metadata import MetadataWindow
from .resize import ResizeWindow
from .protect import ProtectWindow
from .watermark import WatermarkWindow

__all__ = ["CompressWindow", "CropWindow", "AddBgWindow", "AnnotateWindow", "RedactWindow",
           "EditWindow", "MetadataWindow", "ResizeWindow", "ProtectWindow", "WatermarkWindow"]
