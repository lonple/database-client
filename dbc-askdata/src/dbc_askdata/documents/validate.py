from __future__ import annotations

import logging
import zipfile
from pathlib import Path

from dbc_askdata.config import Settings
from dbc_askdata.documents import ALLOWED_EXTS, DOCUMENT_EXTS, IMAGE_EXTS, REJECT_EXTS, ConvertError

log = logging.getLogger(__name__)


def extension_of(filename: str) -> str:
    name = (filename or "").strip()
    if "." not in name:
        raise ConvertError("文件缺少扩展名")
    return name.rsplit(".", 1)[-1].lower()


def pipeline_for(ext: str) -> str:
    if ext in DOCUMENT_EXTS:
        return "DOCUMENT"
    if ext in IMAGE_EXTS:
        return "IMAGE"
    raise ConvertError(f"不支持的格式: .{ext}")


def normalize_format(ext: str) -> str:
    if ext == "htm":
        return "html"
    if ext == "jpeg":
        return "jpg"
    if ext == "tiff":
        return "tif"
    return ext


def _looks_html(head: bytes) -> bool:
    text = head.decode("utf-8", errors="ignore").lstrip("\ufeff \t\r\n").lower()
    return text.startswith("<!doctype html") or text.startswith("<html") or "<html" in text[:500]


def count_xlsx_sheets(path: Path) -> int:
    with zipfile.ZipFile(path) as zf:
        return sum(
            1
            for n in zf.namelist()
            if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")
        )


def validate_upload(*, filename: str, data: bytes, dest: Path, settings: Settings) -> tuple[str, str]:
    if len(data) > settings.document_max_bytes:
        raise ConvertError(f"文件超过 {settings.document_max_bytes} 字节上限")
    if not data:
        raise ConvertError("空文件")
    if data[:2] == b"MZ":
        raise ConvertError("拒绝可执行文件")
    ext = extension_of(filename)
    if ext in REJECT_EXTS:
        raise ConvertError(f"不支持的格式: .{ext}")
    if ext not in ALLOWED_EXTS:
        raise ConvertError(f"不支持的格式: .{ext}")
    head = data[:16]
    if ext == "pdf" and not head.startswith(b"%PDF"):
        raise ConvertError("不是有效的 PDF")
    if ext == "png" and not head.startswith(b"\x89PNG"):
        raise ConvertError("不是有效的 PNG")
    if ext in ("jpg", "jpeg") and not head.startswith(b"\xff\xd8\xff"):
        raise ConvertError("不是有效的 JPEG")
    if ext == "bmp" and not head.startswith(b"BM"):
        raise ConvertError("不是有效的 BMP")
    if ext in ("tif", "tiff") and head[:4] not in (b"II*\x00", b"MM\x00*"):
        raise ConvertError("不是有效的 TIFF")
    if ext == "webp" and not (head.startswith(b"RIFF") and data[8:12] == b"WEBP"):
        raise ConvertError("不是有效的 WebP")
    if ext in ("docx", "xlsx"):
        if not head.startswith(b"PK"):
            raise ConvertError("不是有效的 Office 文档")
    if ext in ("html", "htm") and not _looks_html(data[:2048]):
        raise ConvertError("不是有效的 HTML")
    dest.write_bytes(data)
    if ext == "xlsx":
        try:
            n = count_xlsx_sheets(dest)
        except Exception as ex:
            log.error("读取 xlsx 工作表失败", exc_info=True)
            dest.unlink(missing_ok=True)
            raise ConvertError("无法读取 Excel 工作簿") from ex
        if n > settings.document_xlsx_max_sheets:
            dest.unlink(missing_ok=True)
            raise ConvertError(f"工作表数量超过 {settings.document_xlsx_max_sheets}")
    return pipeline_for(ext), normalize_format(ext)
