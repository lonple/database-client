from __future__ import annotations

DOCUMENT_EXTS = frozenset({"docx", "pdf", "xlsx", "html", "htm"})
IMAGE_EXTS = frozenset({"png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp"})
ALLOWED_EXTS = DOCUMENT_EXTS | IMAGE_EXTS
REJECT_EXTS = frozenset({"exe", "docm", "xlsm", "pptm", "doc", "xls", "gif", "mp4", "zip"})


class ConvertError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
